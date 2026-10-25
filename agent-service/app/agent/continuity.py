"""Resolve conversational references before source retrieval.

Previous turns may help find evidence, but never substitute for it.
"""

from __future__ import annotations

import re
from typing import Any

from .language import response_language


_REFERENCE = re.compile(
    r"\b(?:"
    r"(?:can|could|would) you (?:expand|elaborate)(?: on (?:that|what you (?:just )?said))?"
    r"|tell me more(?: about (?:that|it))?"
    r"|what (?:did|do) you (?:just )?say"
    r"|what (?:do|did) you mean(?: by that)?"
    r"|what about (?:that|it|those)"
    r"|(?:does|is|can|why|how) that\b"
    r"|previous (?:answer|point)"
    r"|(?:puedes|podrías) (?:ampliar|explicar más|profundizar)(?: (?:eso|lo anterior))?"
    r"|(?:qué|que) (?:quisiste decir|hay de eso)"
    r"|(?:a qué|a que) te refieres"
    r"|(?:y|sobre) (?:eso|lo anterior)"
    r")\b",
    re.IGNORECASE,
)


def refers_to_previous_turn(question: str) -> bool:
    return bool(_REFERENCE.search(question))


def search_question(question: str, history: list[dict[str, Any]]) -> str:
    """Add the last standalone user question to a dependent follow-up search."""
    if not refers_to_previous_turn(question):
        return question
    for message in reversed(history):
        if message.get("role") != "user":
            continue
        previous = str(message.get("content", "")).strip()
        if previous and not refers_to_previous_turn(previous):
            return previous[:500]
    return question


def missing_context_reply(question: str, preference: str | None = None, *, memory_enabled: bool = False) -> str:
    if response_language(question, preference) == "en":
        return (
            "I don't have an earlier exchange to refer to yet. What would you like me to expand on?"
            if memory_enabled else
            "I can't see the earlier exchange with conversation memory off. What would you like me to expand on?"
        )
    return (
        "Todavía no tengo un intercambio anterior al que referirme. ¿Qué tema quieres que amplíe?"
        if memory_enabled else
        "Con la memoria desactivada no puedo ver el intercambio anterior. ¿Qué tema quieres que amplíe?"
    )


def unsupported_followup_reply(question: str, preference: str | None = None) -> str:
    asks_why = bool(re.search(r"\bwhy\b|\bpor qu[eé]\b", question, re.IGNORECASE))
    if response_language(question, preference) == "en":
        if asks_why:
            return "The source confirms the rule we discussed, but it doesn't explain why. I don't want to guess at the rationale."
        return "I can follow the conversation, but I can't verify more from the available sources. Which part would you like to explore?"
    if asks_why:
        return "La fuente confirma la regla que comentamos, pero no explica el motivo. No quiero inventar una justificación."
    return "Puedo seguir la conversación, pero no encuentro respaldo para ampliar esa parte. ¿Qué aspecto te interesa revisar?"
