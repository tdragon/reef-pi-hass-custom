#!/bin/bash
#MISE description="release the current version of the integration"
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

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

# Function to get current version from pyproject.toml
get_current_version() {
  grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/'
}

# Function to validate version format (semver)
validate_version() {
  local version=$1
  if ! [[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    error "Invalid version format: $version (expected: X.Y.Z)"
  fi
}

# Function to calculate next version
calculate_version() {
  local current=$1
  local bump_type=$2

  IFS='.' read -r major minor patch <<<"$current"

  case $bump_type in
  major)
    echo "$((major + 1)).0.0"
    ;;
  minor)
    echo "$major.$((minor + 1)).0"
    ;;
  patch)
    echo "$major.$minor.$((patch + 1))"
    ;;
  *)
    error "Invalid bump type: $bump_type (expected: major, minor, or patch)"
    ;;
  esac
}

# Function to update version in a file
update_version_in_file() {
  local file=$1
  local old_version=$2
  local new_version=$3

  if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    sed -i '' "s/\"$old_version\"/\"$new_version\"/g" "$file"
    sed -i '' "s/version = \"$old_version\"/version = \"$new_version\"/g" "$file"
  else
    # Linux
    sed -i "s/\"$old_version\"/\"$new_version\"/g" "$file"
    sed -i "s/version = \"$old_version\"/version = \"$new_version\"/g" "$file"
  fi

  info "Updated $file"
}

# Check for uncommitted changes (both staged and unstaged)
if ! git diff --quiet || ! git diff --cached --quiet; then
  warn "You have uncommitted changes. Please commit or stash them first."
  echo ""
  git status --short
  error "Aborting release due to uncommitted changes"
fi

# Check for untracked files
untracked_files=$(git ls-files --others --exclude-standard)
if [ -n "$untracked_files" ]; then
  warn "You have untracked files. Please add or ignore them first."
  echo ""
  echo "$untracked_files" | while read -r file; do
    echo "  $file"
  done
  error "Aborting release due to untracked files"
fi

info "Working directory is clean"

# Check we're on master branch
current_branch=$(git branch --show-current)
if [ "$current_branch" != "master" ]; then
  warn "You are on branch '$current_branch', not 'master'"
  read -p "Continue anyway? (y/N) " -n 1 -r
  echo
  if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    error "Aborting release"
  fi
fi

# Fetch latest changes from origin
info "Fetching latest changes from origin..."
git fetch origin master --quiet

# Check if branch is in sync with origin
LOCAL=$(git rev-parse @)
REMOTE=$(git rev-parse origin/master)
BASE=$(git merge-base @ origin/master)

if [ "$LOCAL" != "$REMOTE" ]; then
  if [ "$LOCAL" = "$BASE" ]; then
    error "Your branch is behind 'origin/master'. Please pull the latest changes first:\n  git pull origin master"
  elif [ "$REMOTE" = "$BASE" ]; then
    warn "Your branch has unpushed commits."
    git --no-pager log origin/master..HEAD --oneline
    error "Please push your commits first:\n  git push origin master"
  else
    error "Your branch has diverged from 'origin/master'.\nPlease resolve the conflicts first."
  fi
fi

info "Branch is in sync with origin/master"

# Parse arguments
if [ $# -ne 1 ]; then
  error "Usage: $0 <version|major|minor|patch>\nExamples:\n  $0 patch        # Bump patch version\n  $0 minor        # Bump minor version\n  $0 major        # Bump major version\n  $0 0.5.0        # Set explicit version"
fi

# Get current version
current_version=$(get_current_version)
info "Current version: $current_version"

# Determine new version
version_arg=$1
if [[ $version_arg =~ ^(major|minor|patch)$ ]]; then
  new_version=$(calculate_version "$current_version" "$version_arg")
  info "Bumping $version_arg version: $current_version → $new_version"
else
  new_version=$version_arg
  validate_version "$new_version"
  info "Setting explicit version: $current_version → $new_version"
fi

# Check if tag already exists
if git rev-parse "v$new_version" >/dev/null 2>&1; then
  error "Tag v$new_version already exists"
fi

# Check if version already exists remotely
if git ls-remote --tags origin | grep -q "refs/tags/v$new_version"; then
  error "Tag v$new_version already exists on remote"
fi

# Update version in files
echo ""
info "Updating version in files..."
update_version_in_file "pyproject.toml" "$current_version" "$new_version"
update_version_in_file "custom_components/reef_pi/manifest.json" "$current_version" "$new_version"

# Verify changes
echo ""
info "Version changes:"
git diff pyproject.toml custom_components/reef_pi/manifest.json

# Confirm before proceeding
echo ""
read -p "Commit, tag, and push v$new_version? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  warn "Reverting changes..."
  git checkout pyproject.toml custom_components/reef_pi/manifest.json
  error "Release aborted by user"
fi

# Commit changes
echo ""
info "Creating commit..."
git add pyproject.toml custom_components/reef_pi/manifest.json
git commit -m "chore: release v$new_version"

# Create tag
info "Creating tag v$new_version..."
git tag -a "v$new_version" -m "Release v$new_version"

# Push to remote
info "Pushing to origin..."
git push origin master
git push origin "v$new_version"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Release v$new_version created successfully!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
info "GitHub Actions will now:"
echo "  1. Run tests (pytest + hassfest)"
echo "  2. Build reef_pi.zip package"
echo "  3. Create GitHub release (prerelease)"
echo ""
echo "Monitor progress at:"
echo "  https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\(.*\)\.git/\1/')/actions"
echo ""
