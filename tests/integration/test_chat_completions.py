from litestar.testing import TestClient
from syrupy.assertion import SnapshotAssertion
from litestar.response import Response
import httpx
from pydantic import BaseModel
from typing import Optional
import pytest
import os
import json
from pathlib import Path


# Path to the snapshot file for mocking OpenAI responses
SNAPSHOT_FILE = Path(__file__).parent / "__responses__" / "openai_chat_completion.json"


def test_chat_completion(
    client: TestClient,
    snapshot: SnapshotAssertion,
    snapshot_update: bool,
    mocker,
):
    """
    Test chat completion endpoint.
    """
    if snapshot_update and not os.environ.get("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY environment variable not set")

    async def mock_make_request(
        endpoint: str,
        data: Optional[BaseModel],
        stream: bool = False,
        timeout: float = 60.0,
        method: str = "POST",
    ):
        if snapshot_update:
            api_key = os.environ.get("OPENAI_API_KEY")
            async with httpx.AsyncClient() as http_client:
                real_response = await http_client.request(
                    method=method,
                    url=f"https://api.openai.com{endpoint}",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    json=data.model_dump() if data else None,
                    timeout=timeout,
                )
            assert real_response.status_code == 200, real_response.text
            # Save the successful response to our dedicated snapshot file
            with open(SNAPSHOT_FILE, "w") as f:
                json.dump(real_response.json(), f, indent=2)

            return Response(
                content=real_response.content,
                status_code=real_response.status_code,
                headers=dict(real_response.headers),
            )
        else:
            # Read the mock response from our dedicated snapshot file
            with open(SNAPSHOT_FILE, "r") as f:
                mock_data = json.load(f)
            return Response(
                status_code=200,
                content=json.dumps(mock_data),
                headers={"Content-Type": "application/json"},
            )

    mocker.patch(
        "app.services.openai.OpenAIService.make_request",
        side_effect=mock_make_request,
    )

    request_data = {
        "model": "gpt-4",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ],
    }

    response = client.post("/v1/chat/completions", json=request_data)

    assert response.status_code == 200
    assert response.json() == snapshot
