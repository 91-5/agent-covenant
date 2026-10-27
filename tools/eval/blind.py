"""Blinding: seed custody, seeded shuffling, blinded packaging, unblinding.

Frozen discipline (card XJ-20261024-001 constraint 3 + EVO-20261024-001):

* 浮香 (the adjudicator) receives products that are (a) shuffled into
  pseudonymous order and (b) stripped of every condition label -- she cannot
  know which product came from 门禁全开 vs 门禁旁路.
* The shuffle seed is generated with ``secrets`` (no predictable seed), and
  the full correspondence table exists in exactly one place: the sealed key
  file under ``.eval-sealed/`` (gitignored). ZCode hands the key file to sir
  immediately; neither ZCode nor the adjudicator retains the complete mapping.
* Products are pseudonymized end to end: P-codes replace task ids, condition
  letters, and repetition numbers. A product file name like ``T05-A-r2.md``
  is a blinding leak, so packaging rewrites names and scrubs the manifest.
* Unblinding is a separate, explicit operation (`unblind`) that requires the
  key file. The harness has no code path that reveals conditions without it.

Everything is derived from the seed, so sir can re-derive the whole mapping
from the key alone -- the key is the correspondence table, not a password.
"""
from __future__ import annotations

import json
import random
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

PACKAGE_VERSION = 1

SEALED_DIR_NAME = ".eval-sealed"

#: E-level judgements sealed at packaging time (XJ-20261027-001). Present only
#: in packages built with a ``root``; older packages fall back to re-judging.
JUDGEMENTS_FILE = "judgements-blind.json"

#: The repository state the sealed judgements were formed against.
ROOT_STATE_FILE = "root-state.json"


def file_sha256(path: Path) -> str:
    """Streaming SHA-256 of one file (never reads the whole thing into memory)."""
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def product_hashes(products_dir: Path, files: Dict[str, str]) -> Dict[str, str]:
    """SHA-256 per packaged product, keyed by P-code."""
    return {code: file_sha256(products_dir / name) for code, name in files.items()}


