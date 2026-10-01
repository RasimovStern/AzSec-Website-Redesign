#!/usr/bin/env python3
"""
Strip the page skeleton from index.html.

Some hosts — a Claude Artifact, a CMS block, anything that supplies its own
<!doctype>/<head>/<body> — want the page's contents without the wrapper. This
writes that variant to dist/artifact.html and leaves index.html alone.

The <style> block moves out of <head> with the rest; browsers hoist a <style>
found in the body, so the result still renders correctly wherever it lands.

    python3 tools/build-artifact.py
"""

import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "index.html"
OUT = ROOT / "dist" / "artifact.html"


def main() -> int:
    if not SRC.exists():
        print(f"not found: {SRC}", file=sys.stderr)
        return 1

    html = SRC.read_text(encoding="utf-8")

    head_match = re.search(r"<head\b[^>]*>(.*?)</head>", html, re.S | re.I)
    body_match = re.search(r"<body\b[^>]*>(.*?)</body>", html, re.S | re.I)
    if not head_match or not body_match:
        print("index.html does not look like a full document", file=sys.stderr)
        return 1

    # Everything the host will not provide for us: the title and the stylesheet.
    keep = []
    title = re.search(r"<title>.*?</title>", head_match.group(1), re.S | re.I)
    if title:
        keep.append(title.group(0))
    keep += re.findall(r"<style\b[^>]*>.*?</style>", head_match.group(1), re.S | re.I)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(keep) + "\n" + body_match.group(1).strip() + "\n",
                   encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
