from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta
from modules.project_connections.models import Projects
from modules.monitor.models import TestInfo
from core.logger import logger
from core.database import get_db, SessionLocal

def project_monitoror():
    """
    Monitor projects based on their testing intervals and last registered time.
    
    Returns:
        List[Project]: List of projects that need testing based on their interval
    """
    db = None
    try:
        logger.info("Running project monitoror...")
        # Get current time
        current_time = datetime.utcnow()
        db = SessionLocal()
        projects = db.query(Projects).all()
        
        for project in projects:
            if project.is_active:
                project_test_info = db.execute(select(TestInfo).filter(TestInfo.project_id == project.project_id)).first()
                if project_test_info is None:
                    logger.info(f"Project {project.project_name} has no test info. Skipping...")
                    # TODO - Call Testing Function Here
                    continue
                
                # Calculate the time difference between the last test and now
                time_diff = current_time - project_test_info.last_test_conducted
                
                if time_diff >= timedelta(hours=project.test_interval_in_hrs):
                    # Add the project to the list of projects that need testing
                    logger.info(f"Project {project.project_name} needs testing. Adding to the list...")
                    # TODO - Call Testing Function Here
        
        return projects
    except Exception as e:
        # Log the error appropriately
        logger.error(f"Error in project_monitoror: {str(e)}")
        raise
    finally:
        if db:
            db.close()