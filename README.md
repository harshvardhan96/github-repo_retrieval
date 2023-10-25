# GitHub Data Retrieval and Analysis System
Overview:

The system is designed to retrieve and analyze GitHub data for specific queries. It reads parsed GitHub data from a JSON file, tokenizes and chunks the text, and then computes embeddings for these chunks. These embeddings are stored in a Pinecone index for efficient vector search. Finally, the system uses GPT-4 to generate reasoning for the top-k relevant chunks to a given query.

Workflow: 

1. Data Collection:

* 'get_user_repos()': It fetches details about all repositories for a given GitHub username. It returns a list of dictionaries, each containing information like the repository name, description, URL, programming language used, star count, and fork count.

* 'get_repo_tree()': It fetches the content of specific repositories. It retrieves the SHA value for the main branch of each repository using get_repo_sha, and then fetches the tree structure. The content of each file in the repository is decoded from base64 format and stored in a dictionary, which is then saved to a JSON file.

2. Data Preparation: 

* get_json_data(): Reads a JSON file and returns its content.

* tiktoken_len(text): Computes the token length of a given text.

* RecursiveCharacterTextSplitter: Splits text into smaller chunks.

3. Embedding Model Initialization:
   
* Initialized the OpenAI API key.
  
* I used "text-embedding-ada-002" embedding model to compute the embeddings.

4. Vector Index Initialization:
   
* Initialized Pinecone vector database to store meta data and embeddings. 

5. Compute and Store Embeddings:

* Divided the tokenized text data into batches.
  
* For each batch, computed the text embeddings.
  
*  Uploaded these embeddings to the initialized vector index.

6. User Query Input:
   
* Defined a text query from the user.
  
*  Created an embedding for the query using the same embedding model.

7. Execute Query and Retrieve Results:
   
* Used the query embedding to search the vector index.
  
*  Retrieved the top 5 most relevant chunks from GitHub repositories.

8. Generate Explanations:
   
* For each of the top 5 repositories returned in the prevous response, I used GPT-4 to generate a brief explanation detailing its relevance to the query.
  
* To do this, I created an augmented query, where I combined the response with the query, and then defined my custom primer to give context to GPT-4 about the task that it needs to perform. The format of the augmented query is :

augmented_query = "{ 'Query':'" + query + "'," + "'chunk_list':'" + transformed_data_str + "'}"

* The response of gpt4 for the system-user based query is. The input to this is the primer (which is basically giving context to the system about how to answer the user input queries, along with the augmented query defined in the previous step. )

[{"id_1":, "summary_1":, "relevant_text_1":},{"id_2":, "summary_2":,"relevant_text_2":}]
