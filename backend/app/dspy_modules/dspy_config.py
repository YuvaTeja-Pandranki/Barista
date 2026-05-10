"""Configure DSPy LM: Gemini or OpenAI; no key = no LM (eval/offline)."""

from __future__ import annotations

import logging
import os

import dspy
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

_lm_configured: bool = False


def configure_dspy() -> bool:
    global _lm_configured

    gemini_key = os.getenv("GEMINI_API_KEY", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")

    if gemini_key:
        lm = dspy.LM(
            model="gemini/gemini-2.5-flash",
            api_key=gemini_key,
        )
        dspy.configure(lm=lm)
        _lm_configured = True
        logger.info("DSPy configured with Gemini 2.5 Flash")
    elif openai_key:
        lm = dspy.LM(
            model="openai/gpt-4o-mini",
            api_key=openai_key,
        )
        dspy.configure(lm=lm)
        _lm_configured = True
        logger.info("DSPy configured with OpenAI gpt-4o-mini (fallback)")
    else:
        _lm_configured = False
        logger.warning(
            "No GEMINI_API_KEY or OPENAI_API_KEY found — "
            "DSPy running in deterministic fallback mode"
        )

    return _lm_configured


def is_lm_available() -> bool:
    return _lm_configured


configure_dspy()
