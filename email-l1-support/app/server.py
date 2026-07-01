"""FastAPI application factory.

REST API for the L1 support LangGraph pipeline. Interactive docs: /docs
"""
from __future__ import annotations

import logging
import logging.config
from pathlib import Path

import yaml
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.openapi.utils import get_openapi

from app.config import settings
from app.graph import build_graph
from app.schemas import (
    BatchRequest,
    BatchResponse,
    BatchTicketResult,
    HealthResponse,
    RebuildResponse,
    SamplesResponse,
    SupportRequest,
    SupportResponse,
    state_to_response,
)
from app.state import new_state

logger = logging.getLogger(__name__)

TAGS = [
    {"name": "health", "description": "Service health and configuration summary."},
    {"name": "support", "description": "Process support tickets (JSON or file upload)."},
    {"name": "admin", "description": "Maintenance: KB rebuild and sample data listing."},
]

OPENAPI_SERVERS = [
    {"url": "http://127.0.0.1:8080", "description": "Local development server"},
]


def _configure_logging() -> None:
    cfg_path = settings.root / "config" / "logging.yaml"
    if cfg_path.is_file():
        with open(cfg_path, "r", encoding="utf-8") as fh:
            logging.config.dictConfig(yaml.safe_load(fh))


def _read_attachments(paths: list[str]) -> list[dict]:
    out: list[dict] = []
    for rel in paths:
        path = settings.resolve_path(rel)
        if not path.is_file():
            raise HTTPException(status_code=400, detail=f"Attachment not found: {rel}")
        out.append({
            "filename": path.name,
            "mime": "",
            "bytes": path.read_bytes(),
        })
    return out


def create_app() -> FastAPI:
    _configure_logging()
    app = FastAPI(
        title=settings.get("app", "name", default="Email L1 Support Agent"),
        version=settings.get("app", "version", default="1.0.0"),
        description=(
            "L1 email support automation: ingest attachments, analyse logs, "
            "retrieve KB articles, optional web search, guardrails, reply or escalate.\n\n"
            "**Interactive docs:** `/docs` (Swagger UI) · `/redoc` (ReDoc) · `/openapi.json`"
        ),
        openapi_tags=TAGS,
        servers=OPENAPI_SERVERS,
    )
    graph = build_graph()

    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=TAGS,
            servers=OPENAPI_SERVERS,
        )
        app.openapi_schema = schema
        return app.openapi_schema

    app.openapi = custom_openapi

    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["health"],
        summary="Health check",
    )
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            name=settings.get("app", "name"),
            version=settings.get("app", "version"),
            model=settings.get("llm", "model"),
            web_search=bool(settings.get("web_search", "enabled")),
            mcp=bool(settings.get("mcp", "enabled")),
            env_file=settings.env_file_used,
        )

    @app.post(
        "/support",
        response_model=SupportResponse,
        tags=["support"],
        summary="Process ticket (JSON)",
    )
    def support(req: SupportRequest) -> SupportResponse:
        """Process a ticket from JSON (no attachments). Use /support/upload for files."""
        state = new_state(subject=req.subject, body=req.body)
        result = graph.invoke(state)
        return state_to_response(result)

    @app.post(
        "/support/upload",
        response_model=SupportResponse,
        tags=["support"],
        summary="Process ticket (multipart upload)",
    )
    async def support_upload(
        subject: str = Form(..., description="Email subject"),
        body: str = Form("", description="Email body"),
        files: list[UploadFile] = File(default=[], description="One or more attachments"),
    ) -> SupportResponse:
        """Multipart upload: subject, body, and any mix of log/json/csv/pdf/image files."""
        max_bytes = int(settings.get("server", "max_upload_mb", default=25)) * 1024 * 1024
        attachments = []
        for f in files:
            content = await f.read()
            if len(content) > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=(
                        f"File {f.filename} exceeds the "
                        f"{settings.get('server', 'max_upload_mb')} MB upload limit"
                    ),
                )
            attachments.append({
                "filename": f.filename,
                "mime": f.content_type or "",
                "bytes": content,
            })
        state = new_state(subject=subject, body=body, attachments=attachments)
        result = graph.invoke(state)
        return state_to_response(result)

    @app.post(
        "/support/batch",
        response_model=BatchResponse,
        tags=["support"],
        summary="Process multiple tickets",
    )
    def support_batch(req: BatchRequest) -> BatchResponse:
        """Run several tickets in one call. Attachment paths are read from disk on the server."""
        max_batch = int(settings.get("server", "max_batch_size", default=20))
        if len(req.tickets) > max_batch:
            raise HTTPException(
                status_code=400,
                detail=f"Batch size {len(req.tickets)} exceeds limit of {max_batch}",
            )

        results: list[BatchTicketResult] = []
        answered = escalated = 0
        for ticket in req.tickets:
            try:
                attachments = _read_attachments(ticket.attachment_paths)
                state = new_state(
                    subject=ticket.subject,
                    body=ticket.body,
                    attachments=attachments,
                )
                out = graph.invoke(state)
                resp = state_to_response(out)
                if resp.status == "answered":
                    answered += 1
                else:
                    escalated += 1
                results.append(BatchTicketResult(
                    subject=ticket.subject,
                    status=resp.status,
                    category=resp.category,
                    grounding_score=resp.grounding_score,
                    log_was_large=resp.log_was_large,
                ))
            except HTTPException:
                raise
            except Exception as exc:
                logger.exception("Batch ticket failed: %s", ticket.subject)
                escalated += 1
                results.append(BatchTicketResult(
                    subject=ticket.subject,
                    status="escalated",
                    error=str(exc),
                ))

        return BatchResponse(
            total=len(results),
            answered=answered,
            escalated=escalated,
            results=results,
        )

    @app.post(
        "/admin/rebuild-kb",
        response_model=RebuildResponse,
        tags=["admin"],
        summary="Rebuild knowledge-base index",
    )
    def rebuild_kb() -> RebuildResponse:
        """Re-index knowledge_base/ into Chroma. Run after adding or editing KB articles."""
        from app.rag.ingest_kb import build_knowledge_base

        count = build_knowledge_base()
        return RebuildResponse(indexed_chunks=count, detail="Knowledge base re-indexed")

    @app.get(
        "/admin/samples",
        response_model=SamplesResponse,
        tags=["admin"],
        summary="List sample emails and logs",
    )
    def list_samples() -> SamplesResponse:
        """List bundled sample emails and log files (for curl demos and Swagger)."""
        root = settings.root
        emails = sorted(
            str(p.relative_to(root)).replace("\\", "/")
            for p in (root / "sample_data" / "emails").glob("*.json")
        )
        logs = sorted(
            str(p.relative_to(root)).replace("\\", "/")
            for p in (root / "sample_data" / "logs").glob("*")
            if p.is_file()
        )
        return SamplesResponse(emails=emails, logs=logs)

    return app
