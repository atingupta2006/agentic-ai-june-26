"""Guardrails AI integration for draft validation.

Custom validators implement L1 policy (keywords, references, grounding).
Optional Hub validators can be enabled in config after ``guardrails configure``.

Run once (per machine, for Hub PII):
    guardrails configure
    guardrails hub install hub://guardrails/detect_pii
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Any

from guardrails import Guard
from guardrails.validator_base import FailResult, PassResult, Validator, register_validator

from app.config import settings
from app.llm import chat_json

logger = logging.getLogger(__name__)

_last_grounding: dict[str, Any] = {}


@register_validator(name="l1-policy-keywords", data_type="string")
class PolicyKeywordCheck(Validator):
    """Escalate when the ticket text matches configured policy keywords."""

    def validate(self, value: str, metadata: dict | None = None) -> PassResult | FailResult:
        meta = metadata or {}
        haystack = meta.get("ticket_text", "").lower()
        for keyword in meta.get("escalate_keywords", []):
            if str(keyword).lower() in haystack:
                return FailResult(error_message=f"policy: matched '{keyword}'")
        return PassResult()


@register_validator(name="l1-min-references", data_type="string")
class MinReferencesCheck(Validator):
    """Require a minimum number of KB / web references before auto-reply."""

    def validate(self, value: str, metadata: dict | None = None) -> PassResult | FailResult:
        meta = metadata or {}
        num_refs = int(meta.get("num_refs", 0))
        min_refs = int(meta.get("min_refs", 1))
        if num_refs < min_refs:
            return FailResult(
                error_message=f"evidence: only {num_refs} reference(s), need {min_refs}"
            )
        return PassResult()


@register_validator(name="l1-grounding", data_type="string")
class GroundingCheck(Validator):
    """LLM grounding audit — prompt text comes from config/prompts.yaml."""

    def validate(self, value: str, metadata: dict | None = None) -> PassResult | FailResult:
        global _last_grounding
        meta = metadata or {}
        prompts = settings.prompt("grounding_check")
        audit = chat_json(
            prompts["system"],
            prompts["user"].format(
                evidence=meta.get("evidence", "(no evidence)"),
                draft=value,
            ),
        )
        score = float(audit.get("grounding_score", 0.0) or 0.0)
        unsupported = audit.get("unsupported_claims", []) or []
        min_score = float(meta.get("min_grounding_score", 0.6))
        _last_grounding = {
            "grounding_score": score,
            "unsupported_claims": unsupported,
        }
        if score < min_score:
            return FailResult(
                error_message=f"grounding: score {score:.2f} < {min_score:.2f}"
            )
        return PassResult()


@dataclass
class GuardrailOutcome:
    decision: str
    grounding_score: float = 0.0
    unsupported_claims: list[str] = field(default_factory=list)
    escalation_reason: str = ""
    validated_draft: str = ""


def _support_validators() -> list[Validator]:
    return [
        PolicyKeywordCheck(on_fail="noop"),
        MinReferencesCheck(on_fail="noop"),
        GroundingCheck(on_fail="noop"),
    ]


@lru_cache(maxsize=1)
def _pii_guard() -> Guard | None:
    if not settings.get("guardrails", "hub_pii_enabled", default=False):
        return None
    try:
        from guardrails.hub import DetectPII

        return Guard().use(
            DetectPII(
                ["EMAIL_ADDRESS", "PHONE_NUMBER"],
                on_fail=settings.get("guardrails", "hub_pii_on_fail", default="fix"),
            )
        )
    except ImportError:
        logger.warning(
            "guardrails.hub.DetectPII not installed — run: "
            "guardrails hub install hub://guardrails/detect_pii"
        )
        return None


def validate_draft(
    draft: str,
    *,
    ticket_text: str,
    evidence: str,
    num_refs: int,
) -> GuardrailOutcome:
    """Run guardrails-ai validators on the draft (sequential, all reasons collected)."""
    meta = {
        "ticket_text": ticket_text,
        "evidence": evidence,
        "num_refs": num_refs,
        "min_refs": settings.get("guardrails", "min_references", default=1),
        "escalate_keywords": settings.get("guardrails", "always_escalate_keywords", default=[]),
        "min_grounding_score": settings.get("guardrails", "min_grounding_score", default=0.6),
    }

    reasons: list[str] = []
    validated = draft

    for validator in _support_validators():
        result = validator.validate(validated, metadata=meta)
        if isinstance(result, FailResult):
            reasons.append(result.error_message or validator.__class__.__name__)

    pii_guard = _pii_guard()
    if pii_guard is not None and not reasons:
        try:
            outcome = pii_guard.validate(validated, metadata=meta)
            if outcome.validated_output is not None:
                validated = outcome.validated_output
        except Exception as exc:
            reasons.append(str(exc))

    grounding_score = float(_last_grounding.get("grounding_score", 0.0) or 0.0)
    unsupported = list(_last_grounding.get("unsupported_claims", []) or [])
    decision = "proceed" if not reasons else "escalate"

    return GuardrailOutcome(
        decision=decision,
        grounding_score=grounding_score,
        unsupported_claims=unsupported,
        escalation_reason="; ".join(reasons),
        validated_draft=validated,
    )
