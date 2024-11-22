import os
import re
import uuid
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import OpenAIEmbeddings

def add_document_with_metadata(db, text_splitter, file_path):
    file_name = os.path.basename(file_path)

    # Load the document using PyPDFLoader
    if bool(re.match(r".*\.pdf$", file_path, re.IGNORECASE)):
        loader = PyPDFLoader(file_path)
    else:
        print(f"Skipping unsupported file: {file_path}")
        return

    # Load the data
    data = loader.load()
    print(f"Loaded {len(data)} pages from {file_path}")

    splits = []
    for doc in data:
        print(f"Processing file: {file_path}")
        # Add metadata
        doc.metadata['id'] = str(uuid.uuid4())  # Unique ID
        doc.metadata['source'] = file_path  # File path
        doc.metadata['name'] = file_name  # File name

        # Split the document into chunks
        chunks = text_splitter.split_documents([doc])

        # Propagate metadata to each chunk
        for chunk in chunks:
            chunk.metadata = doc.metadata.copy()  # Ensure each chunk gets a copy of the metadata
            splits.append(chunk)

    # Add documents to the Chroma database
    try:
        db.add_documents(documents=splits)
        print(f"Successfully added {len(splits)} chunks from {file_name} to ChromaDB.")
    except Exception as e:
        print(f"Failed to add documents from {file_name} to ChromaDB: {e}")

def main():
    # Initialize components
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    embeddings = OpenAIEmbeddings()
    db = Chroma(persist_directory='docs/chroma/', embedding_function=embeddings)

    # Path to the folder containing PDFs
    folder_path = "ADWR Blogs"  # Update this to your folder path

    # Check if the folder exists
    if not os.path.isdir(folder_path):
        print(f"Folder not found: {folder_path}")
        return

    # Process all PDFs in the folder
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path) and file_name.lower().endswith('.pdf'):
            add_document_with_metadata(db, text_splitter, file_path)

if __name__ == "__main__":
    main()
