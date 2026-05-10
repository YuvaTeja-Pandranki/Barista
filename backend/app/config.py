"""App config from env."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Visual Barista AI"
    app_version: str = "0.1.0"
    debug: bool = True
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"
    gcp_project_id: str = ""
    gcp_location: str = "us-central1"
    weather_api_key: str = ""

    menu_data_path: str = "data/starbucks_menu.json"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
