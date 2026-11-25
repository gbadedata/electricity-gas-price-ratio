"""Download every source into data/raw/ and record its provenance.

The raw files are committed to the repository, so every published number can
be traced back to the exact bytes it was computed from. The manifest records
the URL, retrieval time, HTTP headers that identify the release, byte count
and SHA-256 of each file.

A fetch either succeeds for every source or leaves the previous snapshot in
place: files are downloaded to a temporary folder and only moved into
data/raw/ once all of them have passed basic checks.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .paths import MANIFEST, RAW
from .sources import GOVUK_CONTENT, SOURCES, Source

USER_AGENT = "electricity-gas-price-ratio/1.0 (+https://github.com/gbadedata/electricity-gas-price-ratio)"
TIMEOUT = 120


def _session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=2,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        respect_retry_after_header=True,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    s.headers["User-Agent"] = USER_AGENT
    return s


def resolve_govuk_attachment(session: requests.Session, source: Source) -> tuple[str, dict]:
    """Find the current download URL for a DESNZ table via the GOV.UK content API."""
    r = session.get(f"{GOVUK_CONTENT}{source.govuk_path}", timeout=TIMEOUT)
    r.raise_for_status()
    page = r.json()
    matches = [
        a for a in page.get("details", {}).get("attachments", [])
        if all(t.lower() in a.get("title", "").lower() for t in source.attachment_title_contains)
    ]
    if len(matches) != 1:
        titles = [a.get("title") for a in page.get("details", {}).get("attachments", [])]
        raise RuntimeError(
            f"{source.id}: expected exactly one attachment matching "
            f"{source.attachment_title_contains}, found {len(matches)}. Titles: {titles}"
        )
    att = matches[0]
    return att["url"], {
        "govuk_page": f"https://www.gov.uk{source.govuk_path}",
        "govuk_page_public_updated_at": page.get("public_updated_at"),
        "attachment_title": att.get("title"),
    }


def _check_payload(source: Source, body: bytes) -> None:
    """Reject payloads that are clearly not the data (error pages, SOAP faults)."""
    if len(body) < 1000:
        raise RuntimeError(f"{source.id}: payload only {len(body)} bytes: {body[:300]!r}")
    if source.filename.endswith(".csv"):
        head = body[:300].decode("utf-8", errors="replace")
        if head.lstrip().startswith("<"):
            raise RuntimeError(f"{source.id}: expected CSV, got markup: {head!r}")
        expected = "DATAFLOW" if source.id.startswith("eurostat") else "KEY"
        if not head.startswith(expected):
            raise RuntimeError(f"{source.id}: unexpected CSV header: {head[:120]!r}")
    if source.filename.endswith(".xlsx") and not body.startswith(b"PK"):
        raise RuntimeError(f"{source.id}: expected an .xlsx (zip) file")


def fetch_all(raw_dir: Path = RAW, manifest_path: Path = MANIFEST) -> dict:
    session = _session()
    run_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    entries = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        for source in SOURCES:
            extra: dict = {}
            url = source.url
            if source.kind == "govuk_attachment":
                url, extra = resolve_govuk_attachment(session, source)
            t0 = time.monotonic()
            r = session.get(url, timeout=TIMEOUT)
            r.raise_for_status()
            body = r.content
            _check_payload(source, body)
            (tmp_dir / source.filename).write_bytes(body)
            entries.append({
                "id": source.id,
                "publisher": source.publisher,
                "title": source.title,
                "licence": source.licence,
                "url": url,
                "file": f"data/raw/{source.filename}",
                "retrieved_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "http_status": r.status_code,
                "content_type": r.headers.get("Content-Type"),
                "last_modified": r.headers.get("Last-Modified"),
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
                "seconds": round(time.monotonic() - t0, 2),
                **extra,
            })
            print(f"fetched {source.id}: {len(body):,} bytes", file=sys.stderr)

        # All sources fetched and checked: publish the snapshot.
        raw_dir.mkdir(parents=True, exist_ok=True)
        for source in SOURCES:
            shutil.move(str(tmp_dir / source.filename), raw_dir / source.filename)

    manifest = {"fetched_at": run_at, "sources": entries}
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_manifest(raw_dir: Path = RAW, manifest_path: Path = MANIFEST) -> list[str]:
    """Return a list of problems; empty means every raw file matches its recorded hash."""
    problems = []
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for e in manifest["sources"]:
        p = raw_dir / Path(e["file"]).name
        if not p.exists():
            problems.append(f"{e['id']}: missing {p}")
            continue
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        if digest != e["sha256"]:
            problems.append(f"{e['id']}: sha256 mismatch ({digest} != {e['sha256']})")
    return problems
