from pydantic import BaseModel
from typing import Dict
class ProjectCreate(BaseModel):
    project_name: str
    payload_type: str
    payload_base_url: str
    payload_method: str
    payload_route: str
    payload_headers: str
    payload_body: Dict
    is_active: bool
    test_interval_in_hrs: float
    benchmark_knowledge_id: str