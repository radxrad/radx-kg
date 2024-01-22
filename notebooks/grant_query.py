#!/usr/bin/env python
# coding: utf-8
import numpy as np
import pandas as pd
import requests
from fake_useragent import UserAgent
import json
import re
import time
from titlecase import titlecase
from Levenshtein import jaro_winkler
from typing import List
from utils import rename_and_reorder_columns

# Parameters for NIH Reporter Search
PROJECT_LIMIT = 500 # maximum number of records for project search


def get_projects(core_project_numbers: List[str], chunk_size: int = PROJECT_LIMIT) -> pd.DataFrame:
    """
    Retrieve project data in batches from a list of core project numbers.

    This function divides the list of core project numbers into smaller chunks
    to avoid overloading the API and then fetches data for each chunk. The results
    are concatenated to form a final dataset of project information.

    Parameters
    ----------
    core_project_numbers : List[str]
        A list of core project numbers to retrieve data for.

    chunk_size : int, optional
        The maximum number of core project numbers to include in each API request.
        Defaults to PROJECT_LIMIT.

    Returns
    -------
    pd.DataFrame
        A DataFrame containing project data retrieved from the API.

    Examples
    --------
    >>> core_project_numbers = ["U01AA029316", "R01DC016112"]
    >>> get_projects(core_project_numbers)
        appl_id  subproject_id  fiscal_year        project_num  project_serial_num  ...
    0   10320986          None         2022    4U01AA029316-02            AA029316  ...
    1   ...
    2   10129336          None         2021    5R01DC016112-05            DC016112  ...
    ...
    """
    # Fetch project data in batches and concatenate the results
    offset = 0
    num_records = 1
    batches = []
    while offset < num_records:
        data, num_records = search_project_numbers(core_project_numbers, chunk_size, offset)
        batches.append(data)
        offset += chunk_size
        
    # Normalize the JSON data and concatenate into a DataFrame
    projects = [pd.json_normalize(data["results"]) for data in batches]
    
    # Concatenate the extracted data into a DataFrame
    df = pd.concat(projects, join="inner")

    # Standardize and simplify data
    df = transform_data(df)
    return df


def transform_data(df):
    df["project_serial_num"].fillna("", inplace=True)
    df["project_serial_num"] = df.apply(lambda x: x["project_serial_num"] if len(x["project_serial_num"]) > 0 else x["project_num"], axis=1, result_type='expand')
    df["project_serial_num"] = df["project_serial_num"].str.split("-").str[0]
    
    df["covid_response"].fillna("", inplace=True)
    
    # truncate date to YYYY-MM-DD 
    df["project_start_date"] = df["project_start_date"].str[:10]
    df["budget_start_date"] = df["budget_start"].str[:10]
    df["budget_end_date"] = df["budget_end"].str[:10]
    df_map = {"project_serial_num": "projectSerialNum", "core_project_num": "coreProjectNum", "fiscal_year": "fiscalYear", "appl_id": "applId", 
              "agency_ic_admin.abbreviation": "agency", "project_title": "projectTitle", "abstract_text": "abstract", "phr_text": "narrative", 
              "funding_mechanism": "fundingMechanism", "activity_code": "awardCode", "opportunity_number": "opportunityNumber"}
    df = rename_and_reorder_columns(df, df_map)
    return df


def extract_project_serial_num(core_project_num):
    """
    Example: 1U18TR003793-01 -> TR003793
    """
    pattern = r'.*[A-Z]{2}\d{6}$'
    if re.match(pattern, core_project_num):
        return core_project_num[-8:]
    else:
        return core_project_num


def standardize_name(name):
    # if name is mixed case, don't change it
    # TODO: SHEILA Ann GRANT (is mixed case), need to check each word
    # TODO: MacKensie
    name = name.replace(".", "")
    uname = name.upper()
    if uname.startswith("MC") or " MC" in uname:
        return titlecase(name)
    if not name.islower() and not name.isupper():
        return name

    return name.title()


def add_prefix(identifier, prefix):
    """
    Add a prefix if the identifier is not empty or NaN
    """
    if pd.isna(identifier):
        return ""
    
    if not identifier:
        return ""

    if isinstance(identifier, float):
        identifier = int(identifier)
        
    return f"{prefix}{identifier}"


