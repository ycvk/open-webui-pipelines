"""
title: Moderation Filter Pipeline
date: 2024-07-13
version: 1.0
license: MIT
description: A pipeline for moderating content using OpenAI's moderation API.
requirements: requests
"""

import os
from typing import List, Optional

import requests
from pydantic import BaseModel, Field
from utils.misc import get_last_user_message


class Pipeline:
    class Valves(BaseModel):
        # List target pipeline ids (models) that this filter will be connected to.
        # If you want to connect this filter to all pipelines, you can set pipelines to ["*"]
        pipelines: List[str] = ["*"]

        # Assign a priority level to the filter pipeline.
        priority: int = Field(
            default=0, description="Priority level for the filter operations."
        )

        # Valves for moderation
        moderation_api_base_url: str = Field(
            default="https://api.openai.com/v1",
            description="Base URL for the moderation API.",
        )
        openai_api_key: str = Field(
            default="", description="API key for OpenAI services."
        )
        moderation_model: str = Field(
            default="text-moderation-latest",
            description="Model to use for content moderation.",
        )
        enabled_for_admins: bool = Field(
            default=True, description="Whether moderation is enabled for admin users."
        )

    def __init__(self):
        # Pipeline filters are only compatible with Open WebUI
        self.type = "filter"

        # Set the name of the pipeline
        self.name = "Moderation Filter"

        # Initialize valves
        self.valves = self.Valves(
            **{
                "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            }
        )

    async def on_startup(self):
        # This function is called when the server is started.
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        # This function is called when the server is stopped.
        print(f"on_shutdown:{__name__}")
        pass

    async def on_valves_updated(self):
        # This function is called when the valves are updated.
        pass

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        print(f"inlet:{__name__}")

        if user is None or (not user.get("role") == "admin" or self.valves.enabled_for_admins):
            user_message = get_last_user_message(body["messages"])

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.valves.openai_api_key}",
            }
            payload = {
                "model": self.valves.moderation_model,
                "input": user_message,
            }

            try:
                r = requests.post(
                    url=f"{self.valves.moderation_api_base_url}/moderations",
                    json=payload,
                    headers=headers,
                )

                r.raise_for_status()

                response = r.json()
            except Exception as e:
                print(f"Error: {e}")
                return body

            if response["results"][0]["flagged"]:
                flagged = [
                    k for k, v in response["results"][0]["categories"].items() if v
                ]
                print(f"Flagged: {flagged}")
                raise Exception(
                    f"Message contains flagged content: {', '.join(flagged)}"
                )

        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        print(f"outlet:{__name__}")
        print(f"outlet:body:{body}")
        print(f"outlet:user:{user}")
        return body
