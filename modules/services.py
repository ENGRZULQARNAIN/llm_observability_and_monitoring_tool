from fastapi import HTTPException,APIRouter
from fastapi.responses import FileResponse
from .Auth.schemas import AccessToken
from core.database import SessionLocal
from .Auth.models import Users
import os


router = APIRouter(tags=["SERVICES"])

@router.post("/download-database")
async def download_database(token_data: AccessToken):
    try:
        # Get user from database
        db = SessionLocal()
        user = db.query(Users).filter(Users.verification_token == token_data.access_token).first()
        
        if not user or not user.isVerified:
            raise HTTPException(status_code=401, detail="Invalid token or unauthorized user")
        
        db_path = "./app_database.db" 
        return FileResponse(
            path=db_path,
            filename="app_database.db",
            media_type="application/octet-stream"
        )
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")
    finally:
        db.close()

@router.get("/download-logs")
async def download_logs():
    # Specify the path to your log file
    log_file_path = "app.log"
    
    # Check if the file exists
    if not os.path.exists(log_file_path):
        raise HTTPException(status_code=404, detail="Log file not found")
    
    # Return the file as a downloadable response
    return FileResponse(
        path=log_file_path,
        filename="app.log",  # This determines the download filename
        media_type="application/octet-stream"  # Forces download in most browsers
    )