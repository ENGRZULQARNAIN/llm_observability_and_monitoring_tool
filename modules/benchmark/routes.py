from core.database import get_mongodb
from fastapi import (
    APIRouter, UploadFile, File, Depends, HTTPException, 
    BackgroundTasks, Form, status
)
from modules.monitor.models import TestInfo
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
        logger.info(user)
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



@router.get(
    "/qa_data/{project_id}",
    summary="Get paginated QA pairs for a project",
    description="Get QA pairs with pagination support from SQLite database"
)
async def get_qa_pairs_paginated(
    project_id: str,
    page: int = 1,
    page_size: int = 10,
    db: Session = Depends(get_db)
):
    """
    Get paginated QA pairs for a benchmark project from SQLite database.
    
    Args:
        project_id: Project ID to get QA pairs for
        page: Page number (starts from 1)
        page_size: Number of QA pairs per page (default: 10, max: 100)
        db: SQLite database session
        
    Returns:
        JSON response with paginated QA pairs and metadata
        
    Raises:
        HTTPException: For validation errors, not found errors, etc.
    """
    try:
        # Validate pagination parameters
        if page < 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page number must be greater than 0"
            )
        
        if page_size < 1 or page_size > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Page size must be between 1 and 100"
            )
        
        # Validate project_id is not empty
        if not project_id or not project_id.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project ID cannot be empty"
            )
        
        # Get total count of QA pairs for the project
        try:
            total_qa_pairs = db.query(TestInfo).filter(
                TestInfo.project_id == project_id
            ).count()
        except Exception as e:
            logger.error(f"Error counting QA pairs for project {project_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve QA pairs count"
            )
        
        # Check if project has any QA pairs
        if total_qa_pairs == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No QA pairs found for this project"
            )
        
        # Calculate pagination metadata
        total_pages = (total_qa_pairs + page_size - 1) // page_size
        
        # Check if page is out of range
        if page > total_pages:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Page {page} not found. Total pages available: {total_pages}"
            )
        
        # Calculate offset for pagination
        offset = (page - 1) * page_size
        
        # Get paginated QA pairs from database
        try:
            qa_pairs_query = db.query(TestInfo).filter(
                TestInfo.project_id == project_id
            ).offset(offset).limit(page_size).all()
        except Exception as e:
            logger.error(f"Error fetching QA pairs for project {project_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve QA pairs"
            )
        
        # Convert database records to serializable format
        serializable_qa_pairs = []
        try:
            for qa_record in qa_pairs_query:
                qa_pair = {
                    "question": qa_record.question,
                    "student_answer": qa_record.student_answer,
                    "difficulty_level": qa_record.difficulty_level,
                    "factual_answer": qa_record.factual_answer
                }
                serializable_qa_pairs.append(qa_pair)
        except Exception as e:
            logger.error(f"Error serializing QA pairs: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to process QA pairs data"
            )
        
        # Calculate pagination flags
        has_next = page < total_pages
        has_previous = page > 1
        
        # Prepare response data
        response_data = {
            "qa_pairs": serializable_qa_pairs,
            "pagination": {
                "current_page": page,
                "page_size": page_size,
                "total_qa_pairs": total_qa_pairs,
                "total_pages": total_pages,
                "has_next": has_next,
                "has_previous": has_previous,
                "next_page": page + 1 if has_next else None,
                "previous_page": page - 1 if has_previous else None
            }
        }
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=response_data
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions as they are
        raise
    except Exception as e:
        # Log unexpected errors and return generic error response
        logger.error(f"Unexpected error in get_qa_pairs_paginated: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing your request"
        )


@router.get("/get-dashboard-data/{project_id}")
async def get_dash_board_data(
    project_id: str,
    db: Session = Depends(get_db)):
    """
    Returns dashboard data for a given project_id.
    { 
      "data":{
        "last_run": ...,  # latest test time for project_id from test_info
        "bench_mark_data_title": ...,  # project name from projects table
        "avg_hallucination_score": ...,  # see logic below
        "avg_helpfulness": ...  # see logic below
      }
    }
    """
    from modules.monitor.models import TestInfo
    from modules.project_connections.models import Projects
    from sqlalchemy import desc

    # Get project info
    project = db.query(Projects).filter(Projects.project_id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Get all test_info records for this project
    test_records = db.query(TestInfo).filter(TestInfo.project_id == project_id).order_by(desc(TestInfo.last_test_conducted)).all()

    # last_run: latest test time
    last_run = test_records[0].last_test_conducted.isoformat() if test_records else None

    # bench_mark_data_title: project name
    bench_mark_data_title = project.project_name

    # avg_hallucination_score: 0 means hallucination, 1 means no hallucination
    # If hallucination_score is 0, add 1 to hallucination count (means hallucination occurred)
    # If hallucination_score is 1, add 0 (means no hallucination)
    hallucination_sum = 0
    hallucination_count = 0
    for t in test_records:
        if t.hallucination_score is not None:
            if t.hallucination_score == 0:
                hallucination_sum += 1
            # else: add 0
            hallucination_count += 1
    avg_hallucination_score = (hallucination_sum / hallucination_count) if hallucination_count > 0 else None

    # avg_helpfulness: if 0 means not helpful, add 0; if 1 or other, add that value
    helpfulness_sum = 0
    helpfulness_count = 0
    for t in test_records:
        if t.helpfullness_score is not None:
            if t.helpfullness_score == 0:
                helpfulness_sum += 0
            else:
                helpfulness_sum += t.helpfullness_score
            helpfulness_count += 1
    avg_helpfulness = (helpfulness_sum / helpfulness_count) if helpfulness_count > 0 else None

    return JSONResponse(content={
        "data": {
            "last_run": last_run,
            "bench_mark_data_title": bench_mark_data_title,
            "avg_hallucination_score": avg_hallucination_score,
            "avg_helpfulness": avg_helpfulness
        }
    })
    