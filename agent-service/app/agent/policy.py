"""Deployment-specific answer boundaries without embedding a customer's rules."""

from __future__ import annotations

import os

from .language import response_language


def policy_rules() -> str:
    return os.getenv("AGENT_SCOPE_POLICY", "").strip()


def advice_rules() -> str:
    return os.getenv("AGENT_ADVICE_POLICY", "").strip()


def disclaimer(language: str) -> str:
    key = "AGENT_DISCLAIMER_EN" if language == "en" else "AGENT_DISCLAIMER_ES"
    default = (
        "General information only. Consult a qualified professional before making a decision."
        if language == "en" else
        "Información general. Consulta a un profesional competente antes de tomar una decisión."
    )
    return os.getenv(key, default).strip() or default


def disclaimer_for(question: str, preference: str | None = None) -> str:
    return disclaimer(response_language(question, preference))


def refusal(decision: str, language: str) -> str:
    if decision == "REJECT_ADVICE":
        key = "AGENT_ADVICE_REFUSAL_EN" if language == "en" else "AGENT_ADVICE_REFUSAL_ES"
        default = ("I can explain the available sources, but I can't make a personalized decision for you."
                   if language == "en" else
                   "Puedo explicar las fuentes disponibles, pero no tomar una decisión personalizada por ti.")
    else:
        key = "AGENT_SCOPE_REFUSAL_EN" if language == "en" else "AGENT_SCOPE_REFUSAL_ES"
        default = ("I can help with the subjects covered by this assistant's sources."
                   if language == "en" else
                   "Puedo ayudarte con los temas cubiertos por las fuentes de este asistente.")
    return os.getenv(key, default).strip()
