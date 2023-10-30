import os
import json
import pickle
import openai
import pandas as pd
import pinecone
from uuid import uuid4
from tqdm.auto import tqdm
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tiktoken
import numpy as np
from uuid import uuid4

tokenizer = tiktoken.get_encoding('p50k_base')
unique_languages = set()  # Initialize an empty set to store unique languages

def check_and_create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)

# Initialize services
def init_services(index_name = 'trial-1', index_emb_dim = 1536):
    openai.api_key = "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"
    pinecone.init(api_key="83f50f91-c2e1-4686-bc19-b57f64b2c9ad",  environment="us-central1-gcp")
    if index_name not in pinecone.list_indexes():
        pinecone.create_index(index_name, dimension=index_emb_dim, metric='cosine')

def get_all_folder_names(folder_path):
    all_entries = os.listdir(folder_path)
    folder_names = [os.path.join(folder_path, entry) for entry in all_entries if os.path.isdir(os.path.join(folder_path, entry))]
    return folder_names

# create the length function
def tiktoken_len(text):
    tokens = tokenizer.encode(
        text,
        disallowed_special=()
    )
    return len(tokens)

# Load JSON data
def get_json_data(file_name):
    with open(file_name, 'r') as json_file:
        return json.load(json_file)

# Save data as a pickle file
def save_to_pickle(data, file_name):
    with open(file_name, 'wb') as f:
        pickle.dump(data, f)


def save_to_json(data, file_name):
    with open(file_name, 'w') as f:
        json.dump(data, f)

def read_csv_folders(file_path):
    df = pd.read_csv(file_path)
    github_username_list = df['githubUsername'].tolist()
    return github_username_list

def fetch_json_basenames(root_directory: str):
    try:
        # List all files in the directory
        all_files = os.listdir(root_directory)

        # Extract basename
        repo_names = [os.path.basename(json_file).replace('.json', '') for json_file in all_files]

        return repo_names
    except FileNotFoundError:
        # Handle the case where the directory does not exist
        print('Error in finding the file. ')
        return []


    return user_json_dict


def find_repo_pkl_files(repo_name_list, folder_location):
    # print("Folder Location:",folder_location )
    # List all files and directories in the folder
    all_files_and_dirs = os.listdir(folder_location)
    # print("All files in folder location:", all_files_and_dirs)

    repo_pickle_dict = {}
    try:
        for repo_name in repo_name_list:
            # Filter out directories and focus only on .pkl files that contain the repo_name
            only_repo_pkl_files = [f for f in all_files_and_dirs
                                   if f.endswith('.pkl')
                                   and f.startswith(repo_name)]

            # print("Printing repo pkl files for :", repo_name)
            # print(only_repo_pkl_files)
            repo_pickle_dict[repo_name] = only_repo_pkl_files
        return repo_pickle_dict
    except FileNotFoundError:
        # Handle the case where the directory does not exist
        # return []
        print("Pickle file nto found.")


def compute_mean_embeddings(repo_dict, folder_location, embedding_idx = 1):
    mean_embeddings_dict = {}

    for repo_name, pkl_files in repo_dict.items():
        # Initialize a list to store mean embeddings for each .pkl file
        mean_embeddings_per_file = []

        # Check if pkl_files is not None
        if pkl_files is not None:
            for pkl_file in pkl_files:
                # Create the full path to the .pkl file
                full_path = os.path.join(folder_location, pkl_file)

                # Load list of tuples from .pkl file
                with open(full_path, 'rb') as f:
                    list_of_tuples = pickle.load(f)

                # Extract embeddings from each tuple based on the index
                embeddings_list = [tup[embedding_idx] for tup in list_of_tuples]

                # Convert list of embeddings to NumPy array
                embeddings_array = np.array(embeddings_list)

                # Compute mean of this array only if it is not empty
                if embeddings_array.size != 0:
                    mean_embedding_for_file = np.mean(embeddings_array, axis=0)
                    mean_embeddings_per_file.append(mean_embedding_for_file)
                else:
                    mean_embedding_for_file = np.zeros(1536)

            if mean_embeddings_per_file:
                overall_mean_embedding = np.mean(mean_embeddings_per_file, axis=0)
                mean_embeddings_dict[repo_name] = overall_mean_embedding
            else:
                print('Mean embedding is none for repo:', repo_name)
                mean_embeddings_dict[repo_name] = np.zeros(1536)
        else:
            print(f'No pkl_files found for repo: {repo_name}')

    return mean_embeddings_dict

