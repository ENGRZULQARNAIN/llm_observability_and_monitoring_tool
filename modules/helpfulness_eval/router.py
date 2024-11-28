from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db

router = APIRouter(tags = ["helpfulness_evaluations_router"])

@router.post("/evaluate-helpfulness")
async def evaluate_hallucination(
    text: str,
    db:Session = Depends(get_db)
):
    
    return {"test":"ok"}