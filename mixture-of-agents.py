"""
title: MoA (Mixture of Agents) Filter Pipeline
date: 2024-07-13
version: 1.0
license: MIT
description: A pipeline for implementing the Mixture of Agents (MoA) architecture using Ollama models.
requirements: pydantic, requests
"""

import json
import random
from typing import List, Optional

import requests
from pydantic import BaseModel, Field


class Pipeline:
    class Valves(BaseModel):
        # List target pipeline ids (models) that this filter will be connected to.
        # If you want to connect this filter to all pipelines, you can set pipelines to ["*"]
        pipelines: List[str] = ["*"]

        # Assign a priority level to the filter pipeline.
        priority: int = 0

        # MoA specific valves
        available_models: List[str] = Field(
            default=[],
            description="List of available models to use in the MoA architecture."
        )
        aggregator_model: str = Field(
            default="",
            description="Model to use for aggregation tasks."
        )
        openai_api_base: str = Field(
            default="http://host.docker.internal:11434/v1",
            description="Base URL for Ollama API."
        )
        api_key: str = Field(
            default="",
            description="API key for authorization."
        )
        num_layers: int = Field(
            default=3,
            description="Number of MoA layers."
        )
        num_agents_per_layer: int = Field(
            default=3,
            description="Number of agents to use in each layer."
        )

    def __init__(self):
        self.type = "filter"
        self.name = "MoA Filter Pipeline"

        self.valves = self.Valves()

    async def on_startup(self):
        print(f"on_startup:{__name__}")
        pass

    async def on_shutdown(self):
        print(f"on_shutdown:{__name__}")
        pass

    async def on_valves_updated(self):
        pass

    async def inlet(self, body: dict, user: Optional[dict] = None) -> dict:
        print(f"inlet:{__name__}")
        print(f"inlet:body:{body}")
        print(f"inlet:user:{user}")

        messages = body.get("messages", [])
        if messages:
            last_message = messages[-1]["content"]
            moa_response = self.moa_process(last_message)
            body["messages"][-1]["content"] = moa_response

        return body

    async def outlet(self, body: dict, user: Optional[dict] = None) -> dict:
        print(f"outlet:{__name__}")
        print(f"outlet:body:{body}")
        print(f"outlet:user:{user}")
        return body

    def moa_process(self, prompt: str) -> str:
        if not self.valves.available_models or not self.valves.aggregator_model or not self.valves.openai_api_base:
            return "Error: Available models, aggregator model, or API base URL not set."

        layer_outputs = []

        for layer in range(self.valves.num_layers):
            current_layer_outputs = []
            layer_agents = random.sample(
                self.valves.available_models,
                min(self.valves.num_agents_per_layer, len(self.valves.available_models))
            )

            for agent in layer_agents:
                if layer == 0:
                    response = self.query_ollama(agent, prompt)
                else:
                    aggregator_prompt = self.create_aggregator_prompt(
                        prompt, layer_outputs[-1]
                    )
                    response = self.query_ollama(
                        self.valves.aggregator_model, aggregator_prompt
                    )

                current_layer_outputs.append(response)

            layer_outputs.append(current_layer_outputs)

        final_prompt = self.create_final_aggregator_prompt(prompt, layer_outputs)
        final_response = self.query_ollama(self.valves.aggregator_model, final_prompt)

        return final_response

    def create_aggregator_prompt(
            self, original_prompt: str, previous_responses: List[str]
    ) -> str:
        aggregator_prompt = (
            f"Original prompt: {original_prompt}\n\nPrevious responses:\n"
        )
        for i, response in enumerate(previous_responses, 1):
            aggregator_prompt += f"{i}. {response}\n\n"
        aggregator_prompt += "Based on the above responses and the original prompt, provide an improved and comprehensive answer:"
        return aggregator_prompt

    def create_final_aggregator_prompt(
            self, original_prompt: str, all_layer_outputs: List[List[str]]
    ) -> str:
        final_prompt = (
            f"Original prompt: {original_prompt}\n\nResponses from all layers:\n"
        )
        for layer, responses in enumerate(all_layer_outputs, 1):
            final_prompt += f"Layer {layer}:\n"
            for i, response in enumerate(responses, 1):
                final_prompt += f"  {i}. {response}\n\n"
        final_prompt += f"Considering all the responses from different layers and the original prompt '{original_prompt}', provide a final, comprehensive answer that strictly adheres to the original request:"
        return final_prompt

    def query_ollama(self, model: str, prompt: str) -> str:
        url = f"{self.valves.openai_api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.valves.api_key}"
        }
        data = {"model": model, "stream": False, "messages": [{"role": "user", "content": prompt}]}

        try:
            response = requests.post(url, headers=headers, data=json.dumps(data))
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.RequestException as e:
            print(f"Error querying Ollama API for model {model}: {e}")
            return f"Error: Unable to query model {model}"
