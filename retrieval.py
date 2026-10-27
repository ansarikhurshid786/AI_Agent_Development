"""Find the chunks in Supabase that are about the same thing as the user's question.

How it works (the "R" in RAG = Retrieval):
1. Turn the question into a vector (a list of 768 numbers) with the SAME model
   that made the vectors in the `chunks` table (nomic-embed-text in Ollama).
2. Ask Postgres (pgvector) how close the question vector is to every chunk vector.
3. Keep only chunks whose similarity is at least the cutoff, best first.

The chunks we find are later added to the question, so the AI can answer from them.
"""

import os
from dataclasses import dataclass

import psycopg2
from openai import OpenAI

EMBEDDING_MODEL = "nomic-embed-text"

# nomic-embed-text was trained with a task prefix. The chunks were saved with
# "search_document: ", so the question must use "search_query: ".
QUERY_PREFIX = "search_query: "

# Similarity goes from -1 to 1 (1 = same meaning). Below 0.5 is usually unrelated text.
MIN_SIMILARITY = 0.5
MAX_CHUNKS = 3  # too many chunks makes the prompt long and slow

# Ollama runs locally and speaks the same API as OpenAI, so the OpenAI client works.
# This is separate from the chat client because the chat model may be on Groq.
embedding_client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")


@dataclass
class Chunk:
    source: str  # file the text came from, e.g. "Khurshid_Ansari_CV.pdf"
    content: str
    similarity: float


def embed_query(question):
    """Turn the question into a vector."""
    response = embedding_client.embeddings.create(model=EMBEDDING_MODEL, input=QUERY_PREFIX + question)
    return response.data[0].embedding


def search_chunks(question, min_similarity=MIN_SIMILARITY, limit=MAX_CHUNKS):
    """Return the chunks most similar to the question, best first. Empty list if none pass the cutoff."""
    vector = str(embed_query(question))  # pgvector reads the text form "[0.1, 0.2, ...]"

    # `<=>` is pgvector's cosine DISTANCE (0 = same direction), so similarity = 1 - distance.
    # Sorting by distance (not similarity) lets Postgres use a vector index if the table gets one.
    sql = """
        SELECT source, content, 1 - (embedding <=> %(vector)s::vector) AS similarity
        FROM chunks
        WHERE 1 - (embedding <=> %(vector)s::vector) >= %(min_similarity)s
        ORDER BY embedding <=> %(vector)s::vector
        LIMIT %(limit)s
    """
    with psycopg2.connect(os.getenv("DATABASE_URL")) as conn, conn.cursor() as cur:
        cur.execute(sql, {"vector": vector, "min_similarity": min_similarity, "limit": limit})
        rows = cur.fetchall()
    conn.close()  # `with` only ends the transaction; it does not close the connection
    return [Chunk(source, content, similarity) for source, content, similarity in rows]


def build_prompt(question, chunks):
    """Put the found chunks above the question so the AI answers from them."""
    context = "\n\n".join(f"[{i}] (from {c.source})\n{c.content}" for i, c in enumerate(chunks, 1))
    return (
        "Answer the question using the context below. "
        "If the context does not contain the answer, say so.\n\n"
        f"Context:\n{context}\n\nQuestion: {question}"
    )
