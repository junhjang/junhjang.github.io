#!/usr/bin/env python3
"""Render one post/draft into a single self-contained HTML for private preview.

Usage:
  python3 scripts/make-preview.py <content-path> [--gist]

  <content-path>  path under content/ (no leading/trailing slash), e.g.
                  drafts-ko/designing-a-trading-engine
  --gist          upload the result as a FRESH secret gist (new hash every run)
                  and print the gistpreview.github.io URL + the delete command

The output HTML inlines every local CSS/JS/image and sets
<meta name="referrer" content="no-referrer">, so opening it leaks nothing via
Referer headers. Only GitHub (which hosts the gist) ever sees the URL.

Delete a preview gist when done:  gh gist delete <id>
"""
import sys, re, base64, subprocess, mimetypes
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent      # blog/
BUILD = ROOT / "public-preview"                    # throwaway build dir
OUTDIR = ROOT / "preview"                          # generated HTML (gitignored)


def sh(*args):
    return subprocess.run(args, cwd=ROOT, check=True, capture_output=True, text=True)


def local_file(url):
    """Map a root-relative URL ('/assets/..') to a file in BUILD, else None."""
    if not url.startswith("/"):
        return None
    p = BUILD / url.lstrip("/").split("?")[0].split("#")[0]
    return p if p.is_file() else None


def inline(html):
    def link_repl(m):
        tag = m.group(0)
        if "stylesheet" not in tag:
            return tag
        href = re.search(r'href="([^"]+)"', tag)
        f = local_file(href.group(1)) if href else None
        return f"<style>\n{f.read_text(encoding='utf-8')}\n</style>" if f else tag

    html = re.sub(r"<link\b[^>]*>", link_repl, html)

    def script_repl(m):
        f = local_file(m.group(1))
        return f"<script>\n{f.read_text(encoding='utf-8')}\n</script>" if f else m.group(0)

    html = re.sub(r'<script\b[^>]*\bsrc="([^"]+)"[^>]*>\s*</script>', script_repl, html)

    def img_repl(m):
        src = m.group(1)
        f = local_file(src)
        if not f:
            return m.group(0)
        mime = mimetypes.guess_type(str(f))[0] or "application/octet-stream"
        data = base64.b64encode(f.read_bytes()).decode()
        return m.group(0).replace(src, f"data:{mime};base64,{data}")

    html = re.sub(r'<img\b[^>]*\bsrc="([^"]+)"[^>]*>', img_repl, html)

    return html.replace(
        "<head>", '<head>\n<meta name="referrer" content="no-referrer">', 1
    )


def main():
    args = sys.argv[1:]
    if not args or args[0].startswith("-"):
        sys.exit("usage: make-preview.py <content-path> [--gist]")
    gist = "--gist" in args
    cpath = args[0].strip("/")

    print(f"building site -> {BUILD.name}/ ...")
    sh("hugo", "--baseURL", "/", "--destination", str(BUILD), "--cleanDestinationDir")

    page = BUILD / cpath / "index.html"
    if not page.is_file():
        sys.exit(f"built page not found: {page}\n(check the content path)")

    OUTDIR.mkdir(exist_ok=True)
    out = OUTDIR / (cpath.replace("/", "-") + ".html")
    out.write_text(inline(page.read_text(encoding="utf-8")), encoding="utf-8")
    print(f"wrote {out.relative_to(ROOT)}  ({out.stat().st_size / 1024:.0f} KB)")

    if gist:
        url = sh("gh", "gist", "create", str(out)).stdout.strip().splitlines()[-1]
        gid = url.rstrip("/").split("/")[-1]
        print()
        print(f"  PREVIEW URL : https://gistpreview.github.io/?{gid}")
        print(f"  delete with : gh gist delete {gid} --yes")


if __name__ == "__main__":
    main()
