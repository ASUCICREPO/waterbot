from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

# Initialize Chroma with the correct directory and embedding function
persist_directory = 'docs/chroma/'
embeddings = OpenAIEmbeddings()
db = Chroma(persist_directory=persist_directory, embedding_function=embeddings)

def delete_documents_by_source(db, source_query):
    # Retrieve documents with the specified source
    filtered_docs = db.get(where={"source": source_query})
    
    if not filtered_docs['ids']:
        print("No documents found with the specified source to delete.")
        return

    # Delete documents by their IDs
    db._collection.delete(ids=filtered_docs['ids'])
    print(f"Deleted {len(filtered_docs['ids'])} documents with the source: {source_query}")

# Example usage
if __name__ == "__main__":
    source_to_delete = "../Data/Water-Saving Tips.txt"
    delete_documents_by_source(db, source_to_delete)