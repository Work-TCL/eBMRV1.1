import hashlib
import json
from typing import Any


def canonical_json(value: Any) -> str:
    """Deterministic JSON serialization used everywhere we need a stable hash (record hashes, event
    hashes, command payload hashes). Sort keys, no whitespace ambiguity, ISO strings for anything
    already stringified by the caller.
    """
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def sha256_hex(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
