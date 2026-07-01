"""Pydantic request/response models for the REST API."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SupportRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "subject": "Production app keeps returning 500 errors since this morning",
                    "body": "Worse under load since 9am. No attachments in this JSON call.",
                }
            ]
        }
    }

    subject: str = Field(..., description="Email subject line", examples=["App returns 500 errors"])
    body: str = Field("", description="Email body text", examples=["Started at 9am, worse under load."])


class SupportResponse(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "status": "answered",
                    "answer": "Likely DB connection pool exhaustion. See KB-001 for remediation steps.",
                    "category": "database",
                    "severity": "high",
                    "problem_summary": "Checkout 500 errors under load",
                    "grounding_score": 0.82,
                    "references": ["kb-001-db-connection-pool"],
                    "log_was_large": False,
                    "log_format": "spring",
                    "unsupported_claims": [],
                    "trace": [
                        "ingest",
                        "triage",
                        "log_analysis",
                        "retrieve_kb",
                        "draft_response",
                        "guardrails",
                        "finalize",
                    ],
                }
            ]
        }
    }

    status: Literal["answered", "escalated"]
    answer: str
    category: str = ""
    severity: str = ""
    problem_summary: str = ""
    grounding_score: float = 0.0
    references: list[str] = Field(default_factory=list)
    log_was_large: bool = False
    log_format: str = ""
    unsupported_claims: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)


class RebuildResponse(BaseModel):
    indexed_chunks: int = Field(..., description="Number of KB chunks written to Chroma")
    detail: str = Field(..., description="Human-readable result message")


class BatchTicket(BaseModel):
    subject: str
    body: str = ""
    attachment_paths: list[str] = Field(
        default_factory=list,
        description="Paths relative to project root, e.g. sample_data/logs/app-db.log",
    )


class BatchRequest(BaseModel):
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "tickets": [
                        {
                            "subject": "Production app keeps returning 500 errors",
                            "body": "Worse under load",
                            "attachment_paths": ["sample_data/logs/app-db.log"],
                        },
                        {
                            "subject": "Printer on floor 3 beeps twice",
                            "body": "Not an IT infrastructure issue",
                            "attachment_paths": [],
                        },
                    ]
                }
            ]
        }
    }

    tickets: list[BatchTicket] = Field(..., min_length=1)


class BatchTicketResult(BaseModel):
    subject: str
    status: str
    category: str = ""
    grounding_score: float = 0.0
    log_was_large: bool = False
    error: str = ""


class BatchResponse(BaseModel):
    total: int
    answered: int
    escalated: int
    results: list[BatchTicketResult]


class HealthResponse(BaseModel):
    status: str
    name: str
    version: str
    model: str
    web_search: bool
    mcp: bool
    env_file: str | None = None


class SamplesResponse(BaseModel):
    emails: list[str] = Field(..., description="Relative paths to sample email JSON files")
    logs: list[str] = Field(..., description="Relative paths to sample log files")


def state_to_response(state: dict[str, Any]) -> SupportResponse:
    return SupportResponse(
        status=state.get("status", "escalated"),
        answer=state.get("answer", ""),
        category=state.get("category", ""),
        severity=state.get("severity", ""),
        problem_summary=state.get("problem_summary", ""),
        grounding_score=float(state.get("grounding_score", 0.0) or 0.0),
        references=state.get("references", []) or [],
        log_was_large=bool(state.get("log_was_large", False)),
        log_format=state.get("log_format", "") or "",
        unsupported_claims=state.get("unsupported_claims", []) or [],
        trace=state.get("trace", []) or [],
    )
