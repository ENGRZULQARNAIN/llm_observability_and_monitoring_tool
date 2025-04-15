from modules.benchmark.qa_pair import QAPair
from modules.benchmark.utils import TestRunner, PayloadPlanner
import asyncio
import json
from modules.benchmark.utils import llm
test_runner = TestRunner("afac0874-b47f-4cbd-b56b-50b62764345a")

# Fetch project data
project_data = test_runner._fetch_payload_info_by_project_id()

# Convert project data to a payload configuration
payload_config = {
    "target_url": project_data.target_url,
    "end_point": project_data.end_point,
    "payload_method": project_data.payload_method,
    "body": project_data.payload_body
}

print("\n--- Testing PayloadPlanner ---")
# Create a PayloadPlanner instance
planner = PayloadPlanner(payload_config)

# Set the path to the question field
# For example, if your payload has structure: {"messages": [{"human": "question"}]}
# then the path would be ["messages", 0, "human"]
planner.set_question_field_path(["messages", 0, "human"])

# Send a test message
print("\n--- Testing with custom question ---")
question = "Tell me about artificial intelligence"
response = asyncio.run(planner.send_payload(question))
print(f"API Response: {response}")

# Try with endpoint variations if the first attempt failed
if response.get("error") or response.get("status_code") != 200:
    print("\n--- Trying different endpoint variations ---")
    response = asyncio.run(planner.try_payload_variations(question))
    print(f"API Response with variations: {response}")

# Print the successful payload if available
if planner.is_payload_passed:
    print("\n--- Successful payload ---")
    print(planner.passed_payload)

# # Call the get_student_answer method with no QA pair
# print("Testing API endpoint with project configuration...")
# result = asyncio.run(test_runner.get_student_answer())
# print("\nResult from API call:")
# print(result)

# # You can also test with a dummy QA pair
# dummy_qa = QAPair(
#     question="What can you tell me about this project?",
#     answer="",
#     context="Testing context",
#     verified=False
# )

# print("\nTesting with custom question...")
# result_with_qa = asyncio.run(test_runner.get_student_answer(dummy_qa))
# print("\nResult from API call with custom question:")
# print(result_with_qa)


