#!/bin/bash
#MISE description="deploy reef-pi integration to a local Home Assistant"
set -e
pwd

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Parse arguments
DRY_RUN=false
if [ "$1" = "--dry-run" ] || [ "$1" = "-n" ]; then
  DRY_RUN=true
fi

# Function to print colored messages
info() {
  echo -e "${GREEN}✓${NC} $1"
}

error() {
  echo -e "${RED}✗${NC} $1" >&2
  exit 1
}

warn() {
  echo -e "${YELLOW}!${NC} $1"
}

step() {
  echo -e "${BLUE}→${NC} $1"
}

diff_header() {
  echo -e "${CYAN}$1${NC}"
}

# Load .env file
if [ ! -f .env ]; then
  error ".env file not found. Please create one with HA_SERVER and HA_KEY variables.\n\nExample .env:\n  HA_SERVER=user@homeassistant.local\n  HA_KEY=/path/to/ssh/key"
fi

step "Loading environment variables from .env..."
set -a
source .env
set +a

# Validate required variables
if [ -z "$HA_SERVER" ]; then
  error "HA_SERVER is not set in .env file.\nExample: HA_SERVER=user@homeassistant.local"
fi

if [ -z "$HA_KEY" ]; then
  error "HA_KEY is not set in .env file.\nExample: HA_KEY=/path/to/ssh/key"
fi

# Validate SSH key exists
if [ ! -f "$HA_KEY" ]; then
  error "SSH key not found: $HA_KEY"
fi

info "Environment loaded:"
echo "  Server: $HA_SERVER"
echo "  SSH Key: $HA_KEY"
echo ""

# Test SSH connection
step "Testing SSH connection..."
if ! ssh -i "$HA_KEY" -o ConnectTimeout=5 -o BatchMode=yes "$HA_SERVER" "exit" 2>/dev/null; then
  error "Cannot connect to $HA_SERVER using SSH key $HA_KEY\nPlease check your credentials and network connection."
fi
info "SSH connection successful"

# Check if remote directory exists, create if not
step "Checking remote directory..."
if ! ssh -i "$HA_KEY" "$HA_SERVER" "test -d config/custom_components/reef_pi" 2>/dev/null; then
  warn "Remote directory doesn't exist, creating it..."
  ssh -i "$HA_KEY" "$HA_SERVER" "mkdir -p config/custom_components/reef_pi" || error "Failed to create remote directory"
  info "Remote directory created"
else
  info "Remote directory exists"
fi

# Get current version
current_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
echo ""
if [ "$DRY_RUN" = true ]; then
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${CYAN}DRY RUN: Comparing reef-pi v${current_version} with remote${NC}"
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
else
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${BLUE}Deploying reef-pi v${current_version} to Home Assistant${NC}"
  echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
fi
echo ""

