from pydantic import Field
from datetime import datetime
from pydantic import BaseModel

class QAPair(BaseModel):
    question: str
    answer: str
    context: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    verified: bool = False
