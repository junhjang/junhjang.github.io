#!/usr/bin/env bash
# Private preview: a Cloudflare quick tunnel in front of `hugo server`.
#
# Prints a random https://<words>.trycloudflare.com URL you can open on any
# device (phone included). Drafts under content/drafts-ko/ are served too.
#
# The URL is generated fresh by cloudflared on every run and is never stored
# in this script or committed anywhere — reading this file reveals no URL.
#
# Usage:  ./scripts/preview-tunnel.sh
# Stop:   Ctrl+C   (kills the tunnel and hugo server; the URL dies instantly)

set -euo pipefail
cd "$(dirname "$0")/.."

PORT=1313
TUNNEL_LOG="$(mktemp -t preview-tunnel.XXXXXX)"
HUGO_LOG="$(mktemp -t preview-hugo.XXXXXX)"

cleanup() {
  echo
  echo "stopping preview (URL is now dead)..."
  [[ -n "${TUNNEL_PID:-}" ]] && kill "$TUNNEL_PID" 2>/dev/null || true
  [[ -n "${HUGO_PID:-}"   ]] && kill "$HUGO_PID"   2>/dev/null || true
  rm -f "$TUNNEL_LOG" "$HUGO_LOG"
}
trap cleanup EXIT INT TERM

# stop any leftover preview processes so this is safe to re-run
pkill -f "hugo server"               2>/dev/null || true
pkill -f "cloudflared tunnel --url"  2>/dev/null || true
sleep 1

echo "starting cloudflare tunnel..."
cloudflared tunnel --url "http://localhost:$PORT" >"$TUNNEL_LOG" 2>&1 &
TUNNEL_PID=$!

# wait for cloudflared to print the tunnel URL
URL=""
for _ in $(seq 1 30); do
  URL="$(grep -oE 'https://[a-z0-9-]+\.trycloudflare\.com' "$TUNNEL_LOG" | head -1 || true)"
  [[ -n "$URL" ]] && break
  sleep 1
done
if [[ -z "$URL" ]]; then
  echo "ERROR: tunnel URL not found. cloudflared output:" >&2
  cat "$TUNNEL_LOG" >&2
  exit 1
fi

# hugo server must know the public URL, or internal links point to localhost
echo "starting hugo server (baseURL = $URL)..."
hugo server \
  --bind 127.0.0.1 --port "$PORT" \
  --baseURL "$URL" --appendPort=false \
  --disableLiveReload --disableFastRender >"$HUGO_LOG" 2>&1 &
HUGO_PID=$!
sleep 3
if ! kill -0 "$HUGO_PID" 2>/dev/null; then
  echo "ERROR: hugo server failed to start:" >&2
  cat "$HUGO_LOG" >&2
  exit 1
fi

echo
echo "  ────────────────────────────────────────────────────"
echo "  PREVIEW    :  $URL/"
echo "  draft list :  $URL/drafts-ko/"
echo "  ────────────────────────────────────────────────────"
echo "  Open on your phone. Edit drafts, then refresh the page."
echo "  Ctrl+C here to stop — the URL dies instantly."
echo

wait "$TUNNEL_PID"
