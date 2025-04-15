from modules.benchmark.qa_pair import QAPair
from modules.benchmark.utils import TestRunner
import asyncio
import json

test_runner = TestRunner("afac0874-b47f-4cbd-b56b-50b62764345a")

# Fetch project data
project_data = test_runner._fetch_payload_info_by_project_id()

# Call the get_student_answer method with no QA pair
print("Testing API endpoint with project configuration...")
result = asyncio.run(test_runner.get_student_answer())
print("\nResult from API call:")
print(result)

# You can also test with a dummy QA pair
dummy_qa = QAPair(
    question="What can you tell me about this project?",
    answer="",
    context="Testing context",
    verified=False
)

print("\nTesting with custom question...")
result_with_qa = asyncio.run(test_runner.get_student_answer(dummy_qa))
print("\nResult from API call with custom question:")
print(result_with_qa)