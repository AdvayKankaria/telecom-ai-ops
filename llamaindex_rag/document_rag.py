"""LlamaIndex document RAG over policy text files."""

from __future__ import annotations

import os

os.environ["HF_HOME"] = ".hf_cache"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

from utils.config import DOCS_PATH, INDEX_PATH, OPENAI_API_KEY, PROJECT_ROOT

from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)

# pyrefly: ignore [missing-import]
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

# pyrefly: ignore [missing-import]
from llama_index.llms.openai import OpenAI


def _configure_llamaindex() -> None:
    """Configure LlamaIndex settings lazily to keep imports stable."""
    Settings.embed_model = HuggingFaceEmbedding(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )
    Settings.llm = OpenAI(model="gpt-4.1-mini", api_key=OPENAI_API_KEY)


def _get_or_create_index() -> VectorStoreIndex:
    """Load persisted index if present, otherwise build and persist one."""
    _configure_llamaindex()
    if INDEX_PATH.exists():
        try:
            storage_context = StorageContext.from_defaults(persist_dir=str(INDEX_PATH))
            return load_index_from_storage(storage_context)
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"Failed to load persisted vector index: {exc}") from exc

    try:
        documents = SimpleDirectoryReader(input_dir=str(DOCS_PATH)).load_data()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Failed to load policy documents from {DOCS_PATH}: {exc}"
        ) from exc

    if not documents:
        raise RuntimeError(f"No policy .txt files found in {DOCS_PATH}.")

    try:
        index = VectorStoreIndex.from_documents(documents)
        index.storage_context.persist(persist_dir=str(INDEX_PATH))
        return index
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to build/persist vector index: {exc}") from exc


def query_policy_documents(question: str) -> str:
    """Query policy docs and return a natural language answer."""
    try:
        index = _get_or_create_index()
        query_engine = index.as_query_engine()
        response = query_engine.query(question)
        return str(response)
    except RuntimeError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Policy RAG query failed: {exc}") from exc
