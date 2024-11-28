from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from core.database import get_db

router = APIRouter(tags = ["hallucinations_evaluations_router"])

@router.post("/evaluate")
async def evaluate_hallucination(
    text: str,
    db:Session = Depends(get_db)
):
    
    return {"test":"ok"}