"""Standalone test: create a NEW Foundry memory store and read it back.

Usage:
    python create-memory-store-only.py

Required environment variables:
    FOUNDRY_PROJECT_ENDPOINT   e.g. https://<account>.services.ai.azure.com/api/projects/<project>
    MEMORY_CHAT_MODEL          chat model deployment name in the project
    MEMORY_EMBEDDING_MODEL     embedding model deployment name in the project

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

PROFILE_DETAILS = (
    "Remember work preferences, communication style, preferred formats, recurring "
    "projects, teams, and working hours. Do NOT store credentials, secrets, health, "
    "financial, HR/performance, or other sensitive personal data."
)


def main() -> None:
    try:
        endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
        chat_model = os.environ["MEMORY_CHAT_MODEL"]
        embedding_model = os.environ["MEMORY_EMBEDDING_MODEL"]
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
