from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from core.database import get_db
from modules.Auth.schemas import AccessToken
from modules.project_connections.models import Projects
from modules.Auth.models import Users
from datetime import UTC
from  modules.project_connections.schemas import ProjectCreate
from uuid import uuid4
from core.logger import logger
router = APIRouter(tags=["PROJECT CONNECTIONS"])

@router.put("/update-project/{project_id}")
async def update_project(project_id: str, project: ProjectCreate, token_data: AccessToken, db: Session = Depends(get_db)):
    try:
        user = db.query(Users).filter(Users.verification_token == token_data.access_token).first()
        
        if not user or not user.isVerified:
            raise HTTPException(status_code=401, detail="Invalid token or unauthorized user")

        existing_project = db.query(Projects).filter(Projects.project_id == project_id).first()
        
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        if existing_project.user_id!= user.user_id:
            raise HTTPException(status_code=401, detail="Unauthorized user")

        existing_project.project_name = project.project_name
        existing_project.payload_type = project.payload_type
        existing_project.pyload_base_url = project.payload_base_url
        existing_project.payload_method = project.payload_method
        existing_project.payload_route = project.payload_route
        existing_project.payload_headers = project.payload_headers
        existing_project.payload_body = str(project.payload_body)
        existing_project.is_active = project.is_active
        existing_project.test_interval_in_hrs = project.test_interval_in_hrs

        db.commit()
        db.refresh(existing_project)
        logger.info(f"Project with ID {project_id} updated successfully")

        return {"status": "ok", "message": "Project updated successfully"}

    except Exception as e:
        logger.error(f"Error updating project: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@router.delete("/delete-project/{project_id}")
async def delete_project(project_id: str, token_data: AccessToken, db: Session = Depends(get_db)):
    try:
        user = db.query(Users).filter(Users.verification_token == token_data.access_token).first()
        
        if not user or not user.isVerified:
            raise HTTPException(status_code=401, detail="Invalid token or unauthorized user")

        existing_project = db.query(Projects).filter(Projects.project_id == project_id).first()
        
        if not existing_project:
            raise HTTPException(status_code=404, detail="Project not found")

        if existing_project.user_id!= user.user_id:
            raise HTTPException(status_code=401, detail="Unauthorized user")

        db.delete(existing_project)
        db.commit()
        logger.info(f"Project with ID {project_id} deleted successfully")   

        return {"status": "ok", "message": "Project deleted successfully"}

    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@router.post("/total-projects/")
async def total_projects(token_data: AccessToken, db: Session = Depends(get_db)):
    try:
        user = db.query(Users).filter(Users.verification_token == token_data.access_token).first()
        
        if not user or not user.isVerified:
            raise HTTPException(status_code=401, detail="Invalid token or unauthorized user")

        total_projects = db.query(Projects).filter(Projects.user_id == user.user_id).count()
        logger.info(f"Total projects retrieved successfully")

        return {"status": "ok", "message": "Total projects retrieved successfully", "total_projects": total_projects}

    except Exception as e:
        logger.error(f"Error retrieving total projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()


@router.post("/all-projects/")
async def all_projects(token_data: AccessToken, db: Session = Depends(get_db)):
    try:
        user = db.query(Users).filter(Users.verification_token == token_data.access_token).first()
        
        if not user or not user.isVerified:
            raise HTTPException(status_code=401, detail="Invalid token or unauthorized user")

        projects = db.query(Projects).filter(Projects.user_id == user.user_id).all()
        logger.info(f"All projects retrieved successfully for user {user.user_id}")

        return {"status": "ok", "message": "All projects retrieved successfully", "projects": projects}

    except Exception as e:
        logger.error(f"Error retrieving all projects: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        db.close()