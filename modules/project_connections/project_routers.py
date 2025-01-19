from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from core.database import get_db
from modules.project_connections.models import Projects
from modules.Auth.models import Users
from modules.Auth.dependencies import get_auth_manager
from utils.auth_utils import AuthManager
from datetime import UTC, datetime
from  modules.project_connections.schemas import ProjectCreate

router = APIRouter(tags=["PROJECT CONNECTIONS"])

@router.post("/create-project/")
async def create_project(project: ProjectCreate, db: Session = Depends(get_db), auth_manager: AuthManager = Depends(get_auth_manager)):
    try:
        user = db.query(Users).filter(Users.user_id == project.user_id).first()
        if not user:
            raise HTTPException(status_code=401, detail="Unauthorized user")

        new_project = Projects(
            project_id=str(datetime.now().timestamp()),
            user_id=user.user_id,
            project_name=project.project_name,
            payload_type=project.payload_type,
            pyload_base_url=project.payload_base_url,
            payload_method=project.payload_method,
            payload_route=project.payload_route,
            payload_headers=project.payload_headers,
            payload_body=project.payload_body,
            is_active=project.is_active,
            test_interval_in_hrs=project.test_interval_in_hrs,
            benchmark_knowledge_id=project.benchmark_knowledge_id,
            registered_at=UTC
        )

        db.add(new_project)
        db.commit()
        db.refresh(new_project)

        return JSONResponse(content={"message": "Project created successfully"}, status_code=status.HTTP_201_CREATED)

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()