import os
import requests
import json
import time
import pandas as pd
from dotenv import load_dotenv

CHUNK_SIZE = 500
# Semantic Scholar rate limit 1 request per second
RATE_LIMIT = 1

def get_s2_apikey():
    load_dotenv()
    apikey = os.getenv("S2_API_KEY")
    if not apikey:
        print("Proceeding without S2_API_KEY")
    return apikey


def get_paper_data(paper_ids, fields, apikey):
    """
    API description: https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/post_graph_get_papers
    
    The following types of IDs are supported:
    <sha> - a Semantic Scholar ID, e.g. 649def34f8be52c8b66281af98ae884c09aef38b
    CorpusId:<id> - a Semantic Scholar numerical ID, e.g. 215416146
    DOI:<doi> - a Digital Object Identifier, e.g. DOI:10.18653/v1/N18-3011
    ARXIV:<id> - arXiv.rg, e.g. ARXIV:2106.15928
    MAG:<id> - Microsoft Academic Graph, e.g. MAG:112218234
    ACL:<id> - Association for Computational Linguistics, e.g. ACL:W12-3903
    PMID:<id> - PubMed/Medline, e.g. PMID:19872477
    PMCID:<id> - PubMed Central, e.g. PMCID:2323736
    URL:<url> - URL from one of the sites listed below, e.g. URL:https://arxiv.org/abs/2106.15928v1
    URLs are recognized from the following sites:

    semanticscholar.org
    arxiv.org
    aclweb.org
    acm.org
    biorxiv.org
    """

    chunks = create_chunks(paper_ids, CHUNK_SIZE)

    all_data = get_paper_data_chunk(chunks[0], fields, apikey)
    # #print(all_data)
    for chunk in chunks[1:]:
        time.sleep(RATE_LIMIT)
        data = get_paper_data_chunk(chunk, fields, apikey)
        all_data = all_data + data

    return all_data


def get_paper_data_chunk(paper_ids, fields, apikey):
    """
    API description: https://api.semanticscholar.org/api-docs/graph#tag/Paper-Data/operation/post_graph_get_papers
    
    The following types of IDs are supported:
    <sha> - a Semantic Scholar ID, e.g. 649def34f8be52c8b66281af98ae884c09aef38b
    CorpusId:<id> - a Semantic Scholar numerical ID, e.g. 215416146
    DOI:<doi> - a Digital Object Identifier, e.g. DOI:10.18653/v1/N18-3011
    ARXIV:<id> - arXiv.rg, e.g. ARXIV:2106.15928
    MAG:<id> - Microsoft Academic Graph, e.g. MAG:112218234
    ACL:<id> - Association for Computational Linguistics, e.g. ACL:W12-3903
    PMID:<id> - PubMed/Medline, e.g. PMID:19872477
    PMCID:<id> - PubMed Central, e.g. PMCID:2323736
    URL:<url> - URL from one of the sites listed below, e.g. URL:https://arxiv.org/abs/2106.15928v1
    URLs are recognized from the following sites:

    semanticscholar.org
    arxiv.org
    aclweb.org
    acm.org
    biorxiv.org
    """
    URL = "https://api.semanticscholar.org/graph/v1/paper/batch"
    HEADERS = {"accept": "application/json"}
    if apikey:
        HEADERS["x-api-key"] = apikey

    params = {"fields": fields}
    json={"ids": paper_ids}
    
    try:
        response = requests.post(URL, headers=HEADERS, params=params, json=json)
        response.raise_for_status()
        data = response.json()
        return data
    except requests.exceptions.HTTPError as error:
        print(f"ERROR: Semantic Scholar HTTP error: {error}")
    except requests.exceptions.RequestException as error:
        print(f"ERROR: Semantic Scholar: {error}")
        
    return []


