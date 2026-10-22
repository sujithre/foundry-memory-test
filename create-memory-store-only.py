"""Standalone test: create a NEW Foundry memory store and read it back.

Usage:
    python create-memory-store-only.py

Reads a .env file next to this script (same one as the other scripts), or the
environment. Required:
    FOUNDRY_PROJECT_ENDPOINT   e.g. https://<account>.services.ai.azure.com/api/projects/<project>
    MEMORY_STORE_CHAT_MODEL    chat model deployment name in the project
    MEMORY_STORE_EMBEDDING_MODEL  embedding model deployment name in the project
    (MEMORY_CHAT_MODEL / MEMORY_EMBEDDING_MODEL are also accepted.)

Optional:
    MEMORY_STORE_NAME          defaults to memorystore-test-<timestamp>
"""

from __future__ import annotations

import datetime
import os
import sys

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
)
from azure.identity import AzureCliCredential
from dotenv import load_dotenv

# Load the .env next to this script regardless of the current directory.
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"))
PROFILE_DETAILS = (
    "Remember work preferences, communication style, preferred formats, recurring "
    "projects, teams, and working hours. Do NOT store credentials, secrets, health, "
    "financial, HR/performance, or other sensitive personal data."
)


def main() -> None:
    try:
        endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
        chat_model = os.environ.get("MEMORY_CHAT_MODEL") or os.environ["MEMORY_STORE_CHAT_MODEL"]
        embedding_model = (
            os.environ.get("MEMORY_EMBEDDING_MODEL") or os.environ["MEMORY_STORE_EMBEDDING_MODEL"]
        )
    except KeyError as missing:
        sys.exit(f"Missing required environment variable: {missing}")

    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d%H%M%S")
    name = os.getenv("MEMORY_STORE_NAME", f"memorystore-test-{stamp}")

    client = AIProjectClient(
        endpoint=endpoint, credential=AzureCliCredential(process_timeout=60)
    )
    stores = client.beta.memory_stores

    print(f"Creating memory store '{name}'")
    print(f"  chat model      : {chat_model}")
    print(f"  embedding model : {embedding_model}")

    store = stores.create(
        name=name,
        description="Test memory store created by create-memory-store-only.py",
        definition=MemoryStoreDefaultDefinition(
            chat_model=chat_model,
            embedding_model=embedding_model,
            options=MemoryStoreDefaultOptions(
                user_profile_enabled=True,
                chat_summary_enabled=True,
                user_profile_details=PROFILE_DETAILS,
            ),
        ),
    )
    print(f"CREATED: name={store.name} id={store.id}")

    fetched = stores.get(name)
    print(f"READ BACK: name={fetched.name} id={fetched.id}")

    print("\nAll memory stores in this project:")
    for item in stores.list():
        print(f"  - {item.name}")

    print(
        f"\nSUCCESS. To delete this test store later: "
        f"client.beta.memory_stores.delete('{name}')"
    )


if __name__ == "__main__":
    main()