# Dry-run mode: compare files
if [ "$DRY_RUN" = true ]; then
  # Create temp directory for remote files
  TEMP_DIR=$(mktemp -d)
  trap "rm -rf $TEMP_DIR" EXIT

  step "Downloading remote files for comparison..."

  # Check if remote directory exists
  if ! ssh -i "$HA_KEY" "$HA_SERVER" "test -d config/custom_components/reef_pi" 2>/dev/null; then
    warn "Remote directory doesn't exist yet"
    warn "Showing all local files as new..."
    echo ""
    diff_header "═══════════════════════════════════════════════════════════════"
    diff_header "All files will be created (no remote files found):"
    diff_header "═══════════════════════════════════════════════════════════════"
    find custom_components/reef_pi -type f -not -path "*/__pycache__/*" -not -name "*.pyc" | sed 's/custom_components\/reef_pi\///' | while read -r file; do
      echo -e "  ${GREEN}+ NEW:${NC} $file"
    done
    exit 0
  fi

  # Download remote files using tar+ssh
  if ssh -i "$HA_KEY" "$HA_SERVER" "cd config/custom_components && tar czf - --exclude='__pycache__' --exclude='*.pyc' reef_pi" | tar xzf - -C "$TEMP_DIR" 2>/dev/null; then
    info "Remote files downloaded"
  else
    error "Failed to download remote files. Check SSH connection and remote path."
  fi

  step "Comparing local and remote files..."
  echo ""

  # Compare directories
  diff_header "═══════════════════════════════════════════════════════════════"
  diff_header "Changes that would be deployed:"
  diff_header "═══════════════════════════════════════════════════════════════"

  # Track if any changes found
  CHANGES_FOUND=false

  # Check for new and modified files (exclude __pycache__)
  while IFS= read -r -d '' file; do
    rel_path="${file#custom_components/reef_pi/}"
    remote_file="$TEMP_DIR/reef_pi/$rel_path"

    if [ ! -f "$remote_file" ]; then
      echo -e "${GREEN}+ NEW:${NC} $rel_path"
      CHANGES_FOUND=true
    elif ! diff -q "$file" "$remote_file" >/dev/null 2>&1; then
      echo -e "${YELLOW}M MODIFIED:${NC} $rel_path"
      CHANGES_FOUND=true
    fi
  done < <(find custom_components/reef_pi -type f -not -path "*/__pycache__/*" -not -name "*.pyc" -print0)

  # Check for deleted files (exclude __pycache__)
  if [ -d "$TEMP_DIR/reef_pi" ]; then
    while IFS= read -r -d '' remote_file; do
      rel_path="${remote_file#$TEMP_DIR/reef_pi/}"
      local_file="custom_components/reef_pi/$rel_path"

      if [ ! -f "$local_file" ]; then
        echo -e "${RED}- DELETED:${NC} $rel_path"
        CHANGES_FOUND=true
      fi
    done < <(find "$TEMP_DIR/reef_pi" -type f -not -path "*/__pycache__/*" -not -name "*.pyc" -print0)
  fi

  if [ "$CHANGES_FOUND" = false ]; then
    echo -e "${GREEN}No changes detected - local and remote are identical${NC}"
  fi

  echo ""
  diff_header "═══════════════════════════════════════════════════════════════"
  echo -e "${CYAN}Note: __pycache__ and .pyc files are excluded from comparison${NC}"

  # Show detailed diff if requested
  echo ""
  read -p "Show detailed diff? (y/N) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    diff_header "Detailed differences:"
    diff_header "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

    while IFS= read -r -d '' file; do
      rel_path="${file#custom_components/reef_pi/}"
      remote_file="$TEMP_DIR/reef_pi/$rel_path"

      if [ -f "$remote_file" ] && ! diff -q "$file" "$remote_file" >/dev/null 2>&1; then
        echo ""
        diff_header "File: $rel_path"
        diff -u "$remote_file" "$file" || true
      fi
    done < <(find custom_components/reef_pi -type f -not -path "*/__pycache__/*" -not -name "*.pyc" -print0)
  fi

  echo ""
  info "Dry-run complete - no files were changed"
  exit 0
fi

# Copy files to server (exclude __pycache__)
step "Copying files to server (excluding __pycache__)..."
if tar czf - --exclude='__pycache__' --exclude='*.pyc' -C custom_components reef_pi | ssh -i "$HA_KEY" "$HA_SERVER" "cd config/custom_components && tar xzf -"; then
  info "Files copied successfully"
else
  error "Failed to copy files to server. Check SSH connection and permissions."
fi

# Verify files were copied
step "Verifying deployment..."
file_count=$(ssh -i "$HA_KEY" "$HA_SERVER" "find config/custom_components/reef_pi -type f -not -path '*/__pycache__/*' -not -name '*.pyc' | wc -l" | tr -d ' ')
if [ "$file_count" -gt 0 ]; then
  info "Verified: $file_count files deployed (excluding __pycache__)"
else
  error "Verification failed: No files found on server"
fi

# Restart Home Assistant
echo ""
step "Restarting Home Assistant core..."
warn "This will restart Home Assistant and may take a minute..."

# Run restart command and capture output
if ssh -i "$HA_KEY" "$HA_SERVER" "ha core restart" 2>&1 | while IFS= read -r line; do
  echo "  $line"
done; then
  info "Restart command sent successfully"
else
  warn "Restart command may have failed, but deployment is complete"
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Deployment complete!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
info "Next steps:"
echo "  1. Wait for Home Assistant to restart (~30-60 seconds)"
echo "  2. Check the logs for any errors"
echo "  3. Reload the reef-pi integration if needed"
echo ""
