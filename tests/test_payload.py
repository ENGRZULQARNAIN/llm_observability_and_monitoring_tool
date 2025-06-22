import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock
from langchain_anthropic import ChatAnthropic
# Add the root directory to the Python path to import modules properly
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, parent_dir)

# Import after path setup
# from modules.benchmark.utils import test_payload  # noqa: E402


def valid_payload_config(final_payload):
    """Fixture for a valid payload configuration."""
    return {
        "target_url": "https://ml-staging.qc360.us",
        "end_point": "/chat_completion/",
        "payload_method": "POST",
        "body": final_payload,
        "headers": {"Content-Type": "application/json"}
    }


@pytest.fixture
def invalid_payload_config():
    """Fixture for an invalid payload configuration."""
    return {
        "target_url": "https://invalid-api-url.example.com",
        "end_point": "/test-endpoint",
        "payload_method": "POST",
        "body": {"key": "value"},
        "headers": {"Content-Type": "application/json"}
    }


@pytest.mark.asyncio
async def test_successful_payload(valid_payload_config):
    """Test a successful API call with status code 200."""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = await test_payload(valid_payload_config)
        
        # Assert the result is True (request successful)
        assert result is True
        
        # Verify the request was made with correct parameters
        endpoint = (f"{valid_payload_config['target_url']}"
                    f"{valid_payload_config['end_point']}")
        mock_post.assert_called_once_with(
            endpoint,
            headers=valid_payload_config['headers'],
            json=valid_payload_config['body']
        )


@pytest.mark.asyncio
async def test_failed_payload_non_200(valid_payload_config):
    """Test a failed API call with non-200 status code."""
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 404  # Not found
        mock_post.return_value = mock_response
        
        result = await test_payload(valid_payload_config)
        
        # Assert the result is False (request failed)
        assert result is False


@pytest.mark.asyncio
async def test_failed_payload_exception(invalid_payload_config):
    """Test handling of exceptions during API call."""
    with patch('requests.post') as mock_post:
        mock_post.side_effect = Exception("Connection error")
        
        result = await test_payload(invalid_payload_config)
        
        # Assert the result is False (request failed due to exception)
        assert result is False


@pytest.mark.asyncio
async def test_different_http_methods(valid_payload_config):
    """Test different HTTP methods."""
    methods = ['get', 'post', 'put', 'delete', 'patch']
    
    for method in methods:
        config = valid_payload_config.copy()
        config['payload_method'] = method.upper()
        
        with patch(f'requests.{method}') as mock_method:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_method.return_value = mock_response
            
            result = await test_payload(config)
            
            # Assert the result is True (request successful)
            assert result is True
            
            # Verify the correct method was called
            endpoint = f"{config['target_url']}{config['end_point']}"
            if method == 'get':
                mock_method.assert_called_once_with(
                    endpoint,
                    headers=config['headers'],
                    params=config['body']
                )
            else:
                mock_method.assert_called_once_with(
                    endpoint,
                    headers=config['headers'],
                    json=config['body']
                )


@pytest.mark.asyncio
async def test_json_string_handling(valid_payload_config):
    """Test handling of JSON strings in headers and body."""
    config = valid_payload_config.copy()
    config['headers'] = json.dumps(config['headers'])
    config['body'] = json.dumps(config['body'])
    
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response
        
        result = await test_payload(config)
        
        # Assert the result is True (request successful)
        assert result is True
        
        # Verify the JSON strings were properly parsed
        endpoint = f"{config['target_url']}{config['end_point']}"
        mock_post.assert_called_once_with(
            endpoint,
            headers=json.loads(config['headers']),
            json=json.loads(config['body'])
        )
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import get_settings
settings = get_settings()
from langsmith import Client
client = Client(api_key=settings.LANGSMITH_API_KEY)
prompt_payload_planner = client.pull_prompt("zulqarnain/payload_planner")
prompt_helpfullness = client.pull_prompt("helpfullness_prompt_obseravbility")
prompt_hallucinations = client.pull_prompt("hallucinations_testing")

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

payload_planner = prompt_payload_planner | llm

helpfullness_chain = prompt_helpfullness | llm
hallucinations_chain = prompt_hallucinations | llm
# ans = payload_planner.invoke({
#     "question": "user query: hi this is zulqarnain, payload: "
#                 "{'messages': [{'human': 'hey_val_ai'}]}"
# })

# final_payload = ans[0].get("args").get("final_payload")

# # Convert Python-style string dict to proper JSON
# if final_payload and isinstance(final_payload, str):
#     # Use ast.literal_eval to safely evaluate the string as a Python literal
#     import ast
#     try:
#         # Convert Python dict string to actual dict
#         python_dict = ast.literal_eval(final_payload)
#         # Convert the dict to proper JSON
#         final_payload = json.dumps(python_dict)
#         # Now parse it back to get the Python object
#         final_payload = json.loads(final_payload)
#     except (SyntaxError, ValueError) as e:
#         # Fallback if the string cannot be parsed
#         print(f"Error processing payload: {e}")
#         # final_payload = {"messages": [{"human": "hi this is zulqarnain"}]}

# import asyncio
# result = asyncio.run(test_payload(valid_payload_config(final_payload)))
# print(result)



ans = helpfullness_chain.invoke({"question": "what is the capital of pakistan","student_answer": "Islamabad"})
ans_hallucination = hallucinations_chain.invoke({"question": "what is the capital of pakistan","facts":"Islamabad","answer": "Islamabad",})
print(type(ans[0].get("args").get("Helpful")))
print(ans_hallucination[0].get("args").get("hallucination"))
