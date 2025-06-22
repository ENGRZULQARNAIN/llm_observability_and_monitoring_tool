import json
import uuid
from core.database import SessionLocal, get_mongodb
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser
from langchain_anthropic import ChatAnthropic
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import Settings, get_settings
from langchain_core.messages import SystemMessage, HumanMessage
from modules.benchmark.qa_pair import QAPair
import requests
from modules.monitor.models import TestInfo
from modules.project_connections.models import Projects
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.logger import logger
import copy
import re
from typing import Dict, Any, List, Union, Optional

settings = get_settings()

# llm = ChatGoogleGenerativeAI(
#             model="gemini-2.0-flash-exp",
#             temperature=0.2,
#             max_tokens=None,
#             timeout=None,
#             max_retries=0,
#             api_key=settings.GEMINI_API_KEY,
#         )

llm = ChatAnthropic(
            model="claude-3-5-sonnet-latest",
            temperature=0.1,
            api_key=settings.ANTHROPIC_API_KEY,
        )

from core.config import get_settings
settings = get_settings()
from langsmith import Client
client = Client(api_key=settings.LANGSMITH_API_KEY)
prompt_payload_planner = client.pull_prompt("zulqarnain/payload_planner")
prompt_helpfullness = client.pull_prompt("helpfullness_prompt_obseravbility")
prompt_hallucinations = client.pull_prompt("hallucinations_testing")

# print(prompt)


payload_planner_chain = prompt_payload_planner | llm
helpfullness_chain = prompt_helpfullness | llm
hallucinations_chain = prompt_hallucinations | llm



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
            self.test_collection = self.mongo_db.test_collection
            
            
            # Fetch QA pairs
            qa_doc = await self.test_collection.find_one({"project_id": self.project_id})
            if not qa_doc:
                logger.warning(f"No QA pairs found for project {self.project_id}")
                return []
            qa_pairs = qa_doc.get("qa_pairs", [])
            qa_pairs = [QAPair(**qa) for qa in qa_pairs]
            user_id = qa_doc.get("user_id")
            # Run tests
            results = []
            for qa in qa_pairs:
                print(f"Running for QA: {qa.question}")
                student_answer = await self.get_student_answer(qa)
                print(f"Student answer: {student_answer}")
                if student_answer:
                    hallucination = await self._run_test_for_hallucinations(qa,student_answer)
                    helpfulness = await self._run_test_for_helpfullness(qa,student_answer)
                    results.append({"question":qa.question,"student_answer":student_answer,"hallucination":hallucination,"helpfulness":helpfulness,"difficulty_level":qa.difficulty_level})
            self.add_results(results, user_id)
            print(f"Results added for project {self.project_id}")
            logger.info(f"Results added for project {self.project_id}")

        except Exception as e:
            logger.error(f"Error in TestRunner.run: {str(e)}")
            raise
        finally:
            if self.db:
                self.db.close()
    
        
    async def get_student_answer(self, qa_pair=None):
        """Get student answer from MongoDB"""
        get_payload_info = self._fetch_payload_info_by_project_id()
        
        # Check if get_payload_info exists
        if get_payload_info is None:
            logger.error(f"No payload information found for project {self.project_id}")
            return None
            
        # Convert project data to a payload configuration
        student_answer = None
        
        # Default to POST if payload_method is None
        payload_method = get_payload_info.payload_method
        if payload_method is None:
            payload_method = "post"
            logger.warning(f"No payload_method specified for project {self.project_id}, defaulting to POST")
            
        payload_config = {
            "target_url": get_payload_info.target_url,
            "end_point": get_payload_info.end_point,
            "payload_method": payload_method,
            "body": get_payload_info.payload_body,
            "headers": {"Content-Type": "application/json"}
        }
        
        # Check for other required fields
        if not get_payload_info.target_url or not get_payload_info.end_point:
            logger.error(f"Missing target_url or end_point for project {self.project_id}")
            return None
            
        try:
            print("Payload config being sent:", payload_config)
            prepare_payload = await self.prepare_payload(str(payload_config.get("body")), user_query=qa_pair.question)
            payload_config["body"] = prepare_payload
            test_response = await trigger_payload(payload_config)
            
            if test_response[0]:
                student_answer = test_response[1]
            else:
                logger.error(f"Error in trigger_payload: {test_response}")
                print("Error response from model:", test_response[1])
                student_answer = None
                
        except Exception as e:
            logger.error(f"Error in get_student_answer: {str(e)}")
            student_answer = None

        return student_answer
    
    async def prepare_payload(self, payload_infor, user_query=None):
        # Check if payload_infor is None
        if payload_infor is None:
            logger.warning("payload_infor is None, using empty dict")
            return {}
            
        ans = payload_planner_chain.invoke({"question": f"user query: {user_query}, payload: "
                f"{payload_infor}"
        })
        
        # Check if ans is properly returned
        if not ans or not isinstance(ans, list) or not ans[0] or not isinstance(ans[0], dict):
            logger.warning("Invalid response from payload_planner_chain")
            return {}
            
        final_payload = ans[0].get("args", {}).get("final_payload")
        
        # Check if final_payload exists
        if final_payload is None:
            logger.warning("final_payload is None, using empty dict")
            return {}
            
        # Convert Python-style string dict to proper JSON
        if final_payload and isinstance(final_payload, str):
            # Use ast.literal_eval to safely evaluate the string as a Python literal
            import ast
            try:
                # Convert Python dict string to actual dict
                python_dict = ast.literal_eval(final_payload)
                # Convert the dict to proper JSON
                final_payload = json.dumps(python_dict)
                # Now parse it back to get the Python object
                final_payload = json.loads(final_payload)
            except (SyntaxError, ValueError) as e:
                # Fallback if the string cannot be parsed
                logger.warning(f"Error processing payload: {e}")
                return final_payload
        return final_payload

    async def _run_test_for_hallucinations(self, qa_pair=None,student_answer=None):
        hallucination = hallucinations_chain.invoke({"question":qa_pair.question,"facts":qa_pair.answer,"answer":student_answer,})
        return hallucination[0].get("args").get("hallucination")

    async def _run_test_for_helpfullness(self, qa_pair=None,student_answer=None):
        helpfulness = helpfullness_chain.invoke({"question": qa_pair.question,"student_answer": student_answer})
        return helpfulness[0].get("args").get("Helpful")
    
    def add_results(self, results, user_id):
        db = SessionLocal()
        try:
            test_info_objects = [
                TestInfo(
                    test_id=str(uuid.uuid4()),
                    project_id=self.project_id,
                    user_id=user_id,
                    question=result["question"],
                    student_answer=result["student_answer"],
                    hallucination_score=result["hallucination"],
                    helpfullness_score=result["helpfulness"],
                    last_test_conducted=datetime.utcnow(),
                    test_status=str(1 if result["hallucination"] < 0.5 and result["helpfulness"] > 0.5 else 0)
                    difficulty_level = result["difficulty_level"]
                )
                for result in results
            ]
            db.add_all(test_info_objects)
            db.commit()
            print("Committed test_info_objects:", test_info_objects)
        except Exception as e:
            db.rollback()
            logger.error(f"Error adding test results: {str(e)}")
            raise
        finally:
            db.close()

