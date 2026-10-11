from pathlib import Path
import math
import time
import json
import ollama


# 1. Read the machine manual
total_start = time.perf_counter()

manual_path = Path("data/manuals/motor_troubleshooting.txt")

with open(manual_path, "r", encoding="utf-8") as file:
    manual_text = file.read()


# 2. Split the manual using section headings

sections = [
    "Problem 1: Motor overheating",
    "Problem 2: Excessive vibration",
    "Safety:"
]

chunks = []

for index, heading in enumerate(sections):
    start = manual_text.find(heading)

    if start == -1:
        print(f"Warning: Section not found: {heading}")
        continue

    if index + 1 < len(sections):
        next_start = manual_text.find(
            sections[index + 1],
            start + len(heading)
        )
    else:
        next_start = len(manual_text)

    if next_start == -1:
        next_start = len(manual_text)

    chunk = manual_text[start:next_start].strip()
    chunks.append(chunk)

print(f"Manual sections created: {len(chunks)}")

# 3. Generate or load cached document embeddings

cache_path = Path("data/cache/manual_embeddings.json")

start_time = time.perf_counter()

if cache_path.exists():
    with open(cache_path, "r", encoding="utf-8") as file:
        cached_data = json.load(file)

    if cached_data["chunks"] == chunks:
        document_embeddings = cached_data["embeddings"]
        print("Loaded document embeddings from cache.")
    else:
        print("Manual changed. Creating new embeddings.")

        document_response = ollama.embed(
            model="nomic-embed-text",
            input=chunks
        )

        document_embeddings = document_response["embeddings"]

        with open(cache_path, "w", encoding="utf-8") as file:
            json.dump(
                {
                    "chunks": chunks,
                    "embeddings": document_embeddings
                },
                file
            )

        print("Updated embedding cache.")

else:
    document_response = ollama.embed(
        model="nomic-embed-text",
        input=chunks
    )

    document_embeddings = document_response["embeddings"]

    cache_path.parent.mkdir(parents=True, exist_ok=True)

    with open(cache_path, "w", encoding="utf-8") as file:
        json.dump(
            {
                "chunks": chunks,
                "embeddings": document_embeddings
            },
            file
        )

    print("Created embedding cache.")

print(
    f"Document embedding/cache time: "
    f"{time.perf_counter() - start_time:.2f} seconds"
)

# 4. Ask the user for a question
query = input("\nEnter your machine fault question: ").strip()

if not query:
    print("Please enter a machine fault question.")
    raise SystemExit

# 5. Generate an embedding for the question
start_time = time.perf_counter()

query_response = ollama.embed(
    model="nomic-embed-text",
    input=query
)

query_embedding = query_response["embeddings"][0]

print(
    f"Question embedding time: "
    f"{time.perf_counter() - start_time:.2f} seconds"
)


# 6. Calculate cosine similarity
def cosine_similarity(vector_a, vector_b):
    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(
        sum(a * a for a in vector_a)
    )

    magnitude_b = math.sqrt(
        sum(b * b for b in vector_b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


# 7. Retrieve the two most relevant chunks
ranked_chunks = []

for index, chunk in enumerate(chunks):
    score = cosine_similarity(
        query_embedding,
        document_embeddings[index]
    )

    ranked_chunks.append((score, chunk))

ranked_chunks.sort(
    key=lambda item: item[0],
    reverse=True
)

top_chunks = ranked_chunks[:2]

context = "\n\n".join(
    chunk for score, chunk in top_chunks
)

print("\nRelevant manual sections retrieved:")

for rank, (score, chunk) in enumerate(top_chunks, start=1):
    print(f"\n--- Rank {rank} ---")
    print(f"Similarity: {score:.4f}")
    print(f"Retrieved text:\n{chunk}")

# 8. Ask Qwen3 to generate the troubleshooting report
start_time = time.perf_counter()

response = ollama.chat(
    model="qwen3:4b",
    messages=[
        {
            "role": "system",
            "content": (
                "You are an industrial troubleshooting assistant. "
                "Use only the supplied manual context. "
                "List documented causes and recommended inspections. "
                "Include essential safety precautions. "
                "If information is missing, say so. "
                "Do not invent measurements or specifications. "
                "Be concise and use at most 150 words."
            )
        },
        {
            "role": "user",
            "content": (
                "/no_think\n"
                f"Question: {query}\n\n"
                f"Manual context:\n{context}"
            )
        }
    ],
    options={
        "num_predict": 220,
        "temperature": 0
    }
)
print(
    f"\nQwen generation time: "
    f"{time.perf_counter() - start_time:.2f} seconds"
)


# 9. Display the final report
print("\n--- AI Troubleshooting Report ---\n")
print(response["message"]["content"])

print(
    f"\nTotal execution time: "
    f"{time.perf_counter() - total_start:.2f} seconds"
)