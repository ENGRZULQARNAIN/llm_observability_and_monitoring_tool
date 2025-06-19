from pydantic import Field
from datetime import datetime
from pydantic import BaseModel

class QAPair(BaseModel):
    question: str
    answer: str
    difficulty_level: str
