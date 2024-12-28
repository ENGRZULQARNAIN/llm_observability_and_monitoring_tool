from fastapi import HTTPException,APIRouter
from fastapi.responses import FileResponse
from modules.Auth.schemas import AccessToken
from core.database import SessionLocal
from modules.Auth.models import Users


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