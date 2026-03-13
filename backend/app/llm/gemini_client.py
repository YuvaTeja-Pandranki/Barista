"""Gemini client; key from GEMINI_API_KEY."""

from __future__ import annotations

import os

from dotenv import load_dotenv
from google import genai

load_dotenv()


def get_gemini_client(
    model_name: str = "gemini-2.5-flash",
) -> tuple[genai.Client, str]:
    api_key = os.getenv("GEMINI_API_KEY", "")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY is not set. "
            "Add it to .env or export it as an environment variable."
        )

    client = genai.Client(api_key=api_key)
    return client, model_name
