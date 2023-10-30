import openai
import pinecone
import json
import re
import ast
import gradio as gr
import io

import tempfile

# Create a temporary file



def initialize_openai(api_key):
    openai.api_key = api_key

def save_to_json(data, file_name):
    with open(file_name, 'w') as f:
        json.dump(data, f)

def get_json_data(file_name):
    with open(file_name, 'r') as json_file:
        return json.load(json_file)

def initialize_pinecone(api_key, environment, index_name):
    pinecone.init(api_key=api_key, environment=environment)
    return pinecone.Index(index_name)

def load_languages_from_json(file_path):
    with open(file_path, 'r') as json_file:
        return json.load(json_file)

def filter_languages(query, lang_list, model, primer):
    languages_str = ', '.join(lang_list)
    filter_on_lang_query = "{ 'Query':'" + query + "'," + "'lang_list':'" + languages_str + "'}"
    res_lang = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": primer},
            {"role": "user", "content": filter_on_lang_query}
        ]
    )
    return ast.literal_eval(res_lang['choices'][0]['message']['content'])

def query_embedding(query, embed_model):
    res = openai.Embedding.create(
        input=[query],
        engine=embed_model
    )
    return res['data'][0]['embedding']

def fetch_relevant_repos(index, query_embeddings, filtered_output_list, top_k=5):
    return index.query(
        query_embeddings,
        top_k=top_k,
        include_metadata=True,
        filter={"coding_language": { "$in": filtered_output_list }}
    )

def query_repos_by_name(chunk_index, query_embeddings, filtered_repo_names, top_k=3):
    results_dict = {}
    for repo_name in filtered_repo_names:
        res = chunk_index.query(
            query_embeddings,
            top_k=top_k,
            include_metadata=True,
            filter={"repo_name": { "$eq": repo_name }}
        )
        matches = res.get('matches', [])
        # results_dict[repo_name] = ' '.join([match.get('metadata', {}) for match in matches]) if matches else "No relevant information found"
        concatenated_metadata = ""
        for item in matches:
            metadata = item.get('metadata')
            if metadata:
                concatenated_metadata += "{ 'Query':'" + metadata['repo_name'] + "'," + "'context_text':'" + metadata['text'] + "}"

        results_dict[repo_name] = concatenated_metadata
    return results_dict


def transform_data_to_string(data):
    transformed_list = []

    matches = data.get('matches', [])

    for match in matches:
        transformed_dict = {}

        transformed_dict['id'] = match.get('id')
        transformed_dict['chunk'] = match.get('metadata').get('chunk')
        transformed_dict['repo_name'] = match.get('metadata').get('repo_name')
        transformed_dict['text'] = match.get('metadata').get('text')

        transformed_list.append(transformed_dict)

    # Convert the list of dictionaries to a JSON-formatted string
    return json.dumps(transformed_list)

def query_on_chunk_data(chunk_index, query_embeddings, filtered_repo_names, top_k=5):
    results_dict = {}
    res = chunk_index.query(
        query_embeddings,
        top_k=top_k,
        include_metadata=True,
        filter={
              "repo_name": {"$in": filtered_repo_names}
        }
    )
    # matches = res.get('matches', [])
    res_str = transform_data_to_string(res)
    return res_str

def run_augmented_queries(model, primer, query, result_dict):
    augmented_results = {}
    for repo_name, context_text in result_dict.items():
        print(f'Running augmented query for: {repo_name}')
        augmented_query = "{ 'Query':'" + query + "'," + "'context_text':'" + context_text + "'}"
        res = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": primer},
                {"role": "user", "content": augmented_query}
            ]
        )
        augmented_results[repo_name] = res.get('choices', [{}])[0].get('message', {}).get('content', '')
    return augmented_results

def run_single_augmented_queries(model, primer, query, res_str):
    augmented_results = {}
    augmented_query = "{ 'Query':'" + query + "'," + "'chunk_list':'" + res_str + "'}"
    print(f'Running augmented query for:')
        # augmented_query = "{ 'Query':'" + query + "'," + "'context_text':'" + context_text + "'}"
    res = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": primer},
                {"role": "user", "content": augmented_query}
            ]
    )
    augmented_results['data'] = res.get('choices', [{}])[0].get('message', {}).get('content', '')
    return augmented_results

def display_augmented_results(augmented_results, run_method):
    result_dict = {}
    if run_method == 'slow':
        for repo_name, value in augmented_results.items():
            inner_dict = ast.literal_eval(value)
            result_dict[repo_name] = inner_dict  # replace the string representation with the actual dictionary
            # Regular expression pattern to match key-value pairs in the dictionary-like string
        return result_dict
    else:
        results = augmented_results['data']
        inner_dict = ast.literal_eval(results)
        # result_dict[repo_name] = inner_dict  # replace the string representation with the actual dictionary
            # Regular expression pattern to match key-value pairs in the dictionary-like string
        return inner_dict