def get_repo_meta_data(meta_data, target_repo_names):
    user_repo_meta_dict = {}
    for repo_name in target_repo_names:
        for user_data in meta_data:
            for repo_meta in user_data['repo_meta_data']:
                # Only proceed if this repo_name is in target_repo_names
                if repo_meta['name'] == repo_name:
                    user_repo_meta_dict[repo_name] = {}

                    fields_to_check = {
                        'id': 'github_id',
                        'name': 'repo_name',
                        'language': 'coding_language',
                        'description': 'description',
                        'forks_count': 'forks_count',
                        'stargazers_count': 'stargazers_count',
                        'watchers_count': 'watchers_count',
                        'open_issues_count': 'open_issues_count',
                        'updated_at': 'updated_at',
                        'topics': 'topics'
                    }

                    for original_field, new_field in fields_to_check.items():
                        value = repo_meta.get(original_field)

                        if value is not None and value != []:
                            user_repo_meta_dict[repo_name][new_field] = value

                        if value is not None and original_field == 'language':
                            if isinstance(value, list) and all(isinstance(elem, str) for elem in value):
                                unique_languages.update(value)  # Add the string values to the set
                            else:
                                unique_languages.add(value)  # Add the language to the set


    return user_repo_meta_dict


def combine_repo_data(embeddings_dict, metadata_dict):
    combined_list = []

    # Loop through the keys in embeddings_dict
    for repo_name, embeddings in embeddings_dict.items():
        # Get the corresponding metadata. If not present, use an empty dictionary.
        metadata = metadata_dict.get(repo_name, {})

        # Combine repo_id, embeddings, and metadata into a tuple
        combined_data = (str(uuid4()), embeddings.tolist(), metadata)

        # Append the combined data to the list
        combined_list.append(combined_data)

    return combined_list

def upload_data_to_index(index, to_upsert):
    index.upsert(vectors=to_upsert)



# Main execution function
def main():
    chunk_size = 1024
    chunk_overlap = 20
    index_name = 'trial-repo-emb'

    base_json_path = '/Users/harsh/Documents/TrialWork/graphql_json'
    repo_emb_dir = '/Users/harsh/Documents/TrialWork/repo_emb'
    user_names_csv_path = '/Users/harsh/Documents/TrialWork/100githubs.csv'
    chunk_emb_dir = '/Users/harsh/Documents/TrialWork/chunk_embeddings_1024'

    # user_json_folder_names = get_all_folder_names(base_json_path)

    user_json_folder_names = read_csv_folders(user_names_csv_path)

    meta_data_json = get_json_data('repo_meta_data.json')
    meta_data = meta_data_json['data']



    start_i = 0
    end_i = len(user_json_folder_names)
    # end_i = 4

    print(f'Running for Index: {start_i} to {end_i}')

    init_services(index_name)
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size, chunk_overlap=chunk_overlap, length_function=tiktoken_len, separators=["\n\n", "\n", " ", ""]
    )
    index = pinecone.Index(index_name)
    for idx, user_name in enumerate(user_json_folder_names[start_i:end_i]):
        repo_names_for_user = []
        print(f"Running for {idx} and username {user_name}")

        full_user_emb_path = os.path.join(chunk_emb_dir,user_name)
        check_and_create_folder(full_user_emb_path)

        path_to_user_json_folder = os.path.join(base_json_path,user_name)
        repo_names_for_user = fetch_json_basenames(path_to_user_json_folder)
        # print(f"Repo Names for user: {user_name}:")
        # print(repo_names_for_user)

        full_chunk_emb_path = os.path.join(chunk_emb_dir, user_name)
        pkl_files_dict = find_repo_pkl_files(repo_names_for_user,full_chunk_emb_path)

        repo_mean_dict = compute_mean_embeddings(pkl_files_dict, full_chunk_emb_path, embedding_idx = 1)
        # print("Repo mean dict:", repo_mean_dict)

        user_repo_meta_data_dict = get_repo_meta_data(meta_data, repo_names_for_user)
        # print("User Repo Meta Data:", user_repo_meta_data_dict)

        # combined_data_list = combine_repo_data(repo_mean_dict, user_repo_meta_data_dict)

        # print("Data to upload:", type(combined_data_list))

        # upload_data_to_index(index, combined_data_list)

        # process_all_json_files_in_directory(path_to_user_json_folder, text_splitter, index, full_user_emb_path, user_name, combined_text_base_path,repo_combined_texts)
        print("Successfully created embeddings for:", user_name)

    # Convert set to a list and save as JSON
    unique_languages_list = list(unique_languages)
    with open('unique_languages.json', 'w') as f:
        json.dump(unique_languages_list, f)

# Entry point
if __name__ == "__main__":
    main()