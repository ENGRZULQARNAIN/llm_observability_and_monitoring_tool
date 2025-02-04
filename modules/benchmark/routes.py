from fastapi import APIRouter, Depends, HTTPException

from core.database import get_mongodb


router = APIRouter(tags=["Benchmark"])

@router.get("/benchmark")
async def benchmark(db = Depends(get_mongodb)):
    db.benchmark.insert_one({"message": "Benchmarking..."})
    return {"message": "Benchmarking..."}