def get_author_ids(paper_ids):
    #data = get_paper_data(paper_ids, "authors.authorId,authors.name,authors.paperCount,authors.citationCount,authors.hIndex,externalIds")
    apikey = get_s2_apikey()
    data = get_paper_data(paper_ids, "externalIds", apikey)
    time.sleep(RATE_LIMIT)
    id_data = pd.json_normalize(data, errors="ignore")
    
    # remove mismatches (e.g., pmid:37205441 -> return NaN (bioRxiv paper), now published in Small: PMID:37264756)
    id_data.dropna(axis=0, how='all', inplace=True)
    # DOIs are required as the primary key to publications. Ignore entries without a DOI.
    id_data.dropna(subset=["externalIds.DOI"], inplace=True)

    # rename and reorder columns
    col_map = {"paperId": "paperId", "externalIds.PubMed": "pmId", "externalIds.PubMedCentral": "pmcId", "externalIds.DOI": "doi"}
    id_data = rename_and_reorder_columns(id_data, col_map)
    
    # add prefix
    id_data["doi"] = "doi:" + id_data["doi"]

    # use only the matching paper_ids to get author data, otherwise this results in an error
    matching_paper_ids = id_data["paperId"].to_list()
    #data = get_paper_data(matching_paper_ids, "authors.authorId,authors.name,authors.paperCount,authors.citationCount,authors.hIndex")
    data = get_paper_data(matching_paper_ids, "authors.authorId,authors.name,authors.aliases,authors.affiliations,authors.paperCount,authors.citationCount,authors.hIndex,authors.externalIds", apikey)
    author_data = pd.json_normalize(data, record_path=["authors"], meta=["paperId"], errors="ignore")
    author_data.dropna(axis=0, how='all', inplace=True)
    author_data = author_data.astype(str)
    author_data["aliases"] = author_data["aliases"].str.replace(".", "")
    author_data["aliases"] = author_data["aliases"].str.replace("None", "")
    author_data["aliases"] = author_data["aliases"].str.replace("['","")
    author_data["aliases"] = author_data["aliases"].str.replace("']","")
    author_data["aliases"] = author_data["aliases"].str.replace("'","")
    author_data["aliases"] = author_data["aliases"].str.split(",")
    author_data["aliases"] = author_data["aliases"].apply(lambda x: ",".join(x))

    author_data["externalIds.DBLP"] = author_data["externalIds.DBLP"].str.replace(".", "")
    author_data["externalIds.DBLP"] = author_data["externalIds.DBLP"].str.replace("['", ",")
    author_data["externalIds.DBLP"] = author_data["externalIds.DBLP"].str.replace("']", ",")
    author_data["externalIds.DBLP"] = author_data["externalIds.DBLP"].str.replace("'", "")
    author_data["externalIds.DBLP"] = author_data["externalIds.DBLP"].str.split(",")
    author_data["externalIds.DBLP"] = author_data["externalIds.DBLP"].apply(lambda x: ",".join(x))

    author_data["names"] = author_data["name"] + "," + author_data["externalIds.DBLP"] + "," + author_data["aliases"]
    author_data["names"] = author_data["names"].str.replace(",,",",")
    author_data = author_data.merge(id_data, on="paperId")
    author_data.fillna("", inplace=True)
    print(f"Number of mismatches: {len(paper_ids) - author_data['paperId'].nunique()}")
    
    return author_data


def get_citations(paper_ids):
    import json
    apikey = get_s2_apikey()
    data = get_paper_data(paper_ids, "externalIds", apikey)
    # print(json.dumps(data, indent=2))
    time.sleep(RATE_LIMIT)
    id_data = pd.json_normalize(data)
    
    # remove mismatches (e.g., pmid:37205441 -> return NaN (bioRxiv paper), now published in Small: PMID:37264756)
    id_data.dropna(axis=0, how='all', inplace=True)
    # DOIs are required as the primary key to publications. Ignore entries without a DOI.
    id_data.dropna(subset=["externalIds.DOI"], inplace=True)

    # use only the matching paper_ids to get author data, otherwise this results in an error
    matching_paper_ids = id_data["paperId"].to_list()
    
    data = get_paper_data(matching_paper_ids, "paperId,externalIds,citations.paperId,citations.externalIds,citationCount", apikey)

    df = pd.json_normalize(data, record_path=["citations"], record_prefix="citation.", meta=["paperId", "externalIds","citationCount"])
    df.dropna(subset=["citation.externalIds.DOI"], inplace=True)
    
    df = df.merge(id_data, on="paperId")
    df["doi"] = "doi:" + df["externalIds.DOI"]
    df["doiCite"] = "doi:" + df["citation.externalIds.DOI"]
    return df[["doiCite", "doi"]].copy()



