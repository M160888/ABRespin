#!/bin/bash
# =============================================================================
# horsebox deploy.sh — Run on Chromebook after flashing Pi OS to NVMe
#
# Prerequisites:
#   1. Raspberry Pi OS (64-bit, Bookworm) flashed to NVMe via Pi Imager
#      - In Pi Imager: skip the "customise OS" step entirely (we handle it)
#      - NVMe still connected via USB to Chromebook
#   2. If on Crostini: share the USB adapter with Linux first
#      (ChromeOS Settings → Linux → USB devices → share your adapter)
#   3. prepare.sh must have been run at least once to create deploy/bundle/
#
# Usage: ./deploy.sh
# =============================================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BUNDLE="$SCRIPT_DIR/bundle"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
NODE_VERSION="20.11.1"
NODE_TARBALL="node-v${NODE_VERSION}-linux-arm64.tar.gz"

MOUNT_BOOT="/mnt/hb-boot"
MOUNT_ROOT="/mnt/hb-root"

# ── Colours ──────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓${NC} $*"; }
warn() { echo -e "${YELLOW}  !${NC} $*"; }
die()  { echo -e "${RED}  ✗ ERROR:${NC} $*"; exit 1; }
step() { echo -e "\n${CYAN}──${NC} $* ${CYAN}──${NC}"; }

# ── Cleanup on exit ───────────────────────────────────────────────────────────
cleanup() {
    if mountpoint -q "$MOUNT_ROOT" 2>/dev/null; then
        sudo umount "$MOUNT_ROOT" 2>/dev/null || true
    fi
    if mountpoint -q "$MOUNT_BOOT" 2>/dev/null; then
        sudo umount "$MOUNT_BOOT" 2>/dev/null || true
    fi
    sudo rmdir "$MOUNT_BOOT" "$MOUNT_ROOT" 2>/dev/null || true
}
trap cleanup EXIT

# =============================================================================
echo ""
echo "╔══════════════════════════════════════╗"
echo "║   Horsebox Deploy — Unit Setup       ║"
echo "╚══════════════════════════════════════╝"
echo ""

# ── Pre-flight checks ─────────────────────────────────────────────────────────
step "Pre-flight checks"

[ -d "$BUNDLE" ]              || die "deploy/bundle/ not found — run prepare.sh first"
[ -f "$BUNDLE/$NODE_TARBALL" ] || die "Node.js tarball missing from bundle — run prepare.sh"
WHEEL_COUNT=$(ls "$BUNDLE/wheelhouse/" 2>/dev/null | wc -l)
[ "$WHEEL_COUNT" -gt 0 ]      || die "Wheelhouse is empty — run prepare.sh first"
ok "Bundle present ($WHEEL_COUNT Python wheels)"

command -v openssl &>/dev/null || die "openssl not found"
ok "openssl found"

# ── Prompts ───────────────────────────────────────────────────────────────────
step "Unit configuration"

echo ""
read -rp "  Horsebox ID (username + hostname, e.g. hb01, abrespin-03): " HB_USER
[[ "$HB_USER" =~ ^[a-z][a-z0-9-]{0,30}$ ]] || die "Username must be lowercase letters/numbers/hyphens, starting with a letter"

echo ""
while true; do
    read -rsp "  SSH password for $HB_USER: " HB_PASS; echo ""
    read -rsp "  Confirm password: " HB_PASS2; echo ""
    [ "$HB_PASS" = "$HB_PASS2" ] && break
    warn "Passwords don't match, try again."
done

echo ""
read -rsp "  Anthropic API key (sk-ant-...): " HB_API_KEY; echo ""
[[ "$HB_API_KEY" == sk-ant-* ]] || warn "Key doesn't look like a standard Anthropic key — continuing anyway"

echo ""
read -rp "  WiFi SSID (leave blank to skip): " WIFI_SSID
if [ -n "$WIFI_SSID" ]; then
    read -rsp "  WiFi password: " WIFI_PASS; echo ""
fi

HB_HOME="/home/$HB_USER"
KEY_PREVIEW="${HB_API_KEY: -4}"

echo ""
echo "  ┌─────────────────────────────────────┐"
echo "  │  Unit      : $HB_USER"
echo "  │  Hostname  : $HB_USER.local"
echo "  │  API key   : ...${KEY_PREVIEW} (last 4)"
if [ -n "$WIFI_SSID" ]; then
    echo "  │  WiFi      : $WIFI_SSID"
else
    echo "  │  WiFi      : none (ethernet only)"
