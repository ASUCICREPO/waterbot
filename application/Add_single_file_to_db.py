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
        print("Only PDFs are supported in this example.")
        return

    # Load the data
    data = loader.load()
    print("data length:", len(data))

    splits = []
    for doc in data:
        print("Adding : ", file_path)
        # Adding metadata
        doc.metadata['id'] = str(uuid.uuid4())  # Adding unique ID
        doc.metadata['source'] = file_path  # adding path name
        doc.metadata['name'] = file_name  # Adding file name

        # Split the document into chunks
        chunks = text_splitter.split_documents([doc])

        # Propagate metadata to each chunk
        for chunk in chunks:
            chunk.metadata = doc.metadata.copy()  # Ensure each chunk gets a copy of the metadata
            splits.append(chunk)

    # Add documents to the Chroma database
    try:
        db.add_documents(documents=splits)
        print(f"Successfully added {len(splits)} documents to ChromaDB.")
    except Exception as e:
        print(f"Failed to add documents to ChromaDB: {e}")

def main():
    # Initialize components
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1500, chunk_overlap=150)
    embeddings = OpenAIEmbeddings()
    db = Chroma(persist_directory='docs/chroma/', embedding_function=embeddings)

    # Path to your single PDF file
    file_path = "newData/Where does our water come from_ _ Arizona Environment.pdf"  # Update this path to your PDF

    # Add the document
    add_document_with_metadata(db, text_splitter, file_path)

if __name__ == "__main__":
    main()