def root_state(root: Path) -> Dict[str, object]:
    """Snapshot enough of the repository to tell 'same tree' from 'moved on'.

    ``git_head`` plus a dirty flag, not a full worktree hash: the cheap check
    already catches the failure we measured (a merge moving HEAD), and a full
    hash would make packaging depend on hash stability across platforms.
    """
    import subprocess

    def _git(*args: str) -> str:
        try:
            done = subprocess.run(["git", "-C", str(root), *args],
                                  capture_output=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            return ""
        if done.returncode != 0:
            return ""
        return done.stdout.decode("utf-8", errors="replace").strip()

    return {
        "root": str(root),
        "git_head": _git("rev-parse", "HEAD"),
        "dirty": bool(_git("status", "--porcelain")),
        "computed_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "note": "judgements in this package were formed against this repository "
                "state; a different state means the numbers are not comparable",
    }


def generate_seed() -> str:
    """Cryptographically random seed; this is the only place randomness is
    allowed in the harness, and its output is sealed, never logged."""
    return secrets.token_hex(32)


def derive_shuffle(seed: str, items: List[str]) -> List[str]:
    """Deterministic shuffle: same seed + same items => same order (the
    re-derivation property the key file relies on)."""
    rng = random.Random(int(seed, 16))
    shuffled = list(items)
    rng.shuffle(shuffled)
    return shuffled


@dataclass
class RunEntry:
    """One product in a study run, with its (sealed) condition metadata."""

    key: str                 # runner's internal key, never leaves the seal
    task_id: str
    condition: str           # "A" | "B" -- sealed, never packaged
    repetition: int
    product_path: Path       # product markdown on disk
    coverage: Optional[bool] = None


def load_run_data(run_dir: Path) -> List[RunEntry]:
    """Read run-data.json (written by the study runner) plus its products."""
    data = json.loads((run_dir / "run-data.json").read_text(encoding="utf-8"))
    entries: List[RunEntry] = []
    for raw in data["entries"]:
        entries.append(
            RunEntry(
                key=raw["key"],
                task_id=raw["task_id"],
                condition=raw["condition"],
                repetition=int(raw["repetition"]),
                product_path=run_dir / raw["product"],
                coverage=raw.get("coverage"),
            )
        )
    return entries


def build_package(run_dir: Path, out_dir: Path, seed: str,
                  root: Optional[Path] = None,
                  timeout: Optional[int] = None) -> Tuple[Path, Path, List[Dict[str, object]]]:
    """Build the blinded adjudication package and the sealed key.

    Returns (package_dir, key_path, mapping) where mapping is the full
    correspondence (for the key file only -- it must never be echoed to
    stdout or written anywhere else).

    P-codes are assigned in *seeded shuffled* order of the runner keys, so
    package order carries no information about task/condition layout.

    **Judgements are sealed here when ``root`` is given** (XJ-20261027-001):
    every product is judged once, at packaging time, and the E-levels are
    written into ``judgements-blind.json``. ``report``/``unblind`` then read the
    sealed levels instead of re-judging against whatever the repository looks
    like later. Measured cost of the old behaviour: round 3's primary endpoint
    read -50.0% at the analysis commit and -48.3% after the next merge, because
    one task's claims quote live-git facts.

    Sealing at packaging time is also the stronger integrity story: judging
    happens before anyone can see the blind/condition mapping, so there is no
    "re-judge after the results are known" surface at all.

    ``root-state.json`` records the repository state the judgements were formed
    against, so a later mismatch can be reported instead of silently absorbed.
    """
    entries = load_run_data(run_dir)
    if not entries:
        raise ValueError(f"no run entries found in {run_dir}")
    keys = [entry.key for entry in entries]
    shuffled_keys = derive_shuffle(seed, keys)
    by_key = {entry.key: entry for entry in entries}

    package_products = out_dir / "products"
    package_products.mkdir(parents=True, exist_ok=True)

    manifest_files: Dict[str, str] = {}
    mapping: List[Dict[str, object]] = []
    claims_by_code: Dict[str, List[dict]] = {}
    metrics_by_code: Dict[str, dict] = {}

    for index, key in enumerate(shuffled_keys, start=1):
        code = f"P{index:03d}"
        entry = by_key[key]
        product_name = f"{code}.md"
        text = entry.product_path.read_text(encoding="utf-8", errors="replace")
        (package_products / product_name).write_text(text, encoding="utf-8")
        manifest_files[code] = product_name

        # Import lazily: blind stays import-light and judge/extract stay
        # free of packaging concerns.
        from extract import extract_claims  # noqa: local import by design

        claims = extract_claims(text, product=code)
        claims_by_code[code] = [claim.to_dict() for claim in claims]
        metrics_by_code[code] = {
            "claims": len(claims),
            "unanchored": sum(1 for claim in claims if claim.unanchored),
            "coverage": entry.coverage,
        }
        mapping.append(
            {
                "code": code,
                "key": key,
                "task_id": entry.task_id,
                "condition": entry.condition,
                "repetition": entry.repetition,
                "source_product": str(entry.product_path),
                "coverage": entry.coverage,
            }
        )

    manifest = {
        "package_version": PACKAGE_VERSION,
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_products": len(manifest_files),
        "products": manifest_files,
        "blinding": "products shuffled and pseudonymized; no condition, task "
                    "or repetition metadata is present in this package",
    }
    (out_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "claims.json").write_text(
        json.dumps(claims_by_code, ensure_ascii=False, indent=2), encoding="utf-8")
    (out_dir / "metrics-blind.json").write_text(
        json.dumps(metrics_by_code, ensure_ascii=False, indent=2), encoding="utf-8")

    # --- sealed judgements + root snapshot (XJ-20261027-001) -------------------
    if root is not None:
        from judge import DEFAULT_TIMEOUT_SECONDS, judge_markdown  # lazy, as above

        # Product seal (XJ-20261027-002, A1): sealed judgements describe exactly
        # these bytes, so readers must be able to prove the bytes did not change.
        # Legacy packages (no sealed judgements) re-judge from disk and need no
        # such binding -- they are consistent with disk by construction.
        manifest["product_sha256"] = product_hashes(package_products, manifest_files)
        (out_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        sealed: Dict[str, List[Dict[str, object]]] = {}
        for code in sorted(manifest_files):
            text = (package_products / manifest_files[code]).read_text(
                encoding="utf-8", errors="replace")
            judgements = judge_markdown(text, Path(root), product=code,
                                        timeout=timeout or DEFAULT_TIMEOUT_SECONDS)
            sealed[code] = [judgement.to_dict() for judgement in judgements]
        (out_dir / JUDGEMENTS_FILE).write_text(
            json.dumps(sealed, ensure_ascii=False, indent=2), encoding="utf-8")
        (out_dir / ROOT_STATE_FILE).write_text(
            json.dumps(root_state(Path(root)), ensure_ascii=False, indent=2),
            encoding="utf-8")

    key_path = out_dir.parent / f"key-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
    key_payload = {
        "seed": seed,
        "generated_utc": manifest["generated_utc"],
        "custody": "sir-only until report finalization; the seed re-derives "
                   "the full mapping, so this file IS the correspondence table",
        "mapping": mapping,
    }
    key_path.write_text(
        json.dumps(key_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return out_dir, key_path, mapping


def unblind(package_dir: Path, key_path: Path) -> List[Dict[str, object]]:
    """Sir's operation: join the package's P-codes with the sealed mapping.

    Returns the unblinded table (code -> task/condition/rep). Raises if the
    key does not match the package (wrong key = hard stop, never a guess)."""
    manifest = json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
    key_payload = json.loads(key_path.read_text(encoding="utf-8"))
    mapping = key_payload["mapping"]
    codes_in_package = set(manifest["products"])
    codes_in_key = {row["code"] for row in mapping}
    if codes_in_package != codes_in_key:
        raise ValueError(
            "key does not match package: "
            f"package has {len(codes_in_package)} codes, key has {len(codes_in_key)}"
        )
    return sorted(mapping, key=lambda row: row["code"])
