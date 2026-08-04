"""
i18n.py — lightweight translation layer for static bot UI text.

Design:
- Static strings (menus, buttons, disclaimers, error messages) live in
  locales/<code>.json and are looked up with t(key, lang).  These are
  human-written/reviewed, not machine-translated at runtime, so they stay
  fast and reliable even if an AI provider is down.
- Dynamic content (AI chat/recommendations from groq_service.py) is instead
  steered at generation time via language_instruction(lang), which appends
  a "respond in <language>" directive to the prompt sent to the model. See
  groq_service.py for usage.

Adding a language:
1. Copy locales/en.json to locales/<code>.json and translate the values.
2. Add the code + native display name to SUPPORTED_LANGUAGES below.
That's it — the /language picker and t() pick it up automatically.

Note: only the strings above are covered by static locale files so far.
Rolling this out to every handler's text is a larger, incremental job —
this module is meant to make that mechanical (import t, replace the
hardcoded string, add the key to each locale file).
"""

import json
import os
import logging

logger = logging.getLogger(__name__)

LOCALES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "locales")

DEFAULT_LANGUAGE = "en"

# code -> native display name (shown in the /language picker)
SUPPORTED_LANGUAGES = {
    "en": "English",
    "fr": "Français",
    "it": "Italiano",
    "ru": "Русский",
    "pt": "Português",
    "es": "Español",
    "ar": "العربية",
    "de": "Deutsch",
    "sw": "Kiswahili",
    "ja": "日本語",
}

# Language name to feed the LLM for dynamic translation (English name reads
# more reliably as a model instruction than the native name in every case).
LLM_LANGUAGE_NAME = {
    "en": "English",
    "fr": "French",
    "it": "Italian",
    "ru": "Russian",
    "pt": "Portuguese",
    "es": "Spanish",
    "ar": "Arabic",
    "de": "German",
    "sw": "Swahili",
    "ja": "Japanese",
}

_locales_cache = {}


def _load_locale(lang: str) -> dict:
    if lang in _locales_cache:
        return _locales_cache[lang]

    path = os.path.join(LOCALES_DIR, f"{lang}.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.warning(f"[i18n] No locale file for '{lang}', falling back to {DEFAULT_LANGUAGE}")
        if lang == DEFAULT_LANGUAGE:
            data = {}
        else:
            data = _load_locale(DEFAULT_LANGUAGE)
    except Exception as e:
        logger.error(f"[i18n] Failed to load locale '{lang}': {e}")
        data = {}

    _locales_cache[lang] = data
    return data


def t(key: str, lang: str = DEFAULT_LANGUAGE, **kwargs) -> str:
    """
    Look up a static UI string by key for the given language, falling back
    to English and then to the raw key if nothing is found. Any kwargs are
    used to .format() the string (e.g. t("welcome_default", lang, name="Rin")).
    """
    lang = lang if lang in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE
    locale = _load_locale(lang)

    text = locale.get(key)
    if text is None and lang != DEFAULT_LANGUAGE:
        text = _load_locale(DEFAULT_LANGUAGE).get(key)
    if text is None:
        logger.warning(f"[i18n] Missing key '{key}' in all locales")
        return key

    try:
        return text.format(**kwargs)
    except (KeyError, IndexError) as e:
        logger.error(f"[i18n] Format error for key '{key}' ({lang}): {e}")
        return text


def language_instruction(lang: str) -> str:
    """
    A short directive to append to LLM prompts so dynamically generated
    content (AI chat, recommendations, etc.) comes back in the user's
    chosen language. No-op (empty string) for English, since prompts are
    already written in English.
    """
    if lang == "en" or lang not in LLM_LANGUAGE_NAME:
        return ""
    return f"\n\nRespond only in {LLM_LANGUAGE_NAME[lang]}, regardless of what language this prompt is written in."
