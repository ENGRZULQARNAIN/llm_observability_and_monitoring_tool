from core.database import get_mongodb
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
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
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    file_processor: FileProcessor = Depends(get_file_processor),
    qa_generator: QAGenerator = Depends(get_qa_generator),
    db: AsyncIOMotorClient = Depends(get_mongodb),
):
    try:
        # Read file contents before passing to background task
        file_data = []
        for file in files:
            content = await file.read()
            file_data.append({
                "filename": file.filename,
                "content": content
            })
        
        background_tasks.add_task(
            benchmark_creation_background_process,
            file_data=file_data,  # Pass file_data instead of files
            file_processor=file_processor,
            qa_generator=qa_generator,
            db=db
        )
        return JSONResponse(content={"message": "File processing started"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def benchmark_creation_background_process(
    file_data: List[dict],  # Changed parameter type
    file_processor: FileProcessor = Depends(get_file_processor),
    qa_generator: QAGenerator = Depends(get_qa_generator),
    db: AsyncIOMotorClient = Depends(get_mongodb)):
    
    chunks_collection = db.chunks_collection
    qa_collection = db.qa_collection

    file_chunks = []
    file_qa_pairs = []

    for file_info in file_data:
        chunks = await file_processor.process_file_content(
            content=file_info["content"],
            filename=file_info["filename"]
        )
        file_chunks.extend(chunks)
        
        for chunk in chunks:
            qa_pairs = await qa_generator.generate_qa(chunk.content)
            file_qa_pairs.extend(qa_pairs)
    logger.info(f"Generated {len(file_chunks)} chunks and {len(file_qa_pairs)} QA pairs")
    
    chunk_doc = {
        "files_processed": [file_info["filename"] for file_info in file_data],  # Fixed: use file_data instead of files
        "chunks": [chunk.model_dump() for chunk in file_chunks],
        "timestamp": datetime.utcnow()
    }
    chunk_doc_result = await chunks_collection.insert_one(chunk_doc)
    chunk_doc_id = str(chunk_doc_result.inserted_id)
    
    qa_doc = {
        "files_processed": [file_info["filename"] for file_info in file_data],  # Fixed: use file_data instead of files
        "qa_pairs": [qa.model_dump() for qa in file_qa_pairs],
        "timestamp": datetime.utcnow()
    }
    qa_doc_result = await qa_collection.insert_one(qa_doc)
    qa_doc_id = str(qa_doc_result.inserted_id)