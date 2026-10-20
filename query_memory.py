"""Query a memory store with a natural-language question.

The direct `search_memories` API currently times out server-side, so this
uses the WORKING approach: attach the `memory_search_preview` tool to the
Responses API and let the agent recall from the store. Also supports a raw
`--list` dump via `list_memories` (which also works).

Usage:
    # Ask a question (agent recalls from memory):
    python query_memory.py <store_name> "<your question>" [scope]

    # Raw list of all stored memories for the scope:
    python query_memory.py <store_name> --list [scope]

Examples:
    python query_memory.py memorystore-retest-20261009083609 "What car do I drive?"
    python query_memory.py memorystore-retest-20261009083609 --list
"""

import sys

from azure.ai.projects import AIProjectClient

from config import get_settings
from login import get_credential

# Same scope work_around.py writes to.
DEFAULT_SCOPE = (
    "00000000-0000-0000-0000-000000000000_00000000-0000-0000-0000-000000000000"
)


def _client() -> AIProjectClient:
    settings = get_settings()
    return AIProjectClient(
        endpoint=settings.foundry_project_endpoint,
        credential=get_credential(),
    )


def list_memories(store_name: str, scope: str) -> None:
    """Raw dump of every memory item in the store for a scope."""
    client = _client()
    items = list(client.beta.memory_stores.list_memories(name=store_name, scope=scope))
    print(f"Found {len(items)} memory item(s):\n")
    for it in items:
        d = dict(it)
        print(f"  - [{d.get('kind')}] {d.get('content', '')}")


def ask(store_name: str, question: str, scope: str) -> None:
    """Ask a question; the agent recalls from the store via the memory tool."""
    settings = get_settings()
    client = _client()
    oai = client.get_openai_client()

    tool = {
        "type": "memory_search_preview",
        "memory_store_name": store_name,
        "scope": scope,
    }

    conv = oai.conversations.create()
    resp = oai.responses.create(
        model=settings.memory_store_chat_model,
        conversation=conv.id,
        input=[{"type": "message", "role": "user", "content": question}],
        tools=[tool],
    )
    print("ANSWER:\n")
    print(resp.output_text)


def main() -> None:
    if len(sys.argv) < 3:
        print('Usage: python query_memory.py <store_name> "Do I have red color car" [scope]')
        print('   or: python query_memory.py <store_name> --list [scope]')
        return

    store_name = sys.argv[1]
    second = sys.argv[2]

    if second == "--list":
        scope = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_SCOPE
        print(f"Store: {store_name}\nScope: {scope}\n")
        list_memories(store_name, scope)
    else:
        question = second
        scope = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_SCOPE
        print(f"Store: {store_name}\nScope: {scope}\nQuestion: {question}\n")
        ask(store_name, question, scope)


if __name__ == "__main__":
    main()