async def trigger_payload(payload_config):
    """Test payload
    
    Args:
        payload_config (dict): Dictionary containing payload configuration
            with keys: target_url, end_point, payload_method, body, headers
            
    Returns:
        bool: True if request is successful (status 200), False otherwise
    """
    try:
        import requests
        
        # Check if required fields exist
        if not all(key in payload_config for key in ['target_url', 'end_point', 'payload_method']):
            logger.error("Missing required fields in payload_config")
            return False, None
        
        # Check if payload_method is None
        if payload_config['payload_method'] is None:
            logger.error("payload_method cannot be None")
            return False, None
            
        url = f"{payload_config['target_url']}{payload_config['end_point']}"
        method = payload_config['payload_method'].lower()
        headers = payload_config.get('headers', {})
        body = payload_config.get('body', {})
        
        if isinstance(headers, str):
            try:
                headers = json.loads(headers)
            except json.JSONDecodeError:
                headers = {}
                
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                pass
        
        response = None
        if method == 'get':
            response = requests.get(url, headers=headers, params=body)
        elif method == 'post':
            response = requests.post(url, headers=headers, json=body)
        elif method == 'put':
            response = requests.put(url, headers=headers, json=body)
        elif method == 'delete':
            response = requests.delete(url, headers=headers, json=body)
        elif method == 'patch':
            response = requests.patch(url, headers=headers, json=body)
            
        if response and response.status_code == 200:
            print(f"the response is {response.content}")
            return True,response.content
        return False,None
    except Exception as e:
        logger.error(f"Error in trigger_payload: {str(e)}")
        return False,None



# {'messages': [{'human': 'hey_val_ai'}]}