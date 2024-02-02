import requests

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
    #return [data[i:i + chunk_size] for i in range(0, len(data), chunk_size
    for i in range(0, len(data), chunk_size):
        yield data[i:i + chunk_size]


def embed_title_abstract(papers):
    URL = "https://model-apis.semanticscholar.org/specter/v1/invoke"
    MAX_BATCH_SIZE = 16
    
    embeddings_by_paper_id: Dict[str, List[float]] = {}

    for chunk in create_chunks(papers, chunk_size=MAX_BATCH_SIZE):
        # Allow Python requests to convert the data above to JSON
        response = requests.post(URL, json=chunk)

        if response.status_code != 200:
            raise RuntimeError("Sorry, something went wrong, please try later!")

        for paper in response.json()["preds"]:
            embeddings_by_paper_id[paper["paper_id"]] = paper["embedding"]

    return embeddings_by_paper_id


def embed_text(text):
    text_dict = [
        {
            "paper_id": "id",
            "title": text,
            "abstract": text,
        }
    ]
    return embed_title_abstract(text_dict)["id"]