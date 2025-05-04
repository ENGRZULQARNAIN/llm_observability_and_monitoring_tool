from core.database import get_mongodb
from fastapi import (
    APIRouter, UploadFile, File, Depends, HTTPException, 
    BackgroundTasks, Form, status
)
from sqlalchemy.orm import Session
from modules.project_connections.models import Projects
from modules.project_connections.schemas import ProjectCreate
from modules.Auth.models import Users
from fastapi.responses import JSONResponse
from modules.benchmark.file_processer import FileProcessor
from modules.benchmark.qa_generator import QAGenerator
from modules.benchmark.schemas import (
    FileProcessingResponse as SchemaFileProcessingResponse
)
from typing import List
from core.database import get_db
from datetime import datetime
from core.config import get_settings
from core.logger import logger
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from uuid import uuid4
import traceback
import json
import io

router = APIRouter(tags=["Benchmark"])


async def get_file_processor():
    """Dependency to get FileProcessor instance with MongoDB connection."""
    settings = get_settings()
    try:
        db = await get_mongodb(settings=settings)
        return FileProcessor(db)
    except Exception as e:
        logger.error(f"Failed to create FileProcessor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize file processor"
        )


async def get_qa_generator():
    """Dependency to get QAGenerator instance with MongoDB connection."""
    settings = get_settings()
    try:
        db = await get_mongodb(settings=settings)
        return QAGenerator(settings=settings, db=db)
    except Exception as e:
        logger.error(f"Failed to create QAGenerator: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to initialize QA generator"
        )


class TokenData(BaseModel):
    """Schema for authentication token data."""
    access_token: str


@router.post(
    "/process-file", 
    response_model=SchemaFileProcessingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Process files to create benchmark project",
    description=(
        "Upload files and create a new benchmark project. "
        "Files will be processed in the background."
    )
)
async def process_file(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    project_data: str = Form(...),
    access_token: str = Form(...),
    db: Session = Depends(get_db),
    file_processor: FileProcessor = Depends(get_file_processor),
    qa_generator: QAGenerator = Depends(get_qa_generator),
    mongo_db: AsyncIOMotorClient = Depends(get_mongodb),
):
    """
    Process uploaded files and create a benchmark project.
    
    Args:
        background_tasks: FastAPI background tasks manager
        files: List of uploaded files
        project_data: JSON string containing project configuration
        access_token: User authentication token
        db: SQL database session
        file_processor: File processor instance
        qa_generator: QA generator instance
        mongo_db: MongoDB connection
        
    Returns:
        JSONResponse with processing status
        
    Raises:
        HTTPException: For various error conditions
    """
    request_id = str(uuid4())
    logger.info(f"Request {request_id}: Processing file request received")
    
    # Validate input files
    if not files:
        logger.warning(f"Request {request_id}: No files uploaded")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No files uploaded"
        )
    
    # Parse project data
    try:
        project = ProjectCreate(**json.loads(project_data))
        logger.info(
            f"Request {request_id}: "
            f"Project data parsed for {project.project_name}"
        )
    except Exception as e:
        error_msg = f"Invalid project data format: {str(e)}"
        logger.error(f"Request {request_id}: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )
    
    # Process the request
    try:
        # Validate user authentication
        user = db.query(Users).filter(
            Users.verification_token == access_token
        ).first()
        
        if not user:
            logger.warning(
                f"Request {request_id}: User not found with provided token"
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid authentication token"
            )
            
        if not user.isVerified:
            logger.warning(
                f"Request {request_id}: "
                f"Unverified user attempted to create project"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="User account is not verified"
            )
        
        logger.info(
            f"Request {request_id}: User {user.user_id} authenticated"
        )
        
        # Create the project
        project_id = str(uuid4())
        new_project = Projects(
            project_id=project_id,
            user_id=user.user_id,
            project_name=project.project_name,
            content_type=project.content_type,
            target_url=project.target_url,
            end_point=project.end_point,
            header_keys=",".join(project.header_keys),
            header_values=",".join(project.header_values),
            payload_body=str(project.payload_body),
            is_active=project.is_active,
            test_interval_in_hrs=project.test_interval_in_hrs,
            benchmark_knowledge_id=project.benchmark_knowledge_id,
            registered_at=datetime.utcnow()
        )

        # Save project to database
        try:
            db.add(new_project)
            db.commit()
            db.refresh(new_project)
            logger.info(
                f"Request {request_id}: Project {project_id} created "
                f"for user {user.user_id}"
            )
        except Exception as e:
            db.rollback()
            db_error = f"Database error creating project: {str(e)}"
            logger.error(f"Request {request_id}: {db_error}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create project: {str(e)}"
            )
        
        # Read and validate file contents
        file_data = []
        file_validation_errors = []
        total_size = 0
        MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB max per file
        MAX_TOTAL_SIZE = 50 * 1024 * 1024  # 50 MB max total
        
        for file in files:
            # Check file size by reading the file content first
            content = await file.read()
            file_size = len(content)
            
            if file_size > MAX_FILE_SIZE:
                file_validation_errors.append(
                    f"File {file.filename} exceeds maximum size of 20MB"
                )
                continue
                
            total_size += file_size
            if total_size > MAX_TOTAL_SIZE:
                file_validation_errors.append(
                    "Total file size exceeds maximum of 50MB"
                )
                break
            
            # Check file extension
            file_ext = file.filename.lower().split('.')[-1]
            allowed_extensions = ['pdf', 'txt', 'docx', 'md']
            if file_ext not in allowed_extensions:
                file_validation_errors.append(
                    f"File {file.filename} has unsupported extension. "
                    f"Supported: {', '.join(allowed_extensions)}"
                )
                continue
            
            # Store the content we've already read
            file_data.append({
                "filename": file.filename,
                "content": content
            })
        
        # Handle file validation errors
        if file_validation_errors:
            error_message = "; ".join(file_validation_errors)
            logger.warning(
                f"Request {request_id}: File validation errors: "
                f"{error_message}"
            )
            
            # If no valid files at all, roll back the project
            if not file_data:
                db.delete(new_project)
                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"No valid files to process: {error_message}"
                )
        
        # Start background processing
        logger.info(
            f"Request {request_id}: Starting background processing "
            f"of {len(file_data)} files"
        )
        background_tasks.add_task(
            benchmark_creation_background_process,
            request_id=request_id,
            file_data=file_data,
            user_id=user.user_id,
            project_id=new_project.project_id,
            file_processor=file_processor,
            qa_generator=qa_generator,
            db=mongo_db
        )
        
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": "Project creation started",
                "project_id": project_id,
                "status": "processing",
                "errors": (file_validation_errors
                          if file_validation_errors else None)
            }
        )
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Log the full error details
        logger.error(
            f"Request {request_id}: Unexpected error: {str(e)}\n"
            f"{traceback.format_exc()}"
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request"
        )


