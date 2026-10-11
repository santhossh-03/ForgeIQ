
from pathlib import Path
import ollama

# Read the machine manual
manual_path = Path("data/manuals/motor_troubleshooting.txt")

with open(manual_path, "r", encoding="utf-8") as file:
    manual_text = file.read()

# Create chunks
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

# Convert chunks into embeddings
response = ollama.embed(
    model="nomic-embed-text",
    input=chunks
)

embeddings = response["embeddings"]

print("Total chunks:", len(chunks))
print("Total embeddings:", len(embeddings))
print("Vector dimensions:", len(embeddings[0]))
print("First 5 numbers:", embeddings[0][:5])