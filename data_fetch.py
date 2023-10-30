import requests
import base64
import magic
import json
import pandas as pd
import os

# List of file extensions or names to ignore
ignore_list = ['.gitignore', 'LICENSE', '.vscode', '.editorconfig', 'tsconfig.json',
               'tsconfig.app.json', 'tsconfig.spec.json', '.mvn/wrapper', '.github/ISSUE_TEMPLATE', 'mvnw', 'mvnw.cmd', '.config.js', '.webp',
               '.json.gz', '.ico', '.mp4', '.fbx', '.dat', '.pdf', '.ttf', '.DS_Store', '.mp3', '.mp4', '.jar']

# List of directories to ignore
global inside_ignored_dir
inside_ignored_dir = False
ignore_dirs = ['/node_modules', 'node_modules']

df = pd.read_csv('100githubs.csv')
# Assuming df is your DataFrame
usernames_list = df['githubUsername'].tolist()

# Replace 'your_username' with the GitHub username you want to retrieve repository details for
# github_username = 'octosrishti'
token = 'github_...'

headers = {
    'Accept': 'application/vnd.github+json',
    'Authorization': f'Bearer {token}',
    'X-GitHub-Api-Version': '2022-11-28'
}

headers1 = {
    'Authorization': f'Bearer {token}',
    'X-GitHub-Api-Version': '2022-11-28'
}

user_meta_data_list = []

def get_user_repos(github_username):
    # Make a GET request to the GitHub API to retrieve user information
    user_url = f'https://api.github.com/users/{github_username}'
    response = requests.get(user_url, headers=headers1)

    # Create a list to store repository details
    repository_details = []

    if response.status_code == 200:
        user_data = response.json()

        # Get the user's repositories
        repositories_url = user_data['repos_url']
        repositories_response = requests.get(repositories_url, headers=headers1)

        if repositories_response.status_code == 200:
            repositories_data = repositories_response.json()
            # print(repositories_data[0])

            # Iterate through the repositories and store details in a list of dictionaries
            for repo in repositories_data:
                repo_info = {
                    "Repository Name": repo['name'],
                    "Description": repo['description'],
                    "URL": repo['url'],
                    "Language": repo['language'],
                    "Stars": repo['stargazers_count'],
                    "Forks": repo['forks_count']
                }
                repository_details.append(repo_info)

            return repositories_data
        else:
            print(f"Failed to retrieve repositories for {github_username}.")
    else:
        print(f"User {github_username} not found on GitHub.")


repo_names = []


def get_repo_sha(owner, repo_name, branch="main"):
    # Set the required headers

    api_url = f'https://api.github.com/repos/{owner}/{repo_name}/git/trees/{branch}'
    response = requests.get(api_url, headers=headers)

    if response.status_code == 404:
        # Return None to indicate that the repository or branch doesn't exist
        return None
    elif response.status_code == 200:
        data = response.json()
        return data['sha']
    else:
        # Handle other response codes as needed
        return None

def get_repo_tree(owner, repo_name, sha_val):
    # Define the URL for the tree
    tree_url = f'https://api.github.com/repos/{owner}/{repo_name}/git/trees/{sha_val}?recursive=1'
    print(tree_url)

    # Set the required headers
    headers = {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {token}',
        'X-GitHub-Api-Version': '2022-11-28'
    }

    # Send a GET request to fetch the tree data
    response = requests.get(tree_url, headers=headers)

    content_list = {}

    if response.status_code == 200:
        tree_data = response.json()

        # print("Tree Data:", tree_data)
        # Create a magic object for file type detection
        magic_obj = magic.Magic()

        # Iterate through the tree entries and fetch content for blobs
        for entry in tree_data.get('tree', []):
            global inside_ignored_dir

            if any(ignore_dir in entry['path'] for ignore_dir in ignore_dirs):
                inside_ignored_dir = True

                # Skip the current entry if inside an ignored directory
            if inside_ignored_dir:
                print(f"Skipping {entry['path']} due to being inside an ignored directory.")
                inside_ignored_dir = False  # Reset the flag when exiting the directory
                continue


            if entry['type'] == 'blob':
                file_url = entry['url']
                file_response = requests.get(file_url, headers=headers)
                if file_response.status_code == 200:
                    file_content = file_response.json().get('content')
                    # Detect the file type
                    file_type = magic_obj.from_buffer(base64.b64decode(file_content))

                    # Check if the file is text (you can adjust the condition as needed)
                    # Skip files that match the ignore list or are images
                    if any(entry['path'].endswith(ignore_item) for ignore_item in ignore_list) or 'image' in file_type or any(ignore_dir in entry['path'] for ignore_dir in ignore_dirs):
                        print(f"Skipping {entry['path']} due to filtering criteria.")
                    else:
                        # content_list[entry['path']] = "Binary or non-text content"
                        # Decode the base64-encoded content to get the text
                        try:
                            text_content = base64.b64decode(file_content).decode('utf-8')
                            content_list[entry['path']] = text_content
                        except UnicodeDecodeError:
                            # Handle the case where the content is not valid UTF-8
                            content_list[entry['path']] = " "

                            # Extract and add the file extension to the ignore_list
                            filename = entry['path']
                            file_extension = filename.split('.')[-1]  # Get the extension
                            ignore_list.append('.'+ file_extension)
                            print(f"Added {file_extension} to the ignore list.", file_extension)
                else:
                    print(f"Failed to retrieve content for {entry['path']}. Status code: {file_response.status_code}")
    else:
        print(f"Failed to retrieve tree data. Status code: {response.status_code}")

    return content_list

repo_tree_data = {}
meta_data = []

# Open and read the JSON file
with open('repo_meta_data.json', 'r') as json_file:
    meta_json = json.load(json_file)
    meta_data = meta_json['data']

custom_user_list = ['hrishi12345', 'Shagun20-03', 'Nishantsingh9412', 'saurabhsaini400', 'Anshumanj95', 'ayu913',
                     'meenal2000', 'HarshP4585', 'Awizp', 'skmdsohel']


for user_data in meta_data:
    if user_data['user_name'] in custom_user_list:
        user = user_data['user_name']
        repo_list = user_data['repo_meta_data']

        # Create a directory for the user if it doesn't exist
        user_directory = os.path.join('json_data', user)  # 'user_data' is the parent directory
        os.makedirs(user_directory, exist_ok=True)

        for repo in repo_list:
            repo_filepath = os.path.join(user_directory, f'{repo["name"]}.json')

            # Check if the repo file already exists
            if os.path.exists(repo_filepath):
                print(f"Skipping {repo_filepath} as it already exists in {user_directory}")
                continue

            sha_val = get_repo_sha(user, repo['name'], branch= repo['default_branch'])
            print("SHA", sha_val)
            if sha_val == None:
                continue
            else:
                repo_tree_data['repo_name'] = repo['name']
                repo_tree_data['files'] = get_repo_tree(user, repo['name'], sha_val)

                # Store repo_tree_data as a JSON file in the user's directory
                repo_filename = os.path.join(user_directory, f'{repo["name"]}.json')
                with open(repo_filename, 'w') as json_file:
                    json.dump(repo_tree_data, json_file)








