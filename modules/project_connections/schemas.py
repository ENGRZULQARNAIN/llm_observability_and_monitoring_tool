from pydantic import BaseModel
from typing import Dict,List
class ProjectCreate(BaseModel):
    project_name: str
    content_type: str
    target_url: str
    end_point: str
    header_keys: List[str]
    header_values:List[str]
    payload_body: str
    is_active: bool
    test_interval_in_hrs: float
    benchmark_knowledge_id: str


class ProjectUpdate(BaseModel):
    project_id: str
    project_name: str
    content_type: str
    target_url: str
    end_point: str
    header_keys: List[str]
    header_values:List[str]
    is_active: bool
    test_interval_in_hrs: float
    benchmark_knowledge_id:str