import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

load_dotenv()


def ingest_pdfs():
    print("📄 Processing PDFs...")
    all_docs = []
    data_folder = "./data"

    # Loop through all PDFs in the data folder
    for file in os.listdir(data_folder):
        if file.endswith(".pdf"):
            loader = PyPDFLoader(os.path.join(data_folder, file))
            all_docs.extend(loader.load())

    # Split text into manageable chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_text("\n".join([doc.page_content for doc in all_docs]))

    # Save to Vector DB
    Chroma.from_texts(
        texts=chunks,
        embedding=OpenAIEmbeddings(),
        persist_directory="./db"
    )
    print(f"✅ Indexed {len(chunks)} chunks from your PDFs!")


if __name__ == "__main__":
    ingest_pdfs()