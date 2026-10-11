
from pathlib import Path
import math
import ollama

# 1. Read the manual
manual_path = Path("data/manuals/motor_troubleshooting.txt")

with open(manual_path, "r", encoding="utf-8") as file:
    manual_text = file.read()

# 2. Split the manual into overlapping chunks
words = manual_text.split()
chunk_size = 100
overlap = 20

chunks = []
start = 0

while start < len(words):
    end = start + chunk_size
    chunks.append(" ".join(words[start:end]))

    if end >= len(words):
        break

    start = end - overlap

# 3. Generate embeddings for the chunks
document_response = ollama.embed(
    model="nomic-embed-text",
    input=chunks
)

document_embeddings = document_response["embeddings"]

# 4. Get the user's question
query = "Why is the motor temperature too high?"

query_response = ollama.embed(
    model="nomic-embed-text",
    input=query
)

query_embedding = query_response["embeddings"][0]


# 5. Calculate cosine similarity
def cosine_similarity(vector_a, vector_b):
    dot_product = sum(
        a * b for a, b in zip(vector_a, vector_b)
    )

    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


# 6. Score every chunk against the question
results = []

for index, chunk in enumerate(chunks):
    score = cosine_similarity(
        query_embedding,
        document_embeddings[index]
    )

    results.append((score, chunk))

# 7. Rank the chunks from highest similarity to lowest
results.sort(key=lambda item: item[0], reverse=True)

# 8. Display the ranked results
print("Question:", query)

for rank, (score, chunk) in enumerate(results, start=1):
    print(f"\nRank {rank} | Similarity: {score:.4f}")
    print(chunk)