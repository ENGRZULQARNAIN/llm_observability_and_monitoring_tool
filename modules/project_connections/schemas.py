from pydantic import BaseModel

class ProjectCreate(BaseModel):
    user_id: str
    project_name: str
    payload_type: str
    payload_base_url: str
    payload_method: str
    payload_route: str
    payload_headers: str
    payload_body: str
    is_active: bool
    test_interval_in_hrs: float
    benchmark_knowledge_id: str