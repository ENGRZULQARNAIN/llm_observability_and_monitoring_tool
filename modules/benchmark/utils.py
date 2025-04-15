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
import copy
import re
from typing import Dict, Any, List, Union, Optional

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
from core.config import get_settings
settings = get_settings()
from langsmith import Client
client = Client(api_key=settings.LANGSMITH_API_KEY)
prompt = client.pull_prompt("zulqarnain/payload_planner")
# print(prompt)


chain = prompt | llm

# answer = chain.invoke(input="""{
#     "messages": [
#         {
#             "human": "hey_val_ai"
#         }
#     ]
# }""")

# print(answer[-1].get("args"))


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
        

class PayloadPlanner:
    """
    Class for preparing and sending API payloads with customizable structure
    """
    def __init__(self, raw_payload: Dict):
        """
        Initialize the PayloadPlanner
        
        Args:
            raw_payload: Dictionary containing payload configuration
        """
        self.raw_payload = raw_payload
        self.is_payload_passed = False
        self.passed_payload = None
        self.question_field_path = None  # Path to the question field
    
    def set_question_field_path(self, path: List[Union[str, int]]):
        """
        Explicitly set the path to the question field in the payload
        
        Args:
            path: List representing path to question field (e.g. ["messages", 0, "content"])
        """
        self.question_field_path = path
        return self
    
    async def prepare_payload(self, question: Optional[str] = None) -> tuple:
        """
        Prepare the payload for sending, with optional question insertion
        
        Args:
            question: The question or prompt to insert in the payload
            
        Returns:
            tuple: (field_name, prepared_payload)
        """
        try:
            # Parse the payload body from raw_payload
            body = self.raw_payload.get("body", {})
            if isinstance(body, str):
                try:
                    payload = json.loads(body)
                except json.JSONDecodeError:
                    # Try with replaced quotes if standard JSON parsing fails
                    payload = json.loads(body.replace("'", '"'))
            else:
                payload = body
            
            # Make a copy of the payload to avoid modifying the original
            payload_copy = copy.deepcopy(payload)
            
            # If we have a question to insert and a path for it
            field_name = None
            if question and self.question_field_path:
                # Navigate to the correct position in the payload
                current = payload_copy
                for i, key in enumerate(self.question_field_path):
                    if i == len(self.question_field_path) - 1:
                        # We've reached the final position, insert the question
                        current[key] = question
                        field_name = key
                    else:
                        # Keep traversing
                        if key not in current:
                            # Create nested dictionary if needed
                            if isinstance(self.question_field_path[i+1], int):
                                current[key] = []  # Next key is an index, so create a list
                            else:
                                current[key] = {}  # Next key is a string, so create a dict
                        current = current[key]
            
            # Store the prepared payload
            self.prepared_payload = payload_copy
            return field_name, payload_copy
        
        except Exception as e:
            logger.error(f"Error preparing payload: {str(e)}")
            return None, None
    
    async def send_payload(self, question: Optional[str] = None) -> Dict[str, Any]:
        """
        Prepare and send the payload to the target endpoint
        
        Args:
            question: Optional question to insert in the payload
            
        Returns:
            Dict: Response data or error information
        """
        try:
            # Prepare the payload
            field_name, payload = await self.prepare_payload(question)
            if not payload:
                return {"error": "Failed to prepare payload"}
            
            # Extract target information from raw_payload
            target_url = self.raw_payload.get("target_url", "")
            endpoint = self.raw_payload.get("end_point", "")
            method = self.raw_payload.get("payload_method", "POST")
            
            # Prepare headers
            headers = {'Content-Type': 'application/json'}
            if self.raw_payload.get("headers"):
                headers.update(self.raw_payload.get("headers"))
            
            # Log request details
            url = target_url + endpoint
            logger.info(f"Sending {method} request to: {url}")
            logger.info(f"Headers: {headers}")
            logger.info(f"Payload: {payload}")
            
            # Send the request
            if method.upper() == "POST":
                response = requests.post(url, json=payload, headers=headers)
            elif method.upper() == "GET":
                response = requests.get(url, headers=headers)
            else:
                return {"error": f"Unsupported method: {method}"}
            
            # Process the response
            status_code = response.status_code
            if status_code == 200:
                # Success
                try:
                    response_data = response.json()
                    self.is_payload_passed = True
                    self.passed_payload = payload
                    return response_data
                except Exception as e:
                    # Response was not JSON
                    return {"status_code": status_code, "content": response.text}
            else:
                # Error
                return {
                    "status_code": status_code,
                    "error": f"Request failed with status {status_code}",
                    "details": response.text
                }
                
        except Exception as e:
            logger.error(f"Error sending payload: {str(e)}")
            return {"error": str(e)}
    
    async def try_payload_variations(self, question: Optional[str] = None) -> Dict[str, Any]:
        """
        Try different variations of the payload and endpoint format
        
        Args:
            question: Optional question to insert in the payload
            
        Returns:
            Dict: Response from the successful attempt or error information
        """
        # Try with and without trailing slash in endpoint
        original_endpoint = self.raw_payload.get("end_point", "")
        
        # First attempt - original endpoint
        logger.info(f"Trying original endpoint: {original_endpoint}")
        result = await self.send_payload(question)
        if result.get("status_code") == 200 or not result.get("error"):
            return result
        
        # Second attempt - toggle trailing slash
        if original_endpoint.endswith('/'):
            self.raw_payload["end_point"] = original_endpoint[:-1]
        else:
            self.raw_payload["end_point"] = original_endpoint + "/"
            
        logger.info(f"Trying alternative endpoint: {self.raw_payload['end_point']}")
        result = await self.send_payload(question)
        
        # Restore original endpoint
        self.raw_payload["end_point"] = original_endpoint
        return result

    async def get_payload_plan():
        pass
    async def get_payload_plan_by_project_id():
        pass
    async def get_payload_plan_by_project_id():
        pass
