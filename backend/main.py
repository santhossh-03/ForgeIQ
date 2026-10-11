
from typing import Any, Literal
import json

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database.connection import initialize_database
from database.models import (
    get_investigation,
    list_investigations,
    save_investigation,
)
from rag.investigator import investigate_machine_fault


app = FastAPI(title="Industrial AI Troubleshooting Agent")


# Allow the local frontend to communicate with the backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class MachineFaultRequest(BaseModel):
    machine_name: str = Field(
        ...,
        min_length=1,
        description="Name or identifier of the machine.",
    )
    fault_description: str = Field(
        ...,
        min_length=1,
        description="Observed fault or machine symptoms.",
    )


class InvestigationResponse(BaseModel):
    status: Literal["success", "validation_failed", "error"]
    machine_name: str
    fault_description: str
    report_source: str | None = None
    log_analysis: dict[str, Any] | None = None
    retrieved_sections: list[dict[str, Any]] | None = None
    safety_instructions_included: bool | None = None
    report: str | None = None
    evidence_check_passed: bool | None = None
    evidence_issues: list[str] = Field(default_factory=list)
    message: str | None = None
    error: str | None = None


class InvestigationSavedResponse(InvestigationResponse):
    investigation_id: int


class InvestigationHistoryItem(BaseModel):
    id: int
    machine_name: str
    fault_description: str
    status: str
    report_source: str | None = None
    evidence_check_passed: int | None = None
    created_at: str


@app.on_event("startup")
def startup():
    initialize_database()


@app.get("/")
def home():
    return {"message": "Industrial AI Agent is running!"}


@app.post(
    "/investigate",
    response_model=InvestigationSavedResponse,
)
def investigate_fault(request: MachineFaultRequest):
    result = investigate_machine_fault(
        machine_name=request.machine_name,
        fault_description=request.fault_description,
    )

    try:
        investigation_id = save_investigation(result)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Investigation completed, but saving its result failed.",
        ) from exc

    return {
        **result,
        "investigation_id": investigation_id,
    }


@app.get(
    "/investigations",
    response_model=list[InvestigationHistoryItem],
)
def investigation_history(
    limit: int = Query(default=20, ge=1, le=100),
):
    return list_investigations(limit=limit)


@app.get("/investigations/{investigation_id}")
def investigation_detail(investigation_id: int):
    result = get_investigation(investigation_id)

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Investigation not found.",
        )

    for field in (
        "log_analysis",
        "retrieved_sections",
        "evidence_issues",
    ):
        value = result.get(field)
        if value is not None:
            result[field] = json.loads(value)

    if result.get("safety_instructions_included") is not None:
        result["safety_instructions_included"] = bool(
            result["safety_instructions_included"]
        )

    if result.get("evidence_check_passed") is not None:
        result["evidence_check_passed"] = bool(
            result["evidence_check_passed"]
        )

    return result
