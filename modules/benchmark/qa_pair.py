from pydantic import Field
from datetime import datetime
from pydantic import BaseModel

class QAPair(BaseModel):
    question: str
    answer: str
    defficulty_level: str
