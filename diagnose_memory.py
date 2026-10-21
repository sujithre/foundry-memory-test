"""Isolate which piece breaks the memory_search_preview call (500 server_error).

Runs a small matrix against the project in .env and prints PASS/FAIL plus the
request id of every failure (quote these to Azure support).

Usage:
    python diagnose_memory.py --chat gpt-5.2 gpt-5.4 --embedding text-embedding-3-small

Steps per chat model:
  A. responses.create WITHOUT any tool            -> is the model deployment itself reachable?
  B. responses.create WITH memory_search_preview  -> for each embedding model, using a new store
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone

from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
)
from azure.identity import AzureCliCredential

from config import get_settings

SCOPE = "diagnose_user"


def _request_id(err: Exception) -> str:
    body = getattr(err, "body", None)
    if isinstance(body, dict):
        inner = body.get("error", body)
        return str(inner.get("request_id", ""))
    return ""


def _run(label: str, fn) -> bool:
    try:
        text = fn()
        print(f"  PASS  {label}: {text[:80]!r}")
        return True
    except Exception as err:  # noqa: BLE001 - diagnostic script, show everything
        print(f"  FAIL  {label}: {type(err).__name__} request_id={_request_id(err)}")
        print(f"        {str(err)[:200]}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chat", nargs="+", help="chat deployment names to test")
    parser.add_argument("--embedding", nargs="+", help="embedding deployment names to test")
    args = parser.parse_args()

    s = get_settings()
    chats = args.chat or [s.memory_store_chat_model]
    embeddings = args.embedding or [s.memory_store_embedding_model]

    client = AIProjectClient(
        endpoint=s.foundry_project_endpoint,
        credential=AzureCliCredential(process_timeout=60),
    )
    oai = client.get_openai_client()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")

    results: list[tuple[str, bool]] = []
    for chat in chats:
        print(f"\n[chat model: {chat}]")

        ok = _run(
            "A. no tool",
            lambda: oai.responses.create(model=chat, input="Say hi in 3 words.").output_text,
        )
        results.append((f"{chat} / no tool", ok))

        for emb in embeddings:
            store_name = f"diag-{stamp}-{len(results)}"
            try:
                client.beta.memory_stores.create(
                    name=store_name,
                    definition=MemoryStoreDefaultDefinition(
                        chat_model=chat,
                        embedding_model=emb,
                        options=MemoryStoreDefaultOptions(
                            chat_summary_enabled=True,
                            user_profile_enabled=True,
                            user_profile_details="Remember user preferences.",
                        ),
                    ),
                    description="diagnostic",
                )
            except Exception as err:  # noqa: BLE001
                print(f"  FAIL  create store ({chat}, {emb}): {str(err)[:200]}")
                results.append((f"{chat} + {emb} / create store", False))
                continue

            tool = {
                "type": "memory_search_preview",
                "memory_store_name": store_name,
                "scope": SCOPE,
                "update_delay": 1,
            }
            ok = _run(
                f"B. memory tool (store chat={chat}, embedding={emb})",
                lambda: oai.responses.create(
                    model=chat,
                    input=[{"type": "message", "role": "user", "content": "Remember: I like sweets."}],
                    tools=[tool],
                ).output_text,
            )
            results.append((f"{chat} + {emb} / memory tool", ok))

    print("\n=== SUMMARY ===")
    for name, ok in results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")


if __name__ == "__main__":
    main()
