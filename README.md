\# ForgeIQ — Industrial AI Troubleshooting Agent



ForgeIQ is a local AI-powered industrial troubleshooting application that helps investigate machine faults using machine-log analysis, Retrieval-Augmented Generation (RAG), a local LLM, and evidence validation.



\## Features



\- Machine fault investigation from observed symptoms

\- Machine-log analysis

\- RAG-based retrieval from troubleshooting manuals

\- Local LLM inference using Ollama and Qwen3 4B

\- Semantic embeddings using `nomic-embed-text`

\- Evidence validation and structured investigation reports

\- Safety instructions in reports

\- SQLite investigation history

\- Web frontend for submitting investigations and viewing reports

\- Automated tests for retrieval, reporting, validation, APIs, and databases



\## Architecture



1\. User submits a machine fault through the web interface.

2\. FastAPI receives and validates the request.

3\. Machine logs are analyzed.

4\. RAG retrieves relevant troubleshooting manual sections.

5\. Ollama runs the local language model to generate an investigation report.

6\. Evidence validation checks the report.

7\. The investigation is saved in SQLite.



\## Technology Stack



\- Python

\- FastAPI and Pydantic

\- SQLite

\- Ollama

\- Qwen3 4B Instruct

\- `nomic-embed-text`

\- HTML, CSS, and JavaScript



\## Prerequisites



Install Python 3.10 or newer, Git, and \[Ollama](https://ollama.com/download).



Download the required Ollama models:



```powershell

ollama pull qwen3:4b-instruct

ollama pull nomic-embed-text

```



Ensure Ollama is running before performing investigations.



\## Installation



Clone the repository:



```powershell

git clone YOUR\_GITHUB\_REPOSITORY\_URL

cd industrial\_ai\_agent

```



Create and activate a virtual environment on Windows:



```powershell

python -m venv venv

.\\venv\\Scripts\\Activate.ps1

```



Install the core backend dependencies:



```powershell

python -m pip install fastapi "uvicorn\[standard]" pydantic ollama

```



Install any additional packages required by the project before running it.



\## Run the Backend



From the project root:



```powershell

uvicorn backend.main:app --reload

```



\- Backend: http://127.0.0.1:8000

\- API documentation: http://127.0.0.1:8000/docs



\## Run the Frontend



Open a second terminal in the project root:



```powershell

python -m http.server 5500 --directory frontend

```



Open http://127.0.0.1:5500 in your browser.



\## API Endpoints



| Method | Endpoint | Purpose |

|---|---|---|

| GET | `/` | Check backend availability |

| POST | `/investigate` | Investigate a machine fault |

| GET | `/investigations` | Retrieve investigation history |

| GET | `/investigations/{investigation\_id}` | Retrieve a saved investigation |



\## Run Tests



From the project root, with the virtual environment activated:



```powershell

python -m pytest -q

```



Some tests may require Ollama or downloaded models to be available.



\## Project Structure



```text

industrial\_ai\_agent/

├── agents/       # Machine-log analysis

├── backend/      # FastAPI application

├── data/         # Manuals and sample machine logs

├── database/     # Database connection and persistence

├── frontend/     # Web interface

├── models/       # Model-related resources

├── rag/          # Retrieval and investigation pipeline

├── tests/        # Automated tests

├── .gitignore

└── README.md

```



\## Safety and Limitations



ForgeIQ is an investigation-support prototype, not a replacement for qualified maintenance personnel or approved maintenance procedures. AI-generated root causes are hypotheses and must be verified against physical evidence. Follow site safety rules and equipment-specific procedures before inspection or repair.



\## Learning Goals



This project demonstrates practical exploration of local LLMs, embeddings, RAG pipelines, evidence validation, APIs, databases, and frontend integration.



\## Author



Developed as a hands-on AI engineering project focused on industrial AI troubleshooting and local LLM applications.

