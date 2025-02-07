from pydantic import BaseModel
from datetime import datetime

class FileProcessingResponse(BaseModel):
    file_count: int
    chunks: list[str]  # List of chunk IDs
    qa_pairs: list[str]  # List of QA pair IDs
    timestamp: datetime