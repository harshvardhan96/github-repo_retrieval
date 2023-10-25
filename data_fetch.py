import requests
import base64
import magic
import json

# Replace 'your_username' with the GitHub username you want to retrieve repository details for
github_username = 'octosrishti'
token = 'github_token'
owner = 'octosrishti'
# # Set the GitHub API endpoint for user's repositories
# api_url = f'https://api.github.com/users/{owner}/repos'
# Set the required headers
headers = {
    'Accept': 'application/vnd.github+json',
    'Authorization': f'Bearer {token}',
    'X-GitHub-Api-Version': '2022-11-28'
}

def get_user_repos(github_username):
    # Make a GET request to the GitHub API to retrieve user information
    user_url = f'https://api.github.com/users/{github_username}'
    response = requests.get(user_url)

    # Create a list to store repository details
    repository_details = []

    if response.status_code == 200:
        user_data = response.json()

        # Get the user's repositories
        repositories_url = user_data['repos_url']
        repositories_response = requests.get(repositories_url)

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
        else:
            print(f"Failed to retrieve repositories for {github_username}.")
    else:
        print(f"User {github_username} not found on GitHub.")

    # Now the repository details are stored in the `repository_details` list of dictionaries
    # You can access and manipulate the data as needed.
    # for repo in repository_details:
    #     print("Repository Details:")
    #     for key, value in repo.items():
    #         print(f"{key}: {value}")
    #     print("-" * 50)

    return repository_details

repo_details = get_user_repos(github_username)

repo_names = []

# for repo in repo_details:
#     print(repo['Repository Name'])
#     repo_names.append(repo['Repository Name'])

test_repo_list = ['API_Development', 'Restaurant-poller', 'digital_clock']

def get_repo_sha(owner,repo_name, branch = "main"):
    api_url = f'https://api.github.com/repos/{owner}/{repo_name}/git/trees/{branch}'
    response1 = requests.get(api_url, headers=headers)
    data1 = response1.json()
    return data1['sha']

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
            if entry['type'] == 'blob':
                file_url = entry['url']
                file_response = requests.get(file_url, headers=headers)
                if file_response.status_code == 200:
                    file_content = file_response.json().get('content')
                    # Detect the file type
                    file_type = magic_obj.from_buffer(base64.b64decode(file_content))

                    # Check if the file is text (you can adjust the condition as needed)
                    if 'image' in file_type:
                        # Handle non-text files
                        print("Files that are not valid UTF-8 text should not be decoded as text but should be handled differently. ")
                    else:
                        # content_list[entry['path']] = "Binary or non-text content"
                        # Decode the base64-encoded content to get the text
                        text_content = base64.b64decode(file_content).decode('utf-8')
                        content_list[entry['path']] = text_content
                else:
                    print(f"Failed to retrieve content for {entry['path']}. Status code: {file_response.status_code}")
    else:
        print(f"Failed to retrieve tree data. Status code: {response.status_code}")

    return content_list

repo_tree_data = {}

for repo in test_repo_list:
    sha_val = get_repo_sha(owner,repo)
    print("SHA", sha_val)
    repo_tree_data[repo] = (get_repo_tree(owner, repo,sha_val))

# Save the content_list to a JSON file
with open('repo_text_data.json', 'w') as json_file:
    json.dump(repo_tree_data, json_file, indent=4)
#
# for key, value in repo_tree_data.items():
#     print(f"{key}: {value}")
#     print("-" * 50)








