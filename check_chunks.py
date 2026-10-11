
from rag.investigator import load_manual_chunks

chunks = load_manual_chunks()

print("Total chunks:", len(chunks))

for i, chunk in enumerate(chunks, start=1):
    print()
    print("Chunk:", i)
    print("Heading:", chunk["heading"])
    print("Characters:", len(chunk["text"]))
