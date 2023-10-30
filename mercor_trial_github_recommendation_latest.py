# -*- coding: utf-8 -*-
"""Mercor_Trial_GitHub_Recommendation_Latest.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1pff120wUgHUtwO49ceoZd1AqGzc1k9Zc

# Mercor Trial Task - GitHub Recommendation

## Initialize Embedding Model

We use `text-embedding-ada-002` as the embedding model.
"""

import openai

# initialize openai API key
openai.api_key = "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"  #platform.openai.com

embed_model = "text-embedding-ada-002"

res = openai.Embedding.create(
    input=[
        "Sample document text goes here",
        "there will be several phrases in each batch"
    ], engine=embed_model
)

"""Each vector embedding contains `1536` dimensions (the output dimensionality of the `text-embedding-ada-002` model.

## Initializing the Index

To store these embeddings and enable an efficient vector search through them I used Pinecone.
"""

import pinecone

index_name = 'trial-repo-emb'

# initialize connection to pinecone
pinecone.init(
    api_key="83f50f91-c2e1-4686-bc19-b57f64b2c9ad",  # app.pinecone.io (console)
    environment="us-central1-gcp"  # next to API key in console
)

# connect to index
index = pinecone.Index(index_name)
# index = pinecone.GRPCIndex(index_name)
# view index stats
index.describe_index_stats()

"""## Retrieval

Create a query vector to search through our vector db. We will retrieve the most relevant chunks from the GitHub parsed data.
"""

query = "computer vision project for object detection"

lang_list = []
with open('unique_languages.json', 'r') as json_file:
    lang_list = json.load(json_file)

lang_list

# Convert the list to a string
languages_str = ', '.join(lang_list)
print(languages_str)

filter_on_lang_query = "{ 'Query':'" + query + "'," + "'lang_list':'" + languages_str + "'}"

filter_on_lang_query

# system message to 'prime' the model
primer = """ You are a highly specialized content retrieval system programmed to identify relevant coding languages
from a given list ('languages_list') based on user queries. Your task is to evaluate the 'languages_list' in the
context of the query specified in 'Query'. Return the most relevant coding languages as a list of strings in the
format: ['Language1', 'Language2', ...]. Make sure to scrutinize each language in 'languages_list'
to determine its relevance to the query. If no relevant information can be found based on the data provided,
your response should be "I don't know".".
"""

res_lang = openai.ChatCompletion.create(
    model="gpt-4",
    messages=[
        {"role": "system", "content": primer},
        {"role": "user", "content": filter_on_lang_query}
    ]
)

lang_filtered_list = res_lang['choices'][0]['message']['content']

import ast

filtered_output_list = ast.literal_eval(lang_filtered_list)
print(filtered_output_list)

res = openai.Embedding.create(
    input=[query],
    engine=embed_model
)

# retrieve from Pinecone
query_embeddings = res['data'][0]['embedding']

# get relevant contexts (including the questions)
relevant_repos = index.query(query_embeddings,
                  top_k=5,
                  include_metadata=True,
                 filter={
                        "coding_language": { "$in": filtered_output_list }
                })

relevant_repos

filtered_repo_names = [match['metadata']['repo_name'] for match in relevant_repos['matches']]
print(filtered_repo_names)

# connect to chunk index
chunk_data_index = pinecone.Index('trial-1024-small')
# index = pinecone.GRPCIndex(index_name)
# view index stats
chunk_data_index.describe_index_stats()

def query_repos_by_name(index, xq, filtered_repo_names, top_k=3):
    results_dict = {}

    for repo_name in filtered_repo_names:
        # Run the query for the specific repo_name
        res = index.query(
            xq,
            top_k=top_k,
            include_metadata=True,
            filter={
                "repo_name": { "$eq": repo_name }
            }
        )

        # Extract relevant information from the query result
        matches = res.get('matches', [])
        if matches:
            # Assuming you want the 'text' from each match's metadata
            texts = [match.get('metadata', {}).get('text', '') for match in matches]
            # Concatenate texts into a single string
            concatenated_text = ' '.join(texts)
            results_dict[repo_name] = concatenated_text
        else:
            results_dict[repo_name] = "No relevant information found"

    return results_dict

# Example usage:
result = query_repos_by_name(chunk_data_index, query_embeddings, filtered_repo_names)

result

"""### Defined a method to extract relevant info from the response such as id, chunk, repo_name and text. I convert it into specific format and convert it into string so that I can combine it with the original query, and use GPT4 to get reasoning for choosing the top k chunks.

## Retrieval Augmented Generation

So far we have the top k results (chunks) that are relevant to the input query. To generate 2-3 sentences regarding why they are relevant, I used gpt4. I input the extracted results along with the query. I also define a query template, to give a better context to the system about the task that needs to be performed by the gpt4 system.
"""

def run_augmented_queries(model, primer, query, result_dict):
    augmented_results = {}

    for repo_name, context_text in result_dict.items():
        augmented_query = "{ 'Query':'" + query + "'," + "'context_text':'" + context_text + "'}"

        # Run the GPT-4 query
        filtered_repo_explanation = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": primer},
                {"role": "user", "content": augmented_query}
            ]
        )

        # Extract just the generated content
        generated_content = filtered_repo_explanation.get('choices', [{}])[0].get('message', {}).get('content', '')

        # Store the explanation result against the repo_name
        augmented_results[repo_name] = generated_content

        print("Generated result:", augmented_results)

        break

    return augmented_results

result.keys()

# Example usage
model = "gpt-4"
primer = """
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
query = "computer vision project for object detection"
result_dict = result  # Assuming 'result' contains the output from the previous function

augmented_results = run_augmented_queries(model, primer, query, result_dict)

augmented_results

# Convert the outer dictionary
# outer_dict = ast.literal_eval(augmented_results['DriverFatigueDetectionSystem'])

# Now we will iterate through the outer dictionary and convert inner dictionaries
for key, value in augmented_results.items():
    inner_dict = ast.literal_eval(value)
    outer_dict[key] = inner_dict  # replace the string representation with the actual dictionary

print(outer_dict)