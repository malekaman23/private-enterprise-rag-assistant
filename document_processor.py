"""
document_processor.py
----------------------
Yeh module 'data/' folder ke andar rakhi saari files
(PDF, Word, TXT, CSV) ko padhta hai, chhote-chhote chunks
mein todta hai, taaki LLM asaani se relevant portion dhundh sake.
"""

import os
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    CSVLoader,
)
from langchain_text_splitters import RecursiveCharacterTextSplitter

import config


def load_all_documents(data_dir: str = config.DATA_DIR, only_files: list = None):
    """
    data_dir ke andar ki saari supported files load karta hai.
    Agar 'only_files' diya gaya hai (filenames ki list), to sirf
    unhi files ko process karega - baaki skip ho jayengi (taaki
    purani files dubara process na hon aur duplicate na banein).
    """
    documents = []

    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        print(f"'{data_dir}' folder bana diya gaya. Isme apni files daalo.")
        return documents

    files_to_process = only_files if only_files is not None else os.listdir(data_dir)

    for filename in files_to_process:
        filepath = os.path.join(data_dir, filename)
        if not os.path.isfile(filepath):
            continue
        ext = filename.lower().split(".")[-1]

        try:
            if ext == "pdf":
                loader = PyPDFLoader(filepath)
            elif ext == "docx":
                loader = Docx2txtLoader(filepath)
            elif ext == "txt":
                loader = TextLoader(filepath, encoding="utf-8")
            elif ext == "csv":
                loader = CSVLoader(filepath)
            else:
                print(f"Skip kiya: {filename} (unsupported format)")
                continue

            docs = loader.load()
            # source file ka naam har chunk ke metadata mein daal do
            for d in docs:
                d.metadata["source_file"] = filename
            documents.extend(docs)
            print(f"Loaded: {filename} ({len(docs)} pages/sections)")

        except Exception as e:
            print(f"Error loading {filename}: {e}")

    return documents


def split_documents(documents):
    """Bade documents ko chhote overlapping chunks mein todta hai."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,
        chunk_overlap=config.CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_documents(documents)
    print(f"Total chunks banaye gaye: {len(chunks)}")
    return chunks


def process_documents(only_files: list = None, data_dir: str = config.DATA_DIR):
    """Poora pipeline: load karo + split karo. 'only_files' se specific naye files hi process honge."""
    docs = load_all_documents(data_dir=data_dir, only_files=only_files)
    if not docs:
        return []
    return split_documents(docs)
