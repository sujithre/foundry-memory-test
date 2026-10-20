# Foundry memory store test

Creates a memory store, writes memories through the `memory_search_preview` tool, and recalls them.

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env   # fill in your project endpoint and deployment names
az login

python ingest-memory.py
python query_memory.py <store_name> "What car do I drive?"
python query_memory.py <store_name> --list
```

The scope in the scripts uses placeholder IDs; any consistent string works as a partition key.
