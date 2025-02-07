from langchain_community.document_loaders import PyPDFLoader, TextLoader, UnstructuredFileLoader, Docx2txtLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
import tempfile
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from modules.benchmark.chunk import Chunk
from core.logger import logger
import os

class FileProcessor:
    def __init__(self, db: AsyncIOMotorClient, chunk_size=1000, chunk_overlap=20):
        self.db = db
        self.chunks_collection = self.db.chunks_collection
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len
        )
        
        self.loader_mapping = {
            ".pdf": PyPDFLoader,
            ".txt": TextLoader,
            # Add more file types as needed
        }

    async def process_uploaded_file(self, uploaded_file):
        with tempfile.NamedTemporaryFile(delete=False, suffix=uploaded_file.filename) as tmp:
            content = await uploaded_file.read()
            tmp.write(content)
            tmp_path = tmp.name

        try:
            ext = os.path.splitext(uploaded_file.filename)[-1].lower()
            loader_class = self.loader_mapping.get(ext, UnstructuredFileLoader)
            loader = loader_class(tmp_path)

            documents = loader.load()
            chunks = self.text_splitter.split_documents(documents)

            db_chunks = []
            for i, chunk in enumerate(chunks):
                chunk_data = Chunk(
                    content=chunk.page_content,
                    metadata={
                        "source": uploaded_file.filename,
                        "chunk_number": i + 1,
                        **chunk.metadata
                    }
                )
                db_chunks.append(chunk_data)  # Store in list instead of inserting into DB
            
            return db_chunks
        finally:
            os.unlink(tmp_path)