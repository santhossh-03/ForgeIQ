
from pathlib import Path

manual_path = Path("data/manuals/motor_troubleshooting.txt")

with open(manual_path, "r", encoding="utf-8") as file:
    manual_text = file.read()

print("Manual loaded successfully!")
print("Total characters:", len(manual_text))
print("\nManual content:\n")
print(manual_text)