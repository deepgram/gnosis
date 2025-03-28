import httpx
from typing import Dict, Any, Tuple
from src.config import Config

class OpenAIService:
    @staticmethod
    async def forward_chat_completion(body: Dict[str, Any]) -> Tuple[Dict[str, Any], int]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://api.openai.com/v1/chat/completions',
                json=body,
                headers={
                    'Authorization': f'Bearer {Config.OPENAI_API_KEY}',
                    'Content-Type': 'application/json'
                }
            )
            response_data = response.json()
            return response_data, response.status_code 