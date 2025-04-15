import json
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
    def __init__(self, project_id):
        """Regular constructor - no async operations here"""
        self.project_id = project_id
        self.db = SessionLocal()
        # Initialize these to None - they'll be set up in run()
        self.mongo_db = None
        self.qa_collection = None
        self.test_collection = None
    
    def _fetch_payload_info_by_project_id(self):
        """Fetch project info from SQL database"""
        return self.db.query(Projects).filter(Projects.project_id==self.project_id).first()

    async def run(self):
        """Run all tests for project"""
        try:
            # Set up MongoDB connection first
            from core.config import get_settings
            settings = get_settings()
            
            # Connect to MongoDB directly here
            from motor.motor_asyncio import AsyncIOMotorClient
            client = AsyncIOMotorClient(settings.MONGODB_URL)
            self.mongo_db = client[settings.MONGODB_DB]
            self.qa_collection = self.mongo_db.qa_collection
            self.test_collection = self.mongo_db.test_results
            
            
            # Fetch QA pairs
            qa_doc = await self.qa_collection.find_one({"project_id": self.project_id})
            if not qa_doc:
                logger.warning(f"No QA pairs found for project {self.project_id}")
                return []
                
            qa_pairs = [QAPair(**qa) for qa in qa_doc.get("qa_pairs", [])]
            
            # Run tests
            results = []
            for qa in qa_pairs:
                hallucination = await self._run_test_for_hallucinations(qa)
                helpfulness = await self._run_test_for_helpfullness(qa)
                results.extend([hallucination, helpfulness])
            
            # Store results
            await self.test_collection.insert_one({
                "project_id": self.project_id,
                "results": results,
                "timestamp": datetime.utcnow()
            })
            
            # Update test info in SQL database
            from modules.monitor.models import TestInfo
            test_info = self.db.execute(select(TestInfo).filter(TestInfo.project_id == self.project_id)).first()
            if test_info:
                test_info = test_info[0]  # Extract from result proxy
                test_info.last_test_conducted = datetime.utcnow()
            else:
                # Create new test info
                test_info = TestInfo(
                    project_id=self.project_id,
                    last_test_conducted=datetime.utcnow()
                )
                self.db.add(test_info)
            
            self.db.commit()
            return results
            
        except Exception as e:
            logger.error(f"Error in TestRunner.run: {str(e)}")
            raise
        finally:
            if self.db:
                self.db.close()
    
    async def _run_test_for_hallucinations(self, qa_pair: QAPair):
        """Evaluate hallucination using Gemini"""
        messages = [
            SystemMessage(content=hallucination_prompt),
            HumanMessage(content=f"FACTS:\n{qa_pair.context}\n\n QUESTION:\n {qa_pair.question}\n\n STUDENT ANSWER:\n{qa_pair.answer}")
        ]
        response = await llm.ainvoke(messages)
        return {
            "score": 1 if "score: 1" in response.content.lower() else 0,
            "explanation": response.content,
            "type": "hallucination"
        }

    async def _run_test_for_helpfullness(self, qa_pair: QAPair):
        """Evaluate helpfulness using Gemini"""
        messages = [
            SystemMessage(content=helpfullness_prompt),
            HumanMessage(content=f"FACTS:\n{qa_pair.context}\n\n QUESTION:\n {qa_pair.question}\n\n STUDENT ANSWER:\n{await self.get_student_answer(qa_pair)}")
        ]
        response = await llm.ainvoke(messages)
        return {
            "score": 1 if "score: 1" in response.content.lower() else 0,
            "explanation": response.content,
            "type": "helpfulness"
        }
    async def get_student_answer(self, qa_pair=None):
        """Get student answer from MongoDB"""
        get_payload_info = self._fetch_payload_info_by_project_id()
        
        if not get_payload_info:
            logger.error(f"No project found with ID: {self.project_id}")
            return "Error: Project not found"
            
        target_url = get_payload_info.target_url
        end_point = get_payload_info.end_point
        payload_method = get_payload_info.payload_method
        
        # Process the payload body - handle different formats
        try:
            if isinstance(get_payload_info.payload_body, str):
                # Try to load as JSON, handling different quote styles
                try:
                    payload_body = json.loads(get_payload_info.payload_body)
                except json.JSONDecodeError:
                    # Try with replaced quotes if standard JSON parsing fails
                    payload_body = json.loads(get_payload_info.payload_body.replace("'", '"'))
            else:
                payload_body = get_payload_info.payload_body
                
            # # If we have a QA pair, we can insert the question into the payload body
            # if qa_pair:
            #     # Here you can modify the payload to include the question from qa_pair
            #     # This assumes your payload has a structure like {"messages": [{"human": "question"}]}
            #     if isinstance(payload_body, dict) and "messages" in payload_body:
            #         for msg in payload_body["messages"]:
            #             if "human" in msg:
            #                 msg["human"] = qa_pair.question
                
            # Prepare headers if available
            headers = {}
            if hasattr(get_payload_info, 'header_keys') and hasattr(get_payload_info, 'header_values'):
                if get_payload_info.header_keys and get_payload_info.header_values:
                    # Parse header keys and values if they're stored as strings
                    try:
                        header_keys = json.loads(get_payload_info.header_keys) if isinstance(get_payload_info.header_keys, str) else get_payload_info.header_keys
                        header_values = json.loads(get_payload_info.header_values) if isinstance(get_payload_info.header_values, str) else get_payload_info.header_values
                        
                        if isinstance(header_keys, list) and isinstance(header_values, list) and len(header_keys) == len(header_values):
                            for i in range(len(header_keys)):
                                headers[header_keys[i]] = header_values[i]
                    except Exception as e:
                        logger.warning(f"Error processing headers: {str(e)}")
            
            # Add default content-type if not present
            if 'Content-Type' not in headers:
                headers['Content-Type'] = 'application/json'
                
            full_url = target_url + end_point
            print(f"Making {payload_method} request to: {full_url}")
            print(f"Headers: {headers}")
            print(f"Payload: {payload_body}")
            
            if payload_method == "POST":
                response = requests.post(full_url, json=payload_body, headers=headers)
            elif payload_method == "GET":
                response = requests.get(full_url, headers=headers)
            else:
                raise ValueError(f"Invalid payload method: {payload_method}")
            
            print(f"Response status code: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                print(f"Response data: {response_data}")
                return str(response_data)
            else:
                print(f"Error response: {response.text}")
                return f"Error: {response.status_code} - {response.text}"
                
        except Exception as e:
            error_msg = f"Error making request: {str(e)}"
            logger.error(error_msg)
            print(error_msg)
            return error_msg
        



