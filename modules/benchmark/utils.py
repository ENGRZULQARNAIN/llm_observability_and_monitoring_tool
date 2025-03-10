from app.core.database import SessionLocal
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import Settings
import requests 
from modules.project_connections.models import Projects


llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0.5,
            max_tokens=None,
            timeout=None,
            max_retries=0,
            api_key=settings.GEMINI_API_KEY,
        )



hallucination_prompt = """
You are a teacher grading a quiz. 
You will be given FACTS  and a STUDENT ANSWER. 
Here is the grade criteria to follow:
(1) Ensure the STUDENT ANSWER is grounded in the FACTS. 
(2) Ensure the STUDENT ANSWER does not contain "hallucinated" information outside the scope of the FACTS.
Score:
A score of 1 means that the student's answer meets all of the criteria. This is the highest (best) score. 
A score of 0 means that the student's answer does not meet all of the criteria. This is the lowest possible score you can give.
Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. 
Avoid simply stating the correct answer at the outset.
"""

helpfullness_prompt = """ 
You are a teacher grading a quiz. 

You will be given a QUESTION and a STUDENT ANSWER. 

Here is the grade criteria to follow:
(1) Ensure the STUDENT ANSWER is concise and relevant to the QUESTION
(2) Ensure the STUDENT ANSWER helps to answer the QUESTION

Score:
A score of 1 means that the student's answer meets all of the criteria. This is the highest (best) score. 
A score of 0 means that the student's answer does not meet all of the criteria. This is the lowest possible score you can give.

Explain your reasoning in a step-by-step manner to ensure your reasoning and conclusion are correct. 

Avoid simply stating the correct answer at the outset.
"""



class TestRunner:
    def __init__ (project_id):
        self.project_id = project_id
        self.db = SessionLocal()
    
    def _fetch_qa_by_project_id():
        pass


    def _fetch_payload_info_by_project_id():
        return self.db.query(Projects).filter(Projects.project_id==self.project_id).first()

    def _run_test_for_hallucinations(payload):
        pass

    def _run_test_for_helpfullness(payload):
        results = [1]
        pass

    def _store_results(results):
        pass

    def _run():
        pyload_data = self._fetch_payload_info_by_project_id(self.project_id)

        qa = self._fetch_qa_by_project_id(self.project_id)

        hallucination_result = self._run_test_for_hallucinations()

        helpfullness_result = self._run_test_for_helpfullness()

        self._store_results([hallucination_result,helpfullness_result])





