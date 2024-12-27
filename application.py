from fastapi import FastAPI



application = FastAPI()


@application.get("/")
async def read_items():
    return {"version": "v0.0.1"}

