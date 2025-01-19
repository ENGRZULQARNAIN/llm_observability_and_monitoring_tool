from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from core.database import get_db
from modules.Auth.schemas import AccessToken
from modules.project_connections.models import Projects
from modules.Auth.models import Users
from modules.Auth.dependencies import get_auth_manager
from utils.auth_utils import AuthManager
from datetime import UTC, datetime
from  modules.project_connections.schemas import ProjectCreate
from uuid import uuid4
router = APIRouter(tags=["PROJECT CONNECTIONS"])

@router.post("/create-project/")
async def create_project(project: ProjectCreate,token_data:AccessToken ,db: Session = Depends(get_db)):

    try:
        user = db.query(Users).filter(Users.verification_token == token_data.access_token).first()
        
        if not user or not user.isVerified:
            raise HTTPException(status_code=401, detail="Invalid token or unauthorized user")
        
        new_project = Projects(
            project_id= str(uuid4()),
            user_id=user.user_id,
            project_name=project.project_name,
            payload_type=project.payload_type,
            pyload_base_url=project.payload_base_url,
            payload_method=project.payload_method,
            payload_route=project.payload_route,
            payload_headers=project.payload_headers,
            payload_body=str(project.payload_body),
            is_active=project.is_active,
            test_interval_in_hrs=project.test_interval_in_hrs,
            benchmark_knowledge_id=project.benchmark_knowledge_id
        )

        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        return {"status":"ok","message": "Project created successfully"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()