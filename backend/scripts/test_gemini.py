"""Quick smoke test for the standalone Gemini client.

Run from the backend directory:
    python -m scripts.test_gemini
"""

from app.llm.gemini_client import get_gemini_client


def main() -> None:
    client, model_name = get_gemini_client(model_name="gemini-2.5-flash")

    print(f"Using model: {model_name}")

    response = client.models.generate_content(
        model=model_name,
        contents="Suggest a comforting coffee drink for a rainy afternoon.",
    )

    print("\n=== GEMINI RESPONSE ===")
    print(response.text)
    print("=======================")


if __name__ == "__main__":
    main()
