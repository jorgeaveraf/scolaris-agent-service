"""Choose a response language from the current question, with a UI fallback."""

from __future__ import annotations

import os
import re
import unicodedata

_SPANISH = {"qué", "que", "cómo", "como", "cuál", "cual", "cuáles", "dónde", "cuando", "por", "para", "con", "del", "una", "un", "los", "las", "puedo", "explica", "gracias", "hola", "sobre", "según", "segun", "fuente", "fuentes"}
_ENGLISH = {"what", "whats", "who", "how", "which", "where", "when", "why", "the", "this", "that", "does", "can", "could", "please", "explain", "according", "source", "sources", "thanks", "hello", "hi", "hey", "about", "with", "benefits", "members", "team"}


def _social_key(question: str) -> str:
    normalized = unicodedata.normalize("NFKD", question.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", normalized))


_SOCIAL_REPLIES = {
    "can you help me": ("en", "help"),
    "could you help me": ("en", "help"),
    "thanks": ("en", "thanks"),
    "thank you": ("en", "thanks"),
    "bye": ("en", "bye"),
    "goodbye": ("en", "bye"),
    "oye puedes ayudarme": ("es", "help"),
    "puedes ayudarme": ("es", "help"),
    "me puedes ayudar": ("es", "help"),
    "gracias": ("es", "thanks"),
    "muchas gracias": ("es", "thanks"),
    "adios": ("es", "bye"),
    "hasta luego": ("es", "bye"),
}

_EN_GREETING = re.compile(
    r"(?P<greeting>hi|hello|hey|good morning|good afternoon|good evening)"
    r"(?: there| everyone)?(?P<help> can you help me| could you help me)?"
)
_ES_GREETING = re.compile(
    r"(?P<greeting>hola|buenas|buenos dias|buenas tardes|buenas noches|que tal)"
    r"(?: a todos)?(?P<help> puedes ayudarme| me puedes ayudar| me ayudas)?"
)
_CASUAL_GREETING_TEXT = {
    "how are you": "I'm here and ready to help. What's on your mind?",
    "how s it going": "I'm here and ready to help. What's on your mind?",
    "what s up": "Hey! What's on your mind?",
    "what is up": "Hey! What's on your mind?",
    "howdy": "Howdy! What would you like to know?",
    "hiya": "Hi! What would you like to know?",
    "que onda": "¡Qué onda! ¿En qué te ayudo?",
    "hola que onda": "¡Hola! ¿En qué te ayudo?",
    "como estas": "Aquí para ayudarte. ¿Qué te gustaría consultar?",
    "hola como estas": "¡Hola! Aquí para ayudarte. ¿Qué te gustaría consultar?",
    "buen dia": "¡Buen día! ¿Qué te gustaría consultar?",
}

_GREETING_TEXT = {
    "en": {
        "hi": "Hi! What would you like to know?",
        "hello": "Hello! What would you like to know?",
        "hey": "Hey! What would you like to know?",
        "good morning": "Good morning! What would you like to know?",
        "good afternoon": "Good afternoon! What would you like to know?",
        "good evening": "Good evening! What would you like to know?",
    },
    "es": {
        "hola": "¡Hola! ¿Qué te gustaría consultar?",
        "buenas": "¡Hola! ¿Qué te gustaría consultar?",
        "buenos dias": "¡Buenos días! ¿Qué te gustaría consultar?",
        "buenas tardes": "¡Buenas tardes! ¿Qué te gustaría consultar?",
        "buenas noches": "¡Buenas noches! ¿Qué te gustaría consultar?",
        "que tal": "¡Hola! ¿Qué te gustaría consultar?",
    },
}

_SOCIAL_TEXT = {
    "en": {
        "help": "Sure. Tell me what you need help with.",
        "thanks": "You're welcome. What else can I help you with?",
        "bye": "Goodbye!",
    },
    "es": {
        "help": "Sí, claro. Cuéntame qué necesitas.",
        "thanks": "Con gusto. ¿En qué más puedo ayudarte?",
        "bye": "¡Hasta luego!",
    },
}


def conversational_reply(question: str, preference: str | None = None) -> str | None:
    """Answer only complete, harmless social turns without consulting sources."""
    if len(question) > 120:
        return None
    key = _social_key(question)
    casual_greeting = _CASUAL_GREETING_TEXT.get(key)
    if casual_greeting is not None:
        return casual_greeting
    match = _SOCIAL_REPLIES.get(key)
    if match is None:
        for language, pattern in (("en", _EN_GREETING), ("es", _ES_GREETING)):
            greeting = pattern.fullmatch(key)
            if greeting:
                if greeting.group("help"):
                    return _SOCIAL_TEXT[language]["help"]
                return _GREETING_TEXT[language][greeting.group("greeting")]
    if match is None:
        return None
    language, intent = match
    return _SOCIAL_TEXT[language][intent]


def response_language(question: str, preference: str | None = None) -> str:
    words = re.findall(r"[\wáéíóúüñ]+", question.lower(), flags=re.UNICODE)
    spanish = sum(word in _SPANISH for word in words) + sum(char in question.lower() for char in "áéíóúüñ")
    english = sum(word in _ENGLISH for word in words)
    if spanish > english:
        return "es"
    if english > spanish:
        return "en"
    return preference if preference in {"es", "en"} else "es"


def no_source_message(language: str) -> str:
    if language == "en":
        return os.getenv("NO_SOURCE_MESSAGE_EN", "I don't have a sufficient source to answer safely.")
    return os.getenv("NO_SOURCE_MESSAGE", "No encuentro una fuente suficiente para responder con seguridad.")
