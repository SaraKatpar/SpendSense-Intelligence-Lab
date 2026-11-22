"""Fail closed for legacy CSV training paths: only reviewed real source hashes."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require_real_csv(path):
    path = Path(path).resolve()
    manifest = json.loads((ROOT/'eval/spending_mix_v1/approved_training_sources.json').read_text(encoding='utf-8'))
    for name, digest in manifest.items():
        if path == (ROOT/name).resolve() and hashlib.sha256(path.read_bytes()).hexdigest() == digest:
            return path
    raise ValueError('Training input is not an approved, hash-verified real reference CSV. No generated/demo fixtures permitted.')