def get_publication_info(paper_ids):
    apikey = get_s2_apikey()
    data = get_paper_data(paper_ids, "title,journal,year,citationCount,externalIds,abstract", apikey)
    df = pd.json_normalize(data, errors="ignore")
    #print(df.head().to_string())
    
    # DOIs are required as the primary key to publications. Ignore entries without a DOI.
    df.dropna(subset=["externalIds.DOI"], inplace=True)

    # replace NaN values with empty string and convert data to string
    df["year"] = df["year"].apply(lambda x: str(int(x)) if not pd.isna(x) else "")
    df["externalIds.PubMed"] = df["externalIds.PubMed"].apply(lambda x: str(int(x)) if not pd.isna(x) else "")
    df["externalIds.PubMedCentral"] = df["externalIds.PubMedCentral"].apply(lambda x: str(int(x)) if not pd.isna(x) else "")
    df["citationCount"] = df["citationCount"].apply(lambda x: str(int(x)) if not pd.isna(x) else "")
    #df.fillna("", inplace=True)
    
    # rename and reorder columns
    col_map = {"paperId": "paperId", "title": "title", "journal.name": "journal", "year": "year", 
               "externalIds.PubMed": "pmId", "externalIds.PubMedCentral": "pmcId", 
               "externalIds.DOI": "doi", "citationCount": "citationCount", "abstract": "abstract"}
    df = rename_and_reorder_columns(df, col_map)

    # add prefix
    df["doi"] = "doi:" + df["doi"]
    
    return df


def get_embeddings(paper_ids):
    apikey = get_s2_apikey()
    data = get_paper_data(paper_ids, ["embedding.specter_v2"], apikey)
    #print(data)
    df = pd.json_normalize(data)
    print(df.columns)
    return df


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
        

def add_relevance_score(df, columns, distance):
    # weight factors for relevance score calculation
    ALPHA = 0.4 # constant based on distance (1: primary, 2: secondary publication, ...)
    BETA = 0.6 # factor for matching relevant terms
    covid_pattern = "COVID-19|COVID19|COVID|2019-nCoV|SARS-CoV-2|Severe Acute Respiratory Syndrome Coronavirus 2|coronavirus|betacoronavirus|" + \
                    "Spike Glycoprotein|MIS-C|Multisystem Inflammatory Syndrome in Children|virus|viral|pandemic|RADx|RADx-rad|RADx-UP|RADx-TECH|RADx-DHT"
    # check for COVID patterns in the specific columns
    df["covid"] = df[columns[0]].str.contains(covid_pattern, case=False)
    for col in columns[1:]:
        df["covid"] = df["covid"] | df[col].str.contains(covid_pattern, case=False)

    # calculate the relevance score
    df["relevance"] = ALPHA**distance + df["covid"].astype(int) * BETA**distance
    df.drop(columns="covid", inplace=True)
    
    return df


def expand_name_column(df, name_column):
    """ Expands a full name (first middle last name) to separate name fields. """
    df[['name', 'fullName', 'firstName', 'middleName', 'lastName']] = df[name_column].apply(lambda x: pd.Series(create_name_cols(x)))


def create_name_cols(full_name):
    """ Split full name into parts. """
    parts = full_name.split(" ")
    first_name = parts[0].replace(".", "")
    last_name = parts[-1]
    middle_name = ""
    middle_initials = ""
    n_middle_initials = len(parts) - 2
    if n_middle_initials > 0:
        for part in parts[1: n_middle_initials+1]:
            middle_name += part
            middle_initials += part[:1]
    middle_name = middle_name.replace(" ", "")
    middle_name = middle_name.replace(".", "")
    # name = last name + initials (used for mapping of names)
    name = last_name + " " + first_name[:1] + middle_initials

    return name, full_name, first_name, middle_name, last_name
