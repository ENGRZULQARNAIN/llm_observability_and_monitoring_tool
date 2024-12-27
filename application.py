import os
import sys
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

# Get the absolute path to your app directory
BASE_DIR = Path(__file__).resolve().parent

# Add the app directory to Python path
sys.path.append(str(BASE_DIR))
from core.database import create_tables
from modules.Auth import auth_routers
print("Python path:", sys.path)
print("Current working directory:", os.getcwd())
print("Base directory:", BASE_DIR)

try:
   
    print("Successfully imported auth_routers")
except ImportError as e:
    print("Failed to import auth_routers:", str(e))

application = FastAPI(title="OBAM AI FYP")

application.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@application.get("/")
async def read_items():
    return {"message":"OBAM AI version v0.0.3"}

application.include_router(auth_routers.router)

# if __name__ == "__main__":
#     create_tables()