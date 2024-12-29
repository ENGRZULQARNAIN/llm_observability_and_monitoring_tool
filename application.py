import os
import sys
from pathlib import Path
from modules import services
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


# Get the absolute path to your app directory
BASE_DIR = Path(__file__).resolve().parent

# Add the app directory to Python path
sys.path.append(str(BASE_DIR))
from core.database import create_tables
from modules.Auth import auth_routers
print("Python path:", sys.path)
print("Current working directory:", os.getcwd())
print("Base directory:", BASE_DIR)

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
    return {"message":"OBAM AI version v0.0.7"}


application.include_router(auth_routers.router)

application.include_router(services.router)

# if __name__ == "__main__":
#     create_tables()