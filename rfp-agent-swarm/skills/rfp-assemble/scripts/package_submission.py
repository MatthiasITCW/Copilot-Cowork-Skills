#!/usr/bin/env python3
"""
package_submission.py
---------------------

Package the assembled deliverable, cover letter, analytics report, and any
additional attachments into a single zip for submission.

CLI:
    python scripts/package_submission.py \\
        --assembled working/assembled.docx \\
        --cover-letter working/cover_letter.pdf \\
        --analytics working/analytics_report.docx \\
        --attachments "working/attachments/*.pdf" \\
        --output output/submission_package.zip \\
        [--sidecar-manifest working/portal_manifest.json]

Behaviour:
    * Validates every specified file exists
    * Emits a manifest.json inside the zip listing every file and checksum
    * Exits non-zero if any required file is missing

Exit codes:
    0  package written
    2  missing required file
    3  attachment glob expanded to nothing but was provided
    4  output directory not writeable
"""

from __future__ import annotations

import argparse
import datetime
import glob
import hashlib
import json
import os
import sys
import zipfile
from typing import List


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Package RFP submission zip.")
    p.add_argument("--assembled", required=True)
    p.add_argument("--cover-letter", required=True)
    p.add_argument("--analytics", required=True)
    p.add_argument("--attachments", required=False, default="",
                   help="Glob pattern for attachments (optional)")
    p.add_argument("--sidecar-manifest", required=False, default="")
    p.add_argument("--output", required=True)
    return p.parse_args()


def fail(code: int, msg: str) -> None:
    sys.stderr.write("ERROR: " + msg + "\n")
    sys.exit(code)


def require_file(path: str, label: str) -> None:
    if not os.path.exists(path):
        fail(2, "missing required file ({0}): {1}".format(label, path))
    if not os.path.isfile(path):
        fail(2, "path is not a file ({0}): {1}".format(label, path))


def sha256_of(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            block = fh.read(65536)
            if not block:
                break
            h.update(block)
    return h.hexdigest()


def expand_attachments(pattern: str) -> List[str]:
    if not pattern:
        return []
    matches = sorted(glob.glob(pattern))
    if not matches:
        fail(3, "attachments pattern '{0}' matched nothing".format(pattern))
    for m in matches:
        if not os.path.isfile(m):
            fail(2, "attachment is not a file: {0}".format(m))
    return matches


def build_manifest_entries(paths_with_labels: List[tuple]) -> List[dict]:
    entries = []
    for path, label, arcname in paths_with_labels:
        entries.append({
            "label": label,
            "arcname": arcname,
            "size_bytes": os.path.getsize(path),
            "sha256": sha256_of(path),
        })
    return entries


def main() -> int:
    args = parse_args()

    require_file(args.assembled, "assembled deliverable")
    require_file(args.cover_letter, "cover letter")
    require_file(args.analytics, "analytics report")

    attachments = expand_attachments(args.attachments)

    sidecar = args.sidecar_manifest
    if sidecar:
        require_file(sidecar, "sidecar manifest")

    out_dir = os.path.dirname(args.output) or "."
    if not os.path.exists(out_dir):
        try:
            os.makedirs(out_dir, exist_ok=True)
        except OSError as exc:
            fail(4, "output directory not creatable: {0}".format(exc))

    # Build the list of files to add (path, label, arcname)
    entries = [
        (args.assembled, "deliverable",
         "deliverable/" + os.path.basename(args.assembled)),
        (args.cover_letter, "cover_letter",
         "cover_letter/" + os.path.basename(args.cover_letter)),
        (args.analytics, "analytics_report",
         "analytics/" + os.path.basename(args.analytics)),
    ]
    for a in attachments:
        entries.append((a, "attachment", "attachments/" + os.path.basename(a)))
    if sidecar:
        entries.append((sidecar, "sidecar_manifest",
                        "provenance/" + os.path.basename(sidecar)))

    manifest = {
        "schema_version": "1.0",
        "packaged_at": datetime.datetime.utcnow().isoformat() + "Z",
        "file_count": len(entries) + 1,  # +1 for manifest itself
        "files": build_manifest_entries(entries),
    }

    # Write the zip
    try:
        with zipfile.ZipFile(
            args.output, "w", compression=zipfile.ZIP_DEFLATED
        ) as zf:
            for path, _label, arcname in entries:
                zf.write(path, arcname=arcname)
            zf.writestr(
                "manifest.json",
                json.dumps(manifest, indent=2).encode("utf-8"),
            )
    except OSError as exc:
        fail(4, "could not write zip: {0}".format(exc))

    size = os.path.getsize(args.output)
    sys.stderr.write(
        "OK: packaged {0} files into {1} ({2} bytes)\n".format(
            len(entries) + 1, args.output, size
        )
    )
    # Emit a short JSON receipt to stdout so the caller can parse it
    receipt = {
        "output": args.output,
        "size_bytes": size,
        "sha256": sha256_of(args.output),
        "file_count": len(entries) + 1,
    }
    sys.stdout.write(json.dumps(receipt, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
