"""Create a NEW memory store, add memories, read back, recall."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
)
from azure.identity import AzureCliCredential

from config import get_settings

AAD = "00000000-0000-0000-0000-000000000000"  # replace with your object id (optional)
TENANT = "00000000-0000-0000-0000-000000000000"  # replace with your tenant id (optional)
SCOPE = f"{AAD}_{TENANT}"

TURNS = [
    "Remember: I drive a blue Tesla Model 3 and my parking slot is B-42.",
    "Also, my team lead is Priya and our sprint review is every Thursday at 4pm IST.",
]
QUESTION = "What car do I drive, and when is our sprint review?"


def dump(client: AIProjectClient, store: str) -> list:
    items = list(client.beta.memory_stores.list_memories(name=store, scope=SCOPE))
    print(f"    {len(items)} item(s)")
    for it in items:
        d = dict(it)
        print(f"      [{d.get('kind')}] {str(d.get('content', ''))[:120]}")
    return items


def main() -> None:
    s = get_settings()
    client = AIProjectClient(
        endpoint=s.foundry_project_endpoint,
        credential=AzureCliCredential(process_timeout=60),
    )
    oai = client.get_openai_client()

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    store_name = f"memorystore-retest-{stamp}"

    # ---- 1. CREATE THE STORE -------------------------------------------
    store = client.beta.memory_stores.create(
        name=store_name,
        definition=MemoryStoreDefaultDefinition(
            chat_model=s.memory_store_chat_model,          # gpt-5.2
            embedding_model=s.memory_store_embedding_model,  # text-embedding-3-small
            options=MemoryStoreDefaultOptions(
                chat_summary_enabled=True,
                user_profile_enabled=True,
                user_profile_details=s.user_profile_details,
            ),
        ),
        description="Retest - memories written via memory_search_preview tool",
    )
    print(f"[1] created {store.name}  scope={SCOPE}")

    # ---- The tool that makes memory happen ------------------------------
    tool = {
        "type": "memory_search_preview",
        "memory_store_name": store_name,
        "scope": SCOPE,
        "update_delay": 1,     # seconds; use 300 in production
    }

    print("[2] BEFORE")
    before = dump(client, store_name)

    # ---- 2. ADD MEMORIES (no direct write API!) -------------------------
    print("[3] ADD MEMORIES")
    conv = oai.conversations.create()
    for i, text in enumerate(TURNS, start=1):
        resp = oai.responses.create(
            model=s.memory_store_chat_model,
            conversation=conv.id,
            input=[{"type": "message", "role": "user", "content": text}],
            tools=[tool],
        )
        print(f"    turn {i} AGENT: {resp.output_text[:120]}")

    print("[4] wait 45s for extraction")
    time.sleep(45)

    print("[5] AFTER")
    after = dump(client, store_name)
    delta = len(after) - len(before)
    print(f"    RESULT: {len(before)} -> {len(after)} (delta {delta:+d})")

    # ---- 3. RECALL IN A FRESH CONVERSATION ------------------------------
    print("[6] RECALL")
    conv2 = oai.conversations.create()
    resp = oai.responses.create(
        model=s.memory_store_chat_model,
        conversation=conv2.id,
        input=[{"type": "message", "role": "user", "content": QUESTION}],
        tools=[tool],
    )
    print(f"    AGENT: {resp.output_text[:320]}")

    text = (resp.output_text or "").lower()
    print(f"    write  : {'PASS' if delta > 0 else 'FAIL'}")
    print(f"    recall : {'PASS' if ('tesla' in text and 'thursday' in text) else 'FAIL'}")
    print(f"    store  : {store_name}")


if __name__ == "__main__":
    main()