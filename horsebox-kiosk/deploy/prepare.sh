#!/bin/bash
# =============================================================================
# horsebox prepare.sh — Run ONCE on Chromebook (needs internet)
# Downloads all ARM64 dependencies into deploy/bundle/ for offline Pi deploy
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE="$SCRIPT_DIR/bundle"
NODE_VERSION="20.11.1"
NODE_TARBALL="node-v${NODE_VERSION}-linux-arm64.tar.gz"
NODE_URL="https://nodejs.org/dist/v${NODE_VERSION}/${NODE_TARBALL}"
REQUIREMENTS="$SCRIPT_DIR/../requirements.txt"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
warn() { echo -e "${YELLOW}  !${NC} $*"; }
die()  { echo -e "${RED}  ✗ ERROR:${NC} $*"; exit 1; }

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Horsebox Deploy — Prepare Bundle   ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Downloads ARM64 Python wheels, Node.js, and Claude Code"
echo "  into deploy/bundle/ for fully offline Pi deployment."
echo ""

# ── Check dependencies ────────────────────────────────────────────────────────
echo "Checking tools..."
for cmd in pip3 wget openssl npm; do
    command -v "$cmd" &>/dev/null && ok "$cmd found" || die "$cmd not found — install it first"
done

# ── Create bundle structure ───────────────────────────────────────────────────
mkdir -p "$BUNDLE/wheelhouse" "$BUNDLE/npm-cache"

# ── Node.js ARM64 ─────────────────────────────────────────────────────────────
echo ""
echo "── Node.js v${NODE_VERSION} ARM64 ──"
if [ -f "$BUNDLE/$NODE_TARBALL" ]; then
    ok "Already downloaded, skipping."
else
    echo "  Downloading..."
    wget -q --show-progress -O "$BUNDLE/$NODE_TARBALL" "$NODE_URL"
    ok "Downloaded $NODE_TARBALL"
fi

# ── Python ARM64 wheels ────────────────────────────────────────────────────────
echo ""
echo "── Python packages (ARM64 wheels) ──"
echo "  Downloading from PyPI for linux/aarch64 / Python 3.11..."
pip3 download \
    --platform manylinux_2_17_aarch64 \
    --python-version 311 \
    --implementation cp \
    --only-binary :all: \
    -r "$REQUIREMENTS" \
    -d "$BUNDLE/wheelhouse/" \
    -q
WHEEL_COUNT=$(ls "$BUNDLE/wheelhouse/" | wc -l)
ok "$WHEEL_COUNT wheel files downloaded"

# ── Claude Code (npm, offline cache) ──────────────────────────────────────────
echo ""
echo "── Claude Code (npm cache) ──"
echo "  Populating npm cache with @anthropic-ai/claude-code and all dependencies..."
echo "  (This installs to a temp dir just to populate the cache — nothing permanent)"
TMP_CC="$(mktemp -d)"
npm install \
    --prefix "$TMP_CC" \
    --cache "$BUNDLE/npm-cache" \
    @anthropic-ai/claude-code \
    --no-audit \
    --no-fund \
    --loglevel error
rm -rf "$TMP_CC"
ok "npm cache populated"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════╗"
echo "║  Bundle ready                                    ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
echo "  Location : $BUNDLE"
echo "  Node.js  : $NODE_TARBALL"
WHEEL_COUNT=$(ls "$BUNDLE/wheelhouse/" | wc -l)
echo "  Wheels   : $WHEEL_COUNT packages"
NM_SIZE=$(du -sh "$BUNDLE/npm-cache" 2>/dev/null | cut -f1)
echo "  npm cache: $NM_SIZE"
echo ""
echo "  Run deploy.sh for each horsebox unit."
echo ""
