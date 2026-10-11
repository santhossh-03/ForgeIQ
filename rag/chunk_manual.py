
from pathlib import Path

# 1. Read the manual
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
        next_start = manual_text.find(sections[index + 1], start + len(heading))
    else:
        next_start = len(manual_text)

    if next_start == -1:
        next_start = len(manual_text)

    chunk = manual_text[start:next_start].strip()
    chunks.append(chunk)


# 3. Display the chunks
print(f"Manual sections created: {len(chunks)}")

for index, chunk in enumerate(chunks, start=1):
    print(f"\n--- Chunk {index} ---")
    print(chunk)