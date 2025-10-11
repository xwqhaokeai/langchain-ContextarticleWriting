import pytest
from fastapi.testclient import TestClient
from src.api.app import app

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_read_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the Context Article Writing API"}

def test_write_endpoint_success(client, mocker):
    # Mock the agent graph to avoid actual LLM calls
    mocker.patch(
        "src.api.routers.writing.agent_graph.astream_events",
        return_value=mock_agent_stream(),
    )

    request_body = {
        "topic": "Artificial Intelligence in Medicine",
        "style": "popular science article",
        "language": "English",
    }
    response = client.post("/api/v1/write", json=request_body)
    
    assert response.status_code == 200
    json_response = response.json()
    assert json_response["status"] == "completed"
    assert "article_id" in json_response
    assert "file_paths" in json_response

async def mock_agent_stream():
    yield {
        "event": "on_graph_end",
        "data": {
            "output": {
                "messages": [
                    {"content": "Final summary of the article."}
                ]
            }
        }
    }
    yield {
        "event": "on_tool_end",
        "name": "save_article",
        "data": {
            "output": "Article successfully saved to output/md/test.md"
        }
    }