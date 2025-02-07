from core.database import get_mongodb
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from modules.benchmark.file_processer import FileProcessor
from modules.benchmark.qa_generator import QAGenerator
from modules.benchmark.schemas import FileProcessingResponse
from typing import List
from datetime import datetime
from core.database import get_mongodb
from core.config import get_settings
from core.logger import logger
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient

router = APIRouter(tags=["Benchmark"])

async def get_file_processor():
    settings = get_settings()
    db = await get_mongodb(settings=settings)
    return FileProcessor(db)

async def get_qa_generator():
    settings = get_settings()
    db= await get_mongodb(settings=settings)
    return QAGenerator(settings=settings, db=db)



class FileProcessingResponse(BaseModel):
    file_count: int
    chunk_doc_id: str  # ID of the single document containing all chunks
    qa_doc_id: str  # ID of the single document containing all QA pairs
    timestamp: datetime

@router.post("/process-file", response_model=FileProcessingResponse)
async def process_file(
    files: List[UploadFile] = File(...),
    file_processor: FileProcessor = Depends(get_file_processor),
    qa_generator: QAGenerator = Depends(get_qa_generator),
    db: AsyncIOMotorClient = Depends(get_mongodb)
):
    try:
        chunks_collection = db.chunks_collection
        qa_collection = db.qa_collection

        file_chunks = []
        file_qa_pairs = []

        for file in files:
            chunks = await file_processor.process_uploaded_file(file)
            file_chunks.extend(chunks)
            
            for chunk in chunks:
                qa_pairs = await qa_generator.generate_qa(chunk.content)
                file_qa_pairs.extend(qa_pairs)
        logger.info(f"Generated {len(file_chunks)} chunks and {len(file_qa_pairs)} QA pairs")
        
        chunk_doc = {
            "files_processed": [file.filename for file in files],
            "chunks": [chunk.model_dump() for chunk in file_chunks],
            "timestamp": datetime.utcnow()
        }
        chunk_doc_result = await chunks_collection.insert_one(chunk_doc)
        chunk_doc_id = str(chunk_doc_result.inserted_id)
        
        qa_doc = {
            "files_processed": [file.filename for file in files],
            "qa_pairs": [qa.model_dump() for qa in file_qa_pairs],
            "timestamp": datetime.utcnow()
        }
        qa_doc_result = await qa_collection.insert_one(qa_doc)
        qa_doc_id = str(qa_doc_result.inserted_id)
        
        return FileProcessingResponse(
            file_count=len(files),
            chunk_doc_id=chunk_doc_id,
            qa_doc_id=qa_doc_id,
            timestamp=datetime.utcnow()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
