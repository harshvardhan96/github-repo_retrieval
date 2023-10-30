# Readme.md for GitHub Data Retrieval System

## Overview

The code implements a specialized Information Retrieval System that aims to answer user queries about code repositories. The code uses OpenAI GPT-4 for natural language understanding and Pinecone for fast vector search. Two Pinecone indexes are used: 

1. `trial-repo-emb`: Contains embeddings at the repository level, along with metadata like the name of the repository and the programming language used.
2. `trial-1024-small`: Contains chunk-level embeddings of code within repositories.

The code also allows for language filtering and detailed explanations of the relevancy of the fetched data based on different primers. The end-user interface is built using Gradio.

## Approach

### Initialization
1. Initialize OpenAI GPT-4 and Pinecone indexes with API keys.

### Language Filtering
1. Load a pre-existing JSON file containing a list of unique programming languages (`unique_languages.json`).
2. Use GPT-4 to filter these languages based on the query (`filter_languages` function). This is return a list of programming languages that are most relvant for the given user query. 

### Query Embeddings
1. Generate embeddings for the user's query using OpenAI's text embedding model (`query_embedding` function).

### Fetch Relevant Repositories
1. Use the `trial-repo-emb` Pinecone index to find relevant repositories based on the query embedding and filtered languages (`fetch_relevant_repos` function).

### Fetch Chunk-Level Data
1. Use the `trial-1024-small` Pinecone index to retrieve chunk-level data for the filtered repositories (`query_repos_by_name` function).

### Augmented Queries
1. Run additional queries using GPT-4 to provide detailed explanations for why each chunk or repo is relevant to the user query (`run_augmented_queries` function).

### Display Results
1. Display the results in a Gradio UI, including a JSON download option. To run the Gradio UI, run the main.py file after downloading the required dependencies for the project. 

## JSON File Download
The code allows the user to download the JSON file which contains augmented query results. This is achieved by creating a temporary JSON file for each dictionary item, storing the path in a list, and then passing it to the Gradio UI (`download_button`).

## Customizable Primers
It is not recommended to edit the primer drastically since it would change the output format. But if you want to include some additional info, or remove some information from  existing info, you can do so by editing the default primer value given below. 

#### Default Primer Value: 
"""
You are a highly intelligent content retrieval system that answers
user queries. Think step by step and thoughtfully. You need to refer to 'context_text' and provide a brief three-sentence explanation detailing why that particular text is relevant to the query mentioned in 'Query'.
Retrieve 1-2 sentence of programming code and do not return plain text that is not programming code. 
By considering just the programming code present in the context_text, also provide a 1-2 line sentence regarding the technical complexity of programming code. 
Also, consider the context_text and give a 1-2 line sentence about the overall architecture of the repository. 
Also, provide a list of string values of the frameworks/libraries used in the repository. 
Your answer should be in the format of a python dictionary: 
{'repo_name':, 'summary':, 'relevant_code', 'technical complexity':, 'overall architecture':, 'frameworks_used':}
Make sure that you scrutinize the context_text properly before providing the above response. 
If the information can not be found in the information provided by the user you truthfully say "I don't know"
"""

#### Default Output Information Format:
{'repo_name':, 'summary':, 'relevant_code', 'technical complexity':, 'overall architecture':, 'frameworks_used':}

## Dependencies
- OpenAI
- Pinecone
- json
- re
- ast
- Gradio
- io
- tempfile