def main(user_input, primer_1):
    api_key = "sk-..."
    embed_model = "text-embedding-ada-002"
    pinecone_api_key = "83f..."
    environment = "us-..."
    repo_index_name = "trial-repo-emb"
    chunk_index_name = "trial-1024-small"
    json_path = 'unique_languages.json'
    gpt_model = "gpt-4"
    # query = "computer vision project for object detection"
    query = user_input

    lang_filter_primer = """ You are a highly specialized content retrieval system programmed to identify relevant coding languages 
from a given list ('languages_list') based on user queries. Your task is to evaluate the 'languages_list' in the 
context of the query specified in 'Query'. Return the most relevant coding languages as a list of strings in the 
format: ['Language1', 'Language2', ...]. Make sure to scrutinize each language in 'languages_list' 
to determine its relevance to the query. If no relevant information can be found based on the data provided, 
your response should be "I don't know".". """

    explain_primer = """
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

    fast_explain_primer = """
    You are a highly intelligent content retrieval system that answers
user queries. Think step by step and thoughtfully. You need to refer to 'context_text' and provide a brief three-sentence explanation detailing why that particular text is relevant to the query mentioned in 'Query'.
Retrieve 1-2 sentence of Python code and do not return plain text that is not Python code that best matches the provided query.
Your answer should be in the format: 
{'repo_name':, 'summary':, 'relevant_code'}
Make sure that you only return the top 5 values, that you think are relevant to the provided user query, and can provide a relevant code for. 
If the information can not be found in the information
provided by the user you truthfully say "I don't know".
    """

    if primer_1 != '':
        explain_primer = primer_1
        print('Updated Primer:', explain_primer)



    final_result_dict = {}

    # Initialize models
    initialize_openai(api_key)
    repo_index = initialize_pinecone(pinecone_api_key, environment, repo_index_name)
    chunk_index = initialize_pinecone(pinecone_api_key, environment, chunk_index_name)

    # Load languages and filter based on the query
    lang_list = load_languages_from_json(json_path)
    filtered_langs = filter_languages(query, lang_list, gpt_model, lang_filter_primer)

    # Query Embedding
    query_embedding_vector = query_embedding(query, embed_model)

    # Fetch Relevant Repos
    relevant_repos = fetch_relevant_repos(repo_index, query_embedding_vector, filtered_langs)
    filtered_repo_names = [match['metadata']['repo_name'] for match in relevant_repos['matches']]


    repo_data = query_repos_by_name(chunk_index, query_embedding_vector, filtered_repo_names)
    # Run augmented queries
    augmented_results = run_augmented_queries(gpt_model, explain_primer, query, repo_data)

    save_to_json(augmented_results,'augmented_results.json')

    # final_result_dict = display_augmented_results(augmented_results, run_method)
    # final_result_dict = get_json_data('/Users/harsh/Documents/TrialWork/augmented_results.json')

    return augmented_results

# if __name__ == "__main__":
#     main()

def fetch_data(input_text, explain_primer = ''):
    # Simulated data fetching logic
    # final_result_dict = main(query)
    # final_result_dict = get_json_data('/Users/harsh/Documents/TrialWork/augmented_results.json')
    final_result_dict = main(input_text, explain_primer)

    temp_file_path_list = []

    for repo, dicts in final_result_dict.items():
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.json', delete=False) as temp_file:
            json.dump(dicts, temp_file)
            temp_file_path =  temp_file.name
            temp_file_path_list.append(temp_file_path)

    tup = []
    for key,val in final_result_dict.items():
        tup.append(str(val))
    tup.append(temp_file_path_list)
    return tup

with gr.Blocks() as app:
    # UI section for user input and triggering data fetch
    gr.Markdown("# Fetch and Display Data")
    with gr.Row():
        with gr.Column():
            user_input = gr.Textbox(label="Input:")
        with gr.Column():
            fast_slow = gr.Text(label="Choose a method: Fast or Slow:")
        with gr.Column():
            primer_1 = gr.Text(label="Edit primer text (optional)")
    fetch_button = gr.Button("Fetch Data")
    download_button = gr.File(label="Download JSON")

    # UI section to display fetched data
    gr.Markdown("## Fetched Data")
    fetched_data_display1 = gr.Text()
    fetched_data_display2 = gr.Text()
    fetched_data_display3 = gr.Text()
    fetched_data_display4 = gr.Text()
    fetched_data_display5 = gr.Text()

    # Bind the button to the data-fetching method and output area
    fetch_button.click(
        fetch_data,
        inputs=[user_input, primer_1],
        outputs=[
            fetched_data_display1,
            fetched_data_display2,
            fetched_data_display3,
            fetched_data_display4,
            fetched_data_display5,
            download_button
        ]
    )

if __name__ == "__main__":
    app.launch()


