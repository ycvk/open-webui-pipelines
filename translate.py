import os
from typing import List, Optional

import requests
from pydantic import BaseModel
from utils.pipelines.main import get_last_user_message, get_last_assistant_message


class Pipeline:
    class Valves(BaseModel):
        pipelines: List[str] = []
        priority: int = 0
        deepl_url: str

        source_user: Optional[str] = "auto"
        target_user: Optional[str] = "EN"

        source_assistant: Optional[str] = "EN"
        target_assistant: Optional[str] = "ZH"

    def __init__(self):
        self.type = "filter"
        self.name = "DeepL Translation Filter"

        self.valves = self.Valves(
            **{
                "pipelines": ["*"],
                "deepl_url": os.getenv(
                    "DEEPL_API_BASE_URL", "http://example.com"
                ),
            }
        )

    async def on_startup(self):
        print(f"on_startup:{__name__}")

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")

    async def on_valves_updated(self):
        pass

    def translate(self, text: str, source: str, target: str) -> str:
        payload = {
            "text": text,
            "source_lang": source,
            "target_lang": target,
        }

        try:
            r = requests.post(
                f"{self.valves.deepl_url}/translate", json=payload
            )
            r.raise_for_status()

            data = r.json()
            return data["data"]
        except Exception as e:
            print(f"Error translating text: {e}")
            return text

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        print(f"inlet:{__name__}")

        messages = body["messages"]
        user_message = get_last_user_message(messages)

        print(f"User message: {user_message}")

        translated_user_message = self.translate(
            user_message,
            self.valves.source_user,
            self.valves.target_user,
        )

        print(f"Translated user message: {translated_user_message}")

        for message in reversed(messages):
            if message["role"] == "user":
                message["content"] = translated_user_message
                break

        body = {**body, "messages": messages}
        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        print(f"outlet:{__name__}")

        messages = body["messages"]
        assistant_message = get_last_assistant_message(messages)

        print(f"Assistant message: {assistant_message}")

        translated_assistant_message = self.translate(
            assistant_message,
            self.valves.source_assistant,
            self.valves.target_assistant,
        )

        print(f"Translated assistant message: {translated_assistant_message}")

        for message in reversed(messages):
            if message["role"] == "assistant":
                message["content"] = translated_assistant_message
                break

        body = {**body, "messages": messages}
        return body