def remove_prefix(text, prefix):
    """
    Remove prefixes found in NIH Grant abstracts and narratives.

    Parameters
    ----------
    text : str
        The input text containing the prefix to be removed.

    prefix : str
        The prefix to be removed from the input text.

    Returns
    -------
    str
        The text after removing the specified prefix and additional separators.

    Notes
    -----
    It removes the specified prefix and additional separators, such as leading
    slashes, colons, dashes, and hyphens.
    """
    # Remove leading slash
    text = text.removeprefix("/").lstrip()

    if text.lower().lstrip().startswith(prefix.lower()):
        # find the position of the separator for the prefix
        pos = text.find("\n")
        # Avoid inadvertently truncating the text if the separator is found too far away from the prefix
        if pos > len(prefix) + 15:
            pos = -1

        if pos < 0:
            # if there is no separator, remove the prefix
            text = text[len(prefix):].lstrip()
        else:
            # remove the text up to the separator position
            text = text[pos:].lstrip()

    # remove other separators
    text = text.removeprefix(":").lstrip()
    text = text.removeprefix("–").lstrip()
    text = text.removeprefix("-").lstrip()
    return text


def create_chunks(data, chunk_size):
    """
    Split a list into smaller chunks of a specified size.

    Args:
        data (list): The input list to be divided into chunks.
        chunk_size (int): The maximum size of each chunk.

    Returns:
        list: A list of chunks, where each chunk is a sublist of 'data'.

    Example:
        >>> data = [1, 2, 3, 4, 5, 6, 7, 8]
        >>> chunk_size = 3
        >>> create_chunks(data, chunk_size)
        [[1, 2, 3], [4, 5, 6], [7, 8]]
    """
    # split list into chunks of max size: chunk_size
    return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]


def search_project_numbers(core_project_numbers, chunk_size, offset):
    #print("search_projects:", core_project_numbers)  
    PROJECTS_URL = "https://api.reporter.nih.gov/v2/projects/search"
    HEADERS = {"accept": "application/json"}
    params = {"criteria": {"project_nums": core_project_numbers,},
              "offset": offset,
              "limit": chunk_size,
             }
    
    try:
        response = requests.post(PROJECTS_URL, headers=HEADERS, json=params)
        response.raise_for_status()
        data = response.json()
        num_records = data["meta"]["total"]
    except requests.exceptions.HTTPError as error:
        print(f"ERROR: nih_reporter HTTP error: {error}")
    except requests.exceptions.RequestException as error:
        print(f"ERROR: nih_reporter: {error}")

    time.sleep(1)
    return data, num_records


def search_profile_ids(profile_ids, chunk_size, offset): 
    PROJECTS_URL = "https://api.reporter.nih.gov/v2/projects/search"
    HEADERS = {"accept": "application/json"}
    params = {"criteria": {
                  "pi_profile_ids" : profile_ids,
              },
              "offset": offset,
              "limit": chunk_size,
             }
    
    try:
        response = requests.post(PROJECTS_URL, headers=HEADERS, json=params)
        response.raise_for_status()
        data = response.json()
        num_records = data["meta"]["total"]
    except requests.exceptions.HTTPError as error:
        print(f"ERROR: nih_reporter HTTP error: {error}")
    except requests.exceptions.RequestException as error:
        print(f"ERROR: nih_reporter: {error}")

    time.sleep(1)
    return data, num_records


def search_principal_investigators_by_name(investigator, chunk_size, offset): 
    PROJECTS_URL = "https://api.reporter.nih.gov/v2/projects/search"
    HEADERS = {"accept": "application/json"}
    params = {"criteria": {
                  "pi_names" : [
                      {"any_name": investigator}
                  ]
              },
              "offset": offset,
              "limit": chunk_size,
             }
    
    try:
        response = requests.post(PROJECTS_URL, headers=HEADERS, json=params)
        response.raise_for_status()
        data = response.json()
        num_records = data["meta"]["total"]
    except requests.exceptions.HTTPError as error:
        print(f"ERROR: nih_reporter HTTP error: {error}")
    except requests.exceptions.RequestException as error:
        print(f"ERROR: nih_reporter: {error}")

    time.sleep(1)
    return data, num_records

