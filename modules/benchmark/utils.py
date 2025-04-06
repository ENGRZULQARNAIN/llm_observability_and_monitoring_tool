from core.database import SessionLocal, get_mongodb
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import Settings, get_settings
from langchain_core.messages import SystemMessage, HumanMessage
from modules.benchmark.qa_pair import QAPair
import requests
from modules.project_connections.models import Projects
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.logger import logger

settings = get_settings()

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
You will be given FACTS, STUDENT QUESTION  and a STUDENT ANSWER. 
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
    async def __init__(self, project_id):
        self.project_id = project_id
        self.db = SessionLocal()
        self.mongo_db = await get_mongodb(settings=settings)
        self.qa_collection = self.mongo_db.qa_collection
        self.test_collection = self.mongo_db.test_results
    
    def _fetch_qa_by_project_id(self):
        """Fetch QA pairs for project from MongoDB"""
        qa_doc = self.qa_collection.find_one({"project_id": self.project_id})
        if not qa_doc:
            raise ValueError(f"No QA pairs found for project {self.project_id}")
        return [QAPair(**qa) for qa in qa_doc.get("qa_pairs", [])]

    def _fetch_payload_info_by_project_id(self):
        """Fetch project info from SQL database"""
        return self.db.query(Projects).filter(Projects.project_id==self.project_id).first()

    async def _run_test_for_hallucinations(self, qa_pair: QAPair):
        """Evaluate hallucination using Gemini"""
        messages = [
            SystemMessage(content=hallucination_prompt),
            HumanMessage(content=f"FACTS:\n{qa_pair.context}\n\n QUESTION:\n {qa_pair.question}\n\n STUDENT ANSWER:\n{qa_pair.answer}")
        ]
        response = await self.llm.ainvoke(messages)
        return {
            "score": 1 if "score: 1" in response.content.lower() else 0,
            "explanation": response.content,
            "type": "hallucination"
        }

    async def _run_test_for_helpfullness(self, qa_pair: QAPair):
        """Evaluate helpfulness using Gemini"""
        messages = [
            SystemMessage(content=helpfullness_prompt),
            HumanMessage(content=f"FACTS:\n{qa_pair.context}\n\n QUESTION:\n {qa_pair.question}\n\n STUDENT ANSWER:\n{qa_pair.answer}")

        ]
        response = await self.llm.ainvoke(messages)
        return {
            "score": 1 if "score: 1" in response.content.lower() else 0,
            "explanation": response.content,
            "type": "helpfulness"
        }

    async def _store_results(self, results):
        """Store test results in MongoDB"""
        await self.test_collection.insert_one({
            "project_id": self.project_id,
            "results": results,
            "timestamp": datetime.utcnow()
        })

    async def run(self):
        """Run all tests for project"""
        project_data = self._fetch_payload_info_by_project_id()
        qa_pairs = self._fetch_qa_by_project_id()
        
        results = []
        for qa in qa_pairs:
            hallucination = await self._run_test_for_hallucinations(qa)
            helpfulness = await self._run_test_for_helpfullness(qa)
            results.extend([hallucination, helpfulness])
        
        await self._store_results(results)
        return results





