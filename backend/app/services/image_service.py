"""Generate drink image via Gemini; returns data URI or None."""

from __future__ import annotations

import base64
import logging

logger = logging.getLogger(__name__)


def generate_drink_image(image_prompt: str) -> str | None:
    try:
        from app.llm.gemini_client import get_gemini_client

        client, _ = get_gemini_client()

        response = client.models.generate_images(
            model="imagen-3.0-generate-002",
            prompt=image_prompt,
            config={"number_of_images": 1},
        )

        if response.generated_images:
            img = response.generated_images[0]
            b64 = base64.b64encode(img.image.image_bytes).decode("ascii")
            return f"data:image/png;base64,{b64}"

        logger.warning("Gemini returned no images for prompt: %s", image_prompt)
        return None

    except Exception:
        logger.warning("Image generation failed", exc_info=True)
        return None