def get_principal_investigators_by_name(investigators, chunk_size=PROJECT_LIMIT):
    """
    Retrieve principal investigator data for projects associated with a list of core project numbers.

    This function divides the list of investigators into smaller chunks to prevent
    overloading the API. It then fetches project data for each chunk and extracts principal
    investigator information, expanding it into a structured DataFrame.

    Args:
        investigators (list): A list of investigator names to retrieve data for.
        chunk_size (int, optional): The maximum number of core project numbers to include in
            each API request. Defaults to PROJECT_LIMIT.

    Returns:
        pandas.DataFrame: A DataFrame containing principal investigator data associated with
            the specified core project numbers.

    Example:
        >>> investigators = []
        >>> get_principal_investigators(core_project_numbers)
    """
    # Fetch project data in batches and concatenate the results
    batches = []
    for investigator in investigators:
        offset = 0
        num_records = 1
        while offset < num_records:
            data, num_records = search_principal_investigators_by_name(investigator, chunk_size, offset)
            batches.append(data)
            offset += chunk_size
    
    # Extract and expand principal investigator data
    pis = [pd.json_normalize(data["results"], record_path=["principal_investigators"],
                             meta=["appl_id", "core_project_num", "project_serial_num", "fiscal_year"]) for data in batches]
    
    # Concatenate the extracted data into a DataFrame
    df = pd.concat(pis)

    # standardize names
    df["first_name"] = df["first_name"].apply(standardize_name)
    df["last_name"] = df["last_name"].apply(standardize_name)
    df["middle_name"] = df["middle_name"].apply(standardize_name)
    df["full_name"] = df["full_name"].apply(standardize_name)
    df["name"] = df["last_name"] + " " + df["first_name"].str[:1] + df["middle_name"].str[:1]
    # create PI name in firstname lastname format to match dbGaP convention
    #df["grant_pi"] = pis["last_name"] + " " + pis["first_name"]
    df["appl_id"] = df["appl_id"].astype(str)
    col_map = {"profile_id": "profileId", "core_project_num": "coreProjectNum", "project_serial_num": "projectSerialNum", "is_contact_pi": "isContactPi", "fiscal_year": "fiscalYear",
              "name": "name", "full_name": "fullName", "first_name": "firstName", "middle_name": "middleName", "last_name": "lastName"}

    return rename_and_reorder_columns(df, col_map)


def get_principal_investigators(core_project_numbers, chunk_size=PROJECT_LIMIT):
    """
    Retrieve principal investigator data for projects associated with a list of core project numbers.

    This function divides the list of core project numbers into smaller chunks to prevent
    overloading the API. It then fetches project data for each chunk and extracts principal
    investigator information, expanding it into a structured DataFrame.

    Args:
        core_project_numbers (list): A list of core project numbers to retrieve data for.
        chunk_size (int, optional): The maximum number of core project numbers to include in
            each API request. Defaults to PROJECT_LIMIT.

    Returns:
        pandas.DataFrame: A DataFrame containing principal investigator data associated with
            the specified core project numbers.

    Example:
        >>> core_project_numbers = ["U01AA029316", "R01DC016112"]
        >>> get_principal_investigators(core_project_numbers)
    """
    # Fetch project data in batches and concatenate the results
    offset = 0
    num_records = 1
    batches = []
    while offset < num_records:
        data, num_records = search_project_numbers(core_project_numbers, chunk_size, offset)
        batches.append(data)
        offset += chunk_size
    
    # Extract and expand principal investigator data
    pis = [pd.json_normalize(data["results"], record_path=["principal_investigators"],
                             meta=["appl_id", "core_project_num", "project_serial_num", "fiscal_year"]) for data in batches]
    
    # Concatenate the extracted data into a DataFrame
    df = pd.concat(pis)

    # standardize names
    df["first_name"] = df["first_name"].apply(standardize_name)
    df["last_name"] = df["last_name"].apply(standardize_name)
    df["middle_name"] = df["middle_name"].apply(standardize_name)
    df["full_name"] = df["full_name"].apply(standardize_name)
    df["name"] = df["last_name"] + " " + df["first_name"].str[:1] + df["middle_name"].str[:1]
    # create PI name in firstname lastname format to match dbGaP convention
    #df["grant_pi"] = pis["last_name"] + " " + pis["first_name"]
    df["appl_id"] = df["appl_id"].astype(str)
    col_map = {"profile_id": "profileId", "core_project_num": "coreProjectNum", "project_serial_num": "projectSerialNum", "is_contact_pi": "isContactPi", "fiscal_year": "fiscalYear",
              "name": "name", "full_name": "fullName", "first_name": "firstName", "middle_name": "middleName", "last_name": "lastName"}

    return rename_and_reorder_columns(df, col_map)

    
def get_organizations(profile_ids, chunk_size=PROJECT_LIMIT):
    """
    Retrieve principal investigator data for projects associated with a list of profile ids.

    This function divides the list of core project numbers into smaller chunks to prevent
    overloading the API. It then fetches project data for each chunk and extracts principal
    investigator information, expanding it into a structured DataFrame.

    Args:
        core_project_numbers (list): A list of core project numbers to retrieve data for.
        chunk_size (int, optional): The maximum number of core project numbers to include in
            each API request. Defaults to PROJECT_LIMIT.

    Returns:
        pandas.DataFrame: A DataFrame containing principal investigator data associated with
            the specified core project numbers.

    Example:
        >>> core_project_numbers = ["U01AA029316", "R01DC016112"]
        >>> get_principal_investigators(core_project_numbers)
    """
    # Fetch project data in batches and concatenate the results
    offset = 0
    num_records = 1
    batches = []
    while offset < num_records:
        data, num_records = search_profile_ids(profile_ids, chunk_size, offset)
        batches.append(data)
        offset += chunk_size
    
    # Extract and expand principal investigator data
    profiles = [pd.json_normalize(data["results"], record_path=["principal_investigators"],
                             meta=["appl_id", "fiscal_year"]) for data in batches]
    profile_df = pd.concat(profiles)
    # only the contact PI has associated organization info
    profile_df.query("is_contact_pi == True", inplace=True)
    
    # keep only the latest fiscal year to get the latest organization info
    profile_df["appl_id"] = profile_df["appl_id"].astype(str)
    profile_df["profile_id"] = profile_df["profile_id"].astype(str)
    profile_df.sort_values("fiscal_year", ascending=False, inplace=True)
    profile_df.drop_duplicates("profile_id", inplace=True)

    # extract and expand organization information
    projects = [pd.json_normalize(data["results"]) for data in batches]
    project_df = pd.concat(projects)
    project_df = project_df[["appl_id", "organization.org_name", "organization.org_city", "organization.org_zipcode", "organization.org_state", 
                             "organization.org_country", "organization.primary_duns", "organization.primary_uei"]].copy()
    project_df["appl_id"] = project_df["appl_id"].astype(str)

    # keep only records that match the profile ids
    orgs = profile_df.merge(project_df, on="appl_id")
    orgs = orgs[orgs["profile_id"].isin(profile_ids)]

    return orgs


def author_match_score(target_authors, source_authors, threshold):
    """Return the best name match score (0-1) for a PI with a list of authors"""
    if not isinstance(target_authors, list):
        target_authors = [target_authors]

    if not isinstance(source_authors, list):
        source_authors = [source_authors]

    max_score = 0
    match_target_author = ""
    match_source_author = ""
    for target_author in target_authors:
        for source_author in source_authors:
            if (score := jaro_winkler(target_author, source_author, score_cutoff=threshold)) > max_score:
                max_score = score
                match_target_author = target_author
                match_source_author = source_author
 

    return match_target_author, match_source_author, max_score


def search_grants_dot_gov(funding_opportunity):
    POST_URL = "https://apply07.grants.gov/grantsws/rest/opportunities/search"
    ua = UserAgent()
    HEADERS = {"accept": "application/json", 'User-Agent': ua.random}
    params = {"oppNum": funding_opportunity, "oppStatuses": "forecasted|posted|closed|archived"}

    try:
        response = requests.post(POST_URL, headers=HEADERS, json=params)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.HTTPError as error:
        print(f"ERROR: grants.gov HTTP error: {error} for funding opportunity: {funding_opportunity}")
    except requests.exceptions.RequestException as error:
        print(f"ERROR: grants.gov: {error} for funding opportunity: {funding_opportunity}")

    return data["oppHits"], data["hitCount"]


def search_funding_opportunities(funding_opportunities):   
    data = []
    for funding_opportunity in funding_opportunities:
        fo_data, num_records = search_grants_dot_gov(funding_opportunity)
        time.sleep(1)
        if num_records > 0:
            data.append(fo_data[0])

    df = pd.DataFrame(data)
    return df


def add_funding_opportunity_url(id):
    """Add funding opportunity URL"""
    if id.startswith("RFA"):
        return "https://grants.nih.gov/grants/guide/rfa-files/" + id + ".html"
    if id.startswith("PA"):
        return "https://grants.nih.gov/grants/guide/pa-files/" + id + ".html"

    return ""