async def benchmark_creation_background_process(
    request_id: str,
    file_data: List[dict],
    user_id: str,
    project_id: str,
    file_processor: FileProcessor,
    qa_generator: QAGenerator,
    db: AsyncIOMotorClient
):
    """
    Background task to process files and generate QA pairs.
    
    Args:
        request_id: Unique identifier for logging
        file_data: List of dictionaries with filename and content
        user_id: User ID
        project_id: Project ID
        file_processor: File processor instance
        qa_generator: QA generator instance
        db: MongoDB connection
    """
    logger.info(
        f"Request {request_id}: Background processing started "
        f"for project {project_id}"
    )
    
    # Get MongoDB collections
    chunks_collection = db.chunks_collection
    qa_collection = db.qa_collection
    process_status_collection = db.process_status_collection
    
    # Create a status document to track progress
    status_doc = {
        "project_id": project_id,
        "user_id": user_id,
        "status": "processing",
        "started_at": datetime.utcnow(),
        "completed_at": None,
        "files_total": len(file_data),
        "files_processed": 0,
        "chunks_generated": 0,
        "qa_pairs_generated": 0,
        "errors": []
    }
    
    # Insert initial status
    await process_status_collection.insert_one(status_doc)
    
    file_chunks = []
    file_qa_pairs = []
    processed_files = []
    error_files = []

    try:
        # Process each file
        for index, file_info in enumerate(file_data):
            try:
                logger.info(
                    f"Request {request_id}: Processing file "
                    f"{index+1}/{len(file_data)}: {file_info['filename']}"
                )
                
                # Process file into chunks
                chunks = await file_processor.process_file_content(
                    content=file_info["content"],
                    filename=file_info["filename"]
                )
                
                if not chunks:
                    logger.warning(
                        f"Request {request_id}: No chunks generated "
                        f"for file {file_info['filename']}"
                    )
                    error_files.append({
                        "filename": file_info["filename"],
                        "error": "No content chunks could be extracted"
                    })
                    continue
                    
                file_chunks.extend(chunks)
                processed_files.append(file_info["filename"])
                
                # Update status
                await process_status_collection.update_one(
                    {"project_id": project_id},
                    {
                        "$inc": {
                            "files_processed": 1, 
                            "chunks_generated": len(chunks)
                        }
                    }
                )
                
                # Generate QA pairs for each chunk
                chunk_qa_pairs = []
                for chunk in chunks[:2]:
                    try:
                        qa_pairs = await qa_generator.generate_qa(
                            chunk.content
                        )
                        chunk_qa_pairs.extend(qa_pairs)
                    except Exception as e:
                        logger.error(
                            f"Request {request_id}: QA generation failed "
                            f"for chunk in {file_info['filename']}: {str(e)}"
                        )
                        continue
                
                file_qa_pairs.extend(chunk_qa_pairs)
                
                # Update status
                await process_status_collection.update_one(
                    {"project_id": project_id},
                    {"$inc": {"qa_pairs_generated": len(chunk_qa_pairs)}}
                )
                
            except Exception as e:
                error_message = (
                    f"Failed to process file {file_info['filename']}: {str(e)}"
                )
                logger.error(f"Request {request_id}: {error_message}")
                error_files.append({
                    "filename": file_info["filename"],
                    "error": str(e)
                })
                
                # Update errors in status
                await process_status_collection.update_one(
                    {"project_id": project_id},
                    {"$push": {"errors": error_message}}
                )
        
        # Log summary
        logger.info(
            f"Request {request_id}: Generated {len(file_chunks)} chunks and "
            f"{len(file_qa_pairs)} QA pairs from {len(processed_files)} files"
        )
        
        # Create MongoDB documents
        if file_chunks:
            chunk_doc = {
                "project_id": project_id,
                "user_id": user_id,
                "files_processed": processed_files,
                "chunks": [chunk.model_dump() for chunk in file_chunks],
                "timestamp": datetime.utcnow()
            }
            chunk_doc_result = await chunks_collection.insert_one(chunk_doc)
            chunk_doc_id = str(chunk_doc_result.inserted_id)
            logger.info(
                f"Request {request_id}: Saved chunks to MongoDB, "
                f"ID: {chunk_doc_id}"
            )
        else:
            chunk_doc_id = None
            logger.warning(f"Request {request_id}: No chunks to save")
        
        if file_qa_pairs:
            qa_doc = {
                "project_id": project_id,
                "user_id": user_id,
                "files_processed": processed_files,
                "qa_pairs": [qa.model_dump() for qa in file_qa_pairs],
                "timestamp": datetime.utcnow()
            }
            qa_doc_result = await qa_collection.insert_one(qa_doc)
            qa_doc_id = str(qa_doc_result.inserted_id)
            logger.info(
                f"Request {request_id}: Saved QA pairs to MongoDB, "
                f"ID: {qa_doc_id}"
            )
        else:
            qa_doc_id = None
            logger.warning(f"Request {request_id}: No QA pairs to save")
        
        # Update final status
        completion_status = "completed"
        if error_files and not processed_files:
            completion_status = "failed"
        elif error_files:
            completion_status = "completed_with_errors"
            
        await process_status_collection.update_one(
            {"project_id": project_id},
            {
                "$set": {
                    "status": completion_status,
                    "completed_at": datetime.utcnow(),
                    "chunk_doc_id": chunk_doc_id,
                    "qa_doc_id": qa_doc_id,
                    "error_files": error_files
                }
            }
        )
        
        logger.info(
            f"Request {request_id}: Background processing completed "
            f"with status: {completion_status}"
        )
        
    except Exception as e:
        logger.error(
            f"Request {request_id}: Critical error in background processing: "
            f"{str(e)}\n{traceback.format_exc()}"
        )
        
        # Update status to failed
        await process_status_collection.update_one(
            {"project_id": project_id},
            {
                "$set": {
                    "status": "failed",
                    "completed_at": datetime.utcnow(),
                },
                "$push": {"errors": f"Critical error: {str(e)}"}
            }
        )


@router.get(
    "/project-status/{project_id}",
    summary="Get benchmark project processing status",
    description="Check the status of a file processing job for a project"
)
async def get_project_status(
    project_id: str,
    access_token: str,
    db: Session = Depends(get_db),
    mongo_db: AsyncIOMotorClient = Depends(get_mongodb)
):
    """
    Get the status of a benchmark project's file processing.
    
    Args:
        project_id: Project ID to check
        access_token: User authentication token
        db: SQL database session
        mongo_db: MongoDB connection
        
    Returns:
        Processing status information
    """
    # Validate user authentication
    user = db.query(Users).filter(
        Users.verification_token == access_token
    ).first()
    
    if not user or not user.isVerified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid token or unauthorized user"
        )
    
    # Get project
    project = db.query(Projects).filter(
        Projects.project_id == project_id
    ).first()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Check if user owns the project
    if project.user_id != user.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to access this project"
        )
    
    # Get status from MongoDB
    status_doc = await mongo_db.process_status_collection.find_one(
        {"project_id": project_id}
    )
    if not status_doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processing status not found for this project"
        )
    
    # Convert MongoDB ObjectId to string
    status_doc["_id"] = str(status_doc["_id"])
    
    return JSONResponse(content=status_doc)
