#!/bin/bash
# =============================================================================
# horsebox first_boot.sh — Runs ONCE on the Pi on first power-on
#
# Triggered by horsebox-first-boot.service
# Self-destructs after successful completion (removes .first_boot_pending)
# Safe to re-run manually if it fails partway through
# =============================================================================
set -euo pipefail

# ── Load unit config written by deploy.sh ─────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CONFIG="$SCRIPT_DIR/.deploy_config"
[ -f "$CONFIG" ] || { echo "ERROR: .deploy_config not found — was deploy.sh run?"; exit 1; }
# shellcheck source=/dev/null
source "$CONFIG"

LOG="/var/log/horsebox-first-boot.log"
BUNDLE="$SCRIPT_DIR/bundle"

# ── Logging ───────────────────────────────────────────────────────────────────
exec > >(tee -a "$LOG") 2>&1
echo ""
echo "=== Horsebox First Boot: $(date) ==="
echo "    Unit: $HB_USER"
echo ""

ok()   { echo "[OK]   $*"; }
warn() { echo "[WARN] $*"; }
fail() { echo "[FAIL] $*"; }

# ── Fix home directory ownership ──────────────────────────────────────────────
echo "--- Fixing ownership..."
# Home dir was written by deploy.sh as root; user now exists after userconf.txt
chown -R "${HB_USER}:${HB_USER}" "$HB_HOME" 2>/dev/null || true
ok "Ownership fixed: $HB_HOME"

# ── Install Node.js ───────────────────────────────────────────────────────────
echo ""
echo "--- Installing Node.js..."
if command -v node &>/dev/null; then
    ok "Node.js already installed: $(node --version)"
else
    if [ -f "$BUNDLE/$NODE_TARBALL" ]; then
        tar -xzf "$BUNDLE/$NODE_TARBALL" -C /usr/local --strip-components=1
        ok "Node.js installed: $(node --version)"
    else
        fail "Node.js tarball not found in bundle — skipping"
    fi
fi

# ── Create Python venv ────────────────────────────────────────────────────────
echo ""
echo "--- Creating Python virtual environment..."
VENV="$HB_HOME/horsebox/venv"
if [ ! -d "$VENV" ]; then
    sudo -u "$HB_USER" python3 -m venv "$VENV"
    ok "venv created"
else
    ok "venv already exists"
fi

# ── Install Python packages from wheelhouse ────────────────────────────────────
echo ""
echo "--- Installing Python packages (offline from wheelhouse)..."
WHEELHOUSE="$BUNDLE/wheelhouse"
REQUIREMENTS="$HB_HOME/horsebox/requirements.txt"

if [ -d "$WHEELHOUSE" ] && [ "$(ls -A "$WHEELHOUSE")" ]; then
    sudo -u "$HB_USER" "$VENV/bin/pip" install \
        --no-index \
        --find-links="$WHEELHOUSE" \
        -r "$REQUIREMENTS" \
        --quiet
    ok "Python packages installed"
else
    fail "Wheelhouse empty or missing — trying online install"
    sudo -u "$HB_USER" "$VENV/bin/pip" install \
        -r "$REQUIREMENTS" \
        --quiet \
        || warn "pip install failed — check $LOG"
fi

# ── Install Claude Code ────────────────────────────────────────────────────────
echo ""
echo "--- Installing Claude Code..."
if command -v claude &>/dev/null; then
    ok "Claude Code already installed: $(claude --version 2>/dev/null || echo 'unknown version')"
else
    # Try offline first (npm cache populated by prepare.sh)
    NPM_CACHE="$BUNDLE/npm-cache"
    INSTALL_OK=0

    if [ -d "$NPM_CACHE" ] && [ "$(ls -A "$NPM_CACHE")" ]; then
        echo "  Attempting offline install from npm cache..."
        npm install -g \
            --prefer-offline \
            --cache "$NPM_CACHE" \
            --no-audit \
            --no-fund \
            @anthropic-ai/claude-code \
            && INSTALL_OK=1 \
            || warn "Offline npm install failed, trying online..."
    fi

    if [ "$INSTALL_OK" -eq 0 ]; then
        echo "  Attempting online install..."
        npm install -g @anthropic-ai/claude-code \
            && INSTALL_OK=1 \
            || warn "Online npm install also failed"
    fi

    if [ "$INSTALL_OK" -eq 1 ]; then
        ok "Claude Code installed: $(claude --version 2>/dev/null || echo 'installed')"
    else
        warn "Claude Code could not be installed automatically."
        warn "Run manually when internet is available: sudo npm install -g @anthropic-ai/claude-code"
    fi
fi

# ── Verify ANTHROPIC_API_KEY is set ───────────────────────────────────────────
echo ""
echo "--- API key check..."
if grep -q "^ANTHROPIC_API_KEY=" /etc/environment 2>/dev/null; then
    KEY_PREVIEW=$(grep "^ANTHROPIC_API_KEY=" /etc/environment | tail -c 5 | tr -d '\n')
    ok "ANTHROPIC_API_KEY set (...${KEY_PREVIEW})"
else
    warn "ANTHROPIC_API_KEY not found in /etc/environment"
    warn "Add it manually: echo 'ANTHROPIC_API_KEY=sk-ant-...' | sudo tee -a /etc/environment"
fi

# ── X11 mode (required for kiosk) ─────────────────────────────────────────────
echo ""
echo "--- Setting display server to X11..."
if raspi-config nonint do_wayland W1 2>/dev/null; then
    ok "X11 mode set"
else
    warn "raspi-config do_wayland failed — may already be X11, or set manually"
    warn "Run: sudo raspi-config → Advanced Options → Wayland → X11"
fi

# ── Add convenience alias ─────────────────────────────────────────────────────
echo ""
echo "--- Adding convenience alias..."
BASHRC="$HB_HOME/.bashrc"
if ! grep -q "alias debug=" "$BASHRC" 2>/dev/null; then
    echo "" >> "$BASHRC"
    echo "# Horsebox debug shortcut" >> "$BASHRC"
    echo "alias debug='cd ~/horsebox && claude'" >> "$BASHRC"
    chown "${HB_USER}:${HB_USER}" "$BASHRC"
    ok "alias debug='cd ~/horsebox && claude' added to .bashrc"
fi

# ── Mark complete (prevents re-run) ───────────────────────────────────────────
echo ""
echo "--- Marking first boot complete..."
rm -f "$HB_HOME/horsebox/.first_boot_pending"
ok ".first_boot_pending removed"

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
echo "=== First Boot Complete: $(date) ==="
echo ""
echo "    Unit     : $HB_USER"
echo "    Hostname : $HB_HOSTNAME.local"
echo "    Log      : $LOG"
echo ""
echo "    Rebooting in 5 seconds to apply X11 mode..."
echo ""
sleep 5
reboot
