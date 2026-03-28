"""Pronunciation replacements for TTS preprocessing.

Maps abbreviations and terms to their spoken forms for Russian narration.
Applied to narration text before sending to ElevenLabs TTS.

Usage:
    from lecturer.pronunciation import apply_pronunciation
    text = apply_pronunciation(text)
"""

import re

# Replacements applied in order. Each tuple: (pattern, replacement).
# Patterns are compiled as case-sensitive regex.
REPLACEMENTS: list[tuple[str, str]] = [
    # Compound forms with ИИ- → эй-ай (must come before standalone ИИ)
    (r"ИИ-агент", "эй-ай агент"),
    (r"ИИ-инструмент", "эй-ай инструмент"),
    (r"ИИ-клиент", "эй-ай клиент"),
    (r"ИИ-систем", "эй-ай систем"),

    # Standalone ИИ with Russian case endings
    (r"\bИИ\b", "искусственный интеллект"),

    # Latin abbreviations
    (r"\bLLM\b", "эл-эл-эм"),
    (r"\bA2A\b", "эй-ту-эй"),
    (r"\bCLI\b", "си-эл-ай"),
    (r"\bRAG\b", "рэг"),
]

# Compiled patterns (lazy init)
_compiled: list[tuple[re.Pattern, str]] | None = None


def _compile() -> list[tuple[re.Pattern, str]]:
    global _compiled
    if _compiled is None:
        _compiled = [(re.compile(pat), repl) for pat, repl in REPLACEMENTS]
    return _compiled


def apply_pronunciation(text: str) -> str:
    """Apply pronunciation replacements to narration text."""
    for pattern, replacement in _compile():
        text = pattern.sub(replacement, text)
    return text
