from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

# Initialize Chroma with the correct directory and embedding function
persist_directory = 'docs/chroma/'
embeddings = OpenAIEmbeddings()
db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

def retrieve_documents_by_source(db, source_query):
    # Using the 'get' method to filter collection based on metadata
    filtered_docs = db.get(where={"source": source_query})
    return filtered_docs

def write_documents_to_file(docs, file_path):
    with open(file_path, 'w', encoding='utf-8') as file:
        for idx, doc_id in enumerate(docs['ids']):
            file.write(f"Document ID: {doc_id}\n")
            file.write(f"Document Metadata: {docs['metadatas'][idx]}\n")
            document_content = docs['documents'][idx][:200]  # Get first 200 characters
            file.write(f"Document Content (Snippet): {document_content}...\n")
            file.write("-" * 40 + "\n")

# Example usage
if __name__ == "__main__":
    source_to_query = "newData\\100+ Water Saving Tips.pdf"
    found_documents = retrieve_documents_by_source(db, source_to_query)
    
    if found_documents['ids']:
        print(f"Found {len(found_documents['ids'])} documents with the specified source.")
        output_file = "retrieved_documents.txt"
        write_documents_to_file(found_documents, output_file)
        print(f"All documents have been written to {output_file}")
    else:
        print("No documents found with the specified source.")