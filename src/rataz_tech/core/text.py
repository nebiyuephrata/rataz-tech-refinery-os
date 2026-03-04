from __future__ import annotations

import re
from typing import List


WORD_RE = re.compile(r"\w+", re.UNICODE)


def tokenize(text: str) -> List[str]:
    return [m.group(0).lower() for m in WORD_RE.finditer(text)]
