from __future__ import annotations

import json
from pathlib import Path
from typing import Dict


class LocalizationService:
    def __init__(self, default_lang: str, supported_languages: list[str]) -> None:
        self.default_lang = default_lang
        self.supported = set(supported_languages)
        self._catalog: Dict[str, Dict[str, str]] = {}

    def load(self, base_dir: Path) -> None:
        for lang in self.supported:
            fp = base_dir / f"{lang}.json"
            if fp.exists():
                self._catalog[lang] = json.loads(fp.read_text(encoding="utf-8"))

    def t(self, key: str, language: str | None = None) -> str:
        lang = language if language in self.supported else self.default_lang
        return self._catalog.get(lang, {}).get(key, key)
