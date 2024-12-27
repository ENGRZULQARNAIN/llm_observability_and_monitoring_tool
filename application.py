from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path


application = FastAPI()
application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates_path = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(templates_path))



@application.get("/")
async def read_items():
    return {"version": "v0.0.1"}

