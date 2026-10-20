import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    foundry_project_endpoint: str
    memory_store_chat_model: str
    memory_store_embedding_model: str
    user_profile_details: str


def _required_setting(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value or value.startswith("<"):
        raise RuntimeError(
            f"Missing required environment variable {name}. "
            "Copy .env.example to .env and set a real value (not the <placeholder>)."
        )
    return value


@lru_cache
def get_settings() -> Settings:
    load_dotenv(Path(__file__).resolve().parent / ".env")
    return Settings(
        foundry_project_endpoint=_required_setting("FOUNDRY_PROJECT_ENDPOINT"),
        memory_store_chat_model=_required_setting("MEMORY_STORE_CHAT_MODEL"),
        memory_store_embedding_model=_required_setting("MEMORY_STORE_EMBEDDING_MODEL"),
        user_profile_details=os.getenv(
            "USER_PROFILE_DETAILS",
            "Remember personal details, preferences, vehicles, work and schedule information.",
        ),
    )
