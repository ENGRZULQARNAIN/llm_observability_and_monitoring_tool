from pydantic import BaseModel
from datetime import datetime

class Chunk(BaseModel):
    content: str
    metadata: dict = {}
    created_at: datetime = datetime.utcnow()