fi
echo "  └─────────────────────────────────────┘"
echo ""
read -rp "  Proceed? [y/N] " CONFIRM
[[ "$CONFIRM" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 0; }

# ── Find NVMe partitions ──────────────────────────────────────────────────────
step "Finding Pi OS partitions"

# Pi Imager labels them 'bootfs' and 'rootfs'
BOOT_PART=$(blkid -L bootfs 2>/dev/null || true)
ROOT_PART=$(blkid -L rootfs 2>/dev/null || true)

if [ -z "$BOOT_PART" ] || [ -z "$ROOT_PART" ]; then
    echo ""
    warn "Could not auto-detect partitions by label. Available block devices:"
    lsblk -o NAME,SIZE,FSTYPE,LABEL,MOUNTPOINT | grep -v "^loop"
    echo ""
    read -rp "  Boot partition (e.g. /dev/sdb1): " BOOT_PART
    read -rp "  Root partition (e.g. /dev/sdb2): " ROOT_PART
fi

ok "Boot : $BOOT_PART"
ok "Root : $ROOT_PART"

# Unmount if already mounted (Pi Imager or auto-mount)
for part in "$BOOT_PART" "$ROOT_PART"; do
    if grep -q "$part" /proc/mounts 2>/dev/null; then
        sudo umount "$part" && ok "Unmounted $part"
    fi
done

# Mount
sudo mkdir -p "$MOUNT_BOOT" "$MOUNT_ROOT"
sudo mount "$BOOT_PART" "$MOUNT_BOOT"
sudo mount "$ROOT_PART" "$MOUNT_ROOT"
ok "Mounted boot → $MOUNT_BOOT"
ok "Mounted root → $MOUNT_ROOT"

# ── Boot partition config ─────────────────────────────────────────────────────
step "Boot partition"

# User account (bypasses first-boot wizard)
PASS_HASH=$(echo "$HB_PASS" | openssl passwd -6 -stdin)
echo "${HB_USER}:${PASS_HASH}" | sudo tee "$MOUNT_BOOT/userconf.txt" > /dev/null
ok "userconf.txt written (user: $HB_USER)"

# Enable SSH
sudo touch "$MOUNT_BOOT/ssh"
ok "SSH enabled"

# ── Root partition — hostname ─────────────────────────────────────────────────
step "Hostname"

echo "$HB_USER" | sudo tee "$MOUNT_ROOT/etc/hostname" > /dev/null
sudo sed -i "s/raspberrypi/$HB_USER/g" "$MOUNT_ROOT/etc/hosts" 2>/dev/null || true
# Ensure 127.0.1.1 entry exists
if ! grep -q "127.0.1.1" "$MOUNT_ROOT/etc/hosts" 2>/dev/null; then
    echo "127.0.1.1       $HB_USER" | sudo tee -a "$MOUNT_ROOT/etc/hosts" > /dev/null
fi
ok "Hostname: $HB_USER"

# ── Sudo access ───────────────────────────────────────────────────────────────
step "Sudo"

echo "${HB_USER} ALL=(ALL) NOPASSWD: ALL" | sudo tee "$MOUNT_ROOT/etc/sudoers.d/010_${HB_USER}" > /dev/null
sudo chmod 440 "$MOUNT_ROOT/etc/sudoers.d/010_${HB_USER}"
ok "Passwordless sudo for $HB_USER"

# ── WiFi ──────────────────────────────────────────────────────────────────────
if [ -n "$WIFI_SSID" ]; then
    step "WiFi"
    NM_DIR="$MOUNT_ROOT/etc/NetworkManager/system-connections"
    sudo mkdir -p "$NM_DIR"
    NM_FILE="$NM_DIR/${WIFI_SSID}.nmconnection"
    sudo tee "$NM_FILE" > /dev/null <<NMEOF
[connection]
id=${WIFI_SSID}
type=wifi
autoconnect=true

[wifi]
ssid=${WIFI_SSID}
mode=infrastructure

[wifi-security]
key-mgmt=wpa-psk
psk=${WIFI_PASS}

[ipv4]
method=auto

[ipv6]
method=auto
addr-gen-mode=default
NMEOF
    sudo chmod 600 "$NM_FILE"
    ok "WiFi config written: $WIFI_SSID"
fi

# ── API key ───────────────────────────────────────────────────────────────────
step "API key"

# Add to /etc/environment (available system-wide, persists across reboots)
sudo sed -i '/^ANTHROPIC_API_KEY=/d' "$MOUNT_ROOT/etc/environment" 2>/dev/null || true
echo "ANTHROPIC_API_KEY=${HB_API_KEY}" | sudo tee -a "$MOUNT_ROOT/etc/environment" > /dev/null
ok "ANTHROPIC_API_KEY written to /etc/environment"

# ── lightdm autologin ─────────────────────────────────────────────────────────
step "Auto-login"

sudo mkdir -p "$MOUNT_ROOT/etc/lightdm"
sudo tee "$MOUNT_ROOT/etc/lightdm/lightdm.conf" > /dev/null <<LEOF
[Seat:*]
autologin-user=${HB_USER}
autologin-user-timeout=0
greeter-session=pi-greeter
LEOF
ok "lightdm autologin: $HB_USER"

# ── Project files ─────────────────────────────────────────────────────────────
step "Project files"

DEST="$MOUNT_ROOT${HB_HOME}/horsebox"
sudo mkdir -p "$DEST"

# Copy project (exclude dev/deploy artefacts)
sudo rsync -a \
    --exclude='venv/' \
    --exclude='__pycache__/' \
    --exclude='*.pyc' \
    --exclude='.git/' \
    --exclude='deploy/bundle/' \
    --exclude='deploy/npm-cache/' \
    "$PROJECT_ROOT/" "$DEST/"

ok "Project files copied"

# ── Bundle (wheels + node) ────────────────────────────────────────────────────
step "Dependency bundle"

BUNDLE_DEST="$DEST/bundle"
sudo mkdir -p "$BUNDLE_DEST"
sudo cp -r "$BUNDLE/wheelhouse" "$BUNDLE_DEST/"
sudo cp "$BUNDLE/$NODE_TARBALL" "$BUNDLE_DEST/"
sudo cp -r "$BUNDLE/npm-cache" "$BUNDLE_DEST/"
ok "Wheelhouse copied ($(ls "$BUNDLE/wheelhouse/" | wc -l) wheels)"
ok "Node.js tarball copied"
ok "npm cache copied"

# ── Deploy config (read by first_boot.sh) ─────────────────────────────────────
sudo tee "$DEST/.deploy_config" > /dev/null <<DCEOF
HB_USER="${HB_USER}"
HB_HOME="${HB_HOME}"
HB_HOSTNAME="${HB_USER}"
NODE_TARBALL="${NODE_TARBALL}"
DCEOF
ok ".deploy_config written"

# ── first_boot sentinel ───────────────────────────────────────────────────────
sudo touch "$DEST/.first_boot_pending"

# ── Systemd services ──────────────────────────────────────────────────────────
step "Systemd services"

SYSTEMD="$MOUNT_ROOT/etc/systemd/system"
sudo mkdir -p "$SYSTEMD"

# Write service files with username substituted
for svc in horsebox-control.service horsebox-kiosk.service; do
    sudo sed "s|/home/pi/|${HB_HOME}/|g; s|User=pi|User=${HB_USER}|g; s|XAUTHORITY=/home/pi/|XAUTHORITY=${HB_HOME}/|g" \
        "$PROJECT_ROOT/$svc" | sudo tee "$SYSTEMD/$svc" > /dev/null
    ok "$svc written"
done

# Write first_boot.service
sudo tee "$SYSTEMD/horsebox-first-boot.service" > /dev/null <<SEOF
[Unit]
Description=Horsebox First Boot Setup
After=multi-user.target
ConditionPathExists=${HB_HOME}/horsebox/.first_boot_pending

[Service]
Type=oneshot
ExecStart=${HB_HOME}/horsebox/deploy/first_boot.sh
RemainAfterExit=yes
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
SEOF
ok "horsebox-first-boot.service written"

# Enable services (create symlinks)
MULTI_USER_WANTS="$SYSTEMD/multi-user.target.wants"
GRAPHICAL_WANTS="$SYSTEMD/graphical.target.wants"
sudo mkdir -p "$MULTI_USER_WANTS" "$GRAPHICAL_WANTS"

sudo ln -sf "/etc/systemd/system/horsebox-control.service"     "$MULTI_USER_WANTS/horsebox-control.service"
sudo ln -sf "/etc/systemd/system/horsebox-first-boot.service"  "$MULTI_USER_WANTS/horsebox-first-boot.service"
sudo ln -sf "/etc/systemd/system/horsebox-kiosk.service"       "$GRAPHICAL_WANTS/horsebox-kiosk.service"
ok "Services enabled"

# ── Unmount ───────────────────────────────────────────────────────────────────
step "Finalising"

sync
sudo umount "$MOUNT_BOOT"
sudo umount "$MOUNT_ROOT"
ok "Partitions unmounted safely"

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║  Done — $HB_USER ready to deploy                    "
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "  1. Disconnect the NVMe from Chromebook"
echo "  2. Fit NVMe into the Pi"
echo "  3. Power on — first boot takes ~3 min (installs venv, Node, Claude Code)"
echo "  4. SSH in after boot:  ssh ${HB_USER}@${HB_USER}.local"
echo "     (or via IP if .local doesn't resolve)"
echo ""
echo "  Claude Code (once booted):  cd ~/horsebox && claude"
echo ""
