from pydantic import BaseModel, Field
from typing import List
from langchain.output_parsers import PydanticOutputParser

class QuestionAnswer(BaseModel):
    question: str = Field(..., description="The generated question")
    answer: str = Field(..., description="The correct answer to the question")

class QAResponse(BaseModel):
    questions: List[QuestionAnswer]
    context: str

class QAPrompt(BaseModel):
    system_prompt: str = Field(
        default="You are an expert at generating high-quality question-answer pairs from given context. Generate concise and clear questions with accurate answers.",
    )
    
    format_instructions: str = Field(
        default="""The output should be formatted as a JSON object with the following structure:
{
    "questions": [
        {
            "question": "question text here",
            "answer": "answer text here"
        }
    ],
    "context": "input context here"
}""",
    )
    
    human_prompt_template: str = Field(
        default="""Given the following context, generate {num_questions} question-answer pairs:
        
Context: {context}

Requirements:
1. Test key concepts and information from the context
2. Have clear, unambiguous answers
3. Cover different aspects of the context
4. Are factual and can be verified from the context

{format_instructions}""",
    )
    
    num_questions: int = Field(default=3, ge=1, le=10)


from langchain_core.messages import SystemMessage, HumanMessage
from modules.benchmark.qa_pair import QAPair
from datetime import datetime
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.output_parsers import PydanticOutputParser
from motor.motor_asyncio import AsyncIOMotorClient
from core.config import Settings


class QAGenerator:
    def __init__(self, settings: Settings, db: AsyncIOMotorClient):
        self.db = db
        self.qa_collection = self.db.qa_collection
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash-exp",
            temperature=0,
            max_tokens=None,
            timeout=None,
            max_retries=0,
            api_key=settings.GEMINI_API_KEY,
        )
        self.prompt_config = QAPrompt()
        self.parser = PydanticOutputParser(pydantic_object=QAResponse)
    
    async def generate_qa(self, context: str, num_questions: int = 3) -> List[QAPair]:
        try:
            messages = [
                SystemMessage(content=self.prompt_config.system_prompt),
                HumanMessage(content=self.prompt_config.human_prompt_template.format(
                    context=context,
                    num_questions=num_questions,
                    format_instructions=self.parser.get_format_instructions()
                ))
            ]
            
            response = await self.llm.ainvoke(messages)
            parsed_response = self.parser.parse(response.content)
            
            qa_pairs = []
            for qa in parsed_response.questions:
                db_qa = QAPair(
                    question=qa.question,
                    answer=qa.answer,
                    context=context,
                    generated_at=datetime.utcnow()
                )
                qa_pairs.append(db_qa)  # Store in list instead of inserting into DB

            return qa_pairs
        except Exception as e:
            raise RuntimeError(f"QA generation failed: {str(e)}")