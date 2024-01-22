#!/usr/bin/env python
# coding: utf-8
import os
import shutil
import glob
import time
from Levenshtein import jaro_winkler
import unicodedata
from titlecase import titlecase
from tqdm import tqdm
import pandas as pd
# from selenium import webdriver
# from selenium.webdriver.common.by import By
# import chromedriver_binary 


def rename_and_reorder_columns(df, col_map):
    df = df[col_map.keys()].copy()
    df.rename(columns=col_map, inplace=True)
    df.fillna("", inplace=True)
    df = df.astype(str)
    return df


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


def fuzzy_merge(df1, df2, left_fuzzy_on, right_fuzzy_on, left_on=None, right_on=None, how="inner", threshold=0.9):
    dfm = df1.copy()
    right_names = df2[right_fuzzy_on].tolist()
    dfm[["match", "score"]] = dfm[left_fuzzy_on].apply(lambda x: pd.Series(author_match(x, right_names, threshold)))
    if left_on and right_on:
        dfm = dfm.merge(df2, left_on=["match", left_on], right_on=[right_fuzzy_on, right_on], how=how)
    else:
        dfm = dfm.merge(df2, left_on=["match"], right_on=[right_fuzzy_on], how=how)
        
    # fill in score when merge is not an "inner" join.
    dfm["score"].fillna(0.0, inplace=True)
    dfm.fillna("", inplace=True)
    dfm["score"] = dfm.apply(lambda x: x["score"] if x[right_fuzzy_on] != "" and x[left_fuzzy_on] != "" else 0.0, axis=1)
    dfm["match"] = dfm.apply(lambda x: x["match"] if x[right_fuzzy_on] != "" and x[left_fuzzy_on] != "" else "", axis=1)
    return dfm


def author_match(target_author, source_authors, threshold):
    """Return the best name match score (0-1) for a PI with a list of authors"""
    target_author = target_author.replace(".", "")
    target_author = unicodedata.normalize('NFD', target_author)
    initial = target_author.split(" ", maxsplit=1)[-1]
    targetInitial = initial[:1]
    if not isinstance(source_authors, list):
        source_authors = [source_authors]
        
    score = 0
    match = ""
    for author in source_authors:
        author = author.replace(".", "")
        author = unicodedata.normalize('NFD', author)
        initial = author.split(" ")[-1]
        sourceInitial = initial[:1]
        if targetInitial != sourceInitial:
            continue
            
        # TODO use preprocess option to strip/lower
        #jw = jaro_winkler(author.strip().lower(), target_author.strip().lower(), score_cutoff=threshold, prefix_weight=0.25)
        jw = jaro_winkler(author.strip().lower(), target_author.strip().lower(), score_cutoff=threshold, prefix_weight=0.1)
        if jw > score and jw >= threshold:   
            score = jw
            match = author

    return match, score


def fuzzy_merge2(df1, df2, left_fuzzy_on, right_fuzzy_on, left_on=None, right_on=None, how="inner", threshold=0.9):
    dfm = df1.copy()
    right_names = df2[right_fuzzy_on].tolist()
    dfm["match"] = dfm[left_fuzzy_on].apply(lambda x: author_match2(x, right_names, threshold))
    dfm = dfm.explode("match")
    if left_on and right_on:
        dfm = dfm.merge(df2, left_on=["match", left_on], right_on=[right_fuzzy_on, right_on], how=how)
    else:
        dfm = dfm.merge(df2, left_on=["match"], right_on=[right_fuzzy_on], how=how)
        
    # fill in score when merge is not an "inner" join.
    dfm.fillna("", inplace=True)
    dfm["match"] = dfm.apply(lambda x: x["match"] if x[right_fuzzy_on] != "" and x[left_fuzzy_on] != "" else "", axis=1)
    return dfm


def author_match2(target_author, source_authors, threshold):
    """Return the best name match score (0-1) for a PI with a list of authors"""
    target_author = target_author.replace(".", "")
    target_author = unicodedata.normalize('NFD', target_author)
    initial = target_author.split(" ", maxsplit=1)[-1]
    targetInitial = initial[:1]
    if not isinstance(source_authors, list):
        source_authors = [source_authors]
        
    score = 0
    matches = []
    for author in source_authors:
        author = author.replace(".", "")
        author = unicodedata.normalize('NFD', author)
        initial = author.split(" ")[-1]
        sourceInitial = initial[:1]
        if targetInitial != sourceInitial:
            continue

        jw = jaro_winkler(author.strip().lower(), target_author.strip().lower(), score_cutoff=threshold, prefix_weight=0.1)
        if  jw >= threshold:   
            matches.append(author)


    return matches

# def download_dbgap_studies(query, filepath):
#     query_dbgap(query)
#     download_studies_file(filepath)


# def query_dbgap(query):
#     options = webdriver.ChromeOptions()
#     options.add_argument('--headless')
#     # options.add_experimental_option("prefs", {"download.default_directory": "/tmp"}) # doesn't set download dir?
#     driver = webdriver.Chrome(options=options)
#     driver.get(f"https://www.ncbi.nlm.nih.gov/gap/advanced_search/?TERM={query}")
#     time.sleep(3)
#     #print(driver.title)
#     button = driver.find_element(By.CLASS_NAME, "svr_container")
#     time.sleep(3)
#     button.click()
#     time.sleep(15)


# def download_studies_file(filepath):
#     # there should be only one csv file, but the name is unknown.
#     files = glob.glob("*.csv")
#     if len(files) > 0:
#         shutil.move(files[0], filepath)
#     else:
#         print("query error")
        
        
# def get_download_url(accession):
#     return "https://www.ncbi.nlm.nih.gov/projects/gap/cgi-bin/GetAuthorizedRequestDownload.cgi?study_id=" + accession


# def get_authorized_requests(studies):
#     authorized_requests = pd.DataFrame()

#     for _, row in tqdm(studies.iterrows(), total=studies.shape[0]):
#         try:
#             df = pd.read_csv(get_download_url(row["accession"]), 
#                              usecols=["Requestor", "Affiliation", "Project", "Date of approval", "Request status", 
#                                       "Public Research Use Statement", "Technical Research Use Statement"],
#                             sep="\t")
#             df["accession"] = row["accession"]
#             df["name"] = row["name"]
#             authorized_requests = pd.concat([authorized_requests, df], ignore_index=True)
#         except:
#             print(f"Skipping: {row['accession']} - no data.")
                                        
#     return authorized_requests