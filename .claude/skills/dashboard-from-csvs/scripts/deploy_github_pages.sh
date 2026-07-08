#!/usr/bin/env bash
# Deploy the current directory's static dashboard to GitHub Pages.
#
# What this does, in order (see SKILL.md Step 4 for why each step exists):
#   1. Check for the gh CLI, offer to install it if missing.
#   2. Check gh auth status, walk through browser login if needed.
#   3. git init/commit if this isn't already a repo, add the remote, push.
#   4. Enable GitHub Pages via the API (no manual Settings click needed).
#   5. Poll the build status until it's done and print the live URL.
#
# Usage:
#   ./deploy_github_pages.sh <remote-repo-url>
# Example:
#   ./deploy_github_pages.sh https://github.com/yourname/your-repo.git
#
# Run this from the project directory that contains index.html.
# It will NOT run unattended past the auth step — if gh isn't logged in,
# it prints a one-time code and waits for you to finish the browser login.

set -euo pipefail

REMOTE_URL="${1:-}"
if [ -z "$REMOTE_URL" ]; then
  echo "usage: $0 <remote-repo-url>" >&2
  echo "example: $0 https://github.com/yourname/your-repo.git" >&2
  exit 1
fi

OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's#.*github\.com[:/]([^/]+)/([^/.]+)(\.git)?#\1/\2#')
if [ -z "$OWNER_REPO" ] || [ "$OWNER_REPO" = "$REMOTE_URL" ]; then
  echo "Could not parse owner/repo out of '$REMOTE_URL' — expected a github.com URL." >&2
  exit 1
fi

echo "== Step 1: checking for gh CLI =="
if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI not found."
  case "$(uname -s)" in
    MINGW*|MSYS*|CYGWIN*)
      echo "Installing via winget (this modifies your system — you'll see a confirmation prompt from your terminal harness)..."
      winget install --id GitHub.cli -e --accept-source-agreements --accept-package-agreements
      ;;
    Darwin*)
      echo "Installing via Homebrew..."
      brew install gh
      ;;
    *)
      echo "Please install the gh CLI for your platform: https://github.com/cli/cli#installation" >&2
      exit 1
      ;;
  esac
else
  echo "gh CLI found: $(gh --version | head -1)"
fi

echo "== Step 2: checking gh auth status =="
if ! gh auth status >/dev/null 2>&1; then
  echo "Not logged in. Starting browser login — copy the one-time code shown below,"
  echo "open the URL, and complete the login in your browser. This step needs a human;"
  echo "it cannot be automated further."
  gh auth login --hostname github.com --git-protocol https --web
else
  echo "Already authenticated as $(gh api user --jq .login)."
fi

echo "== Step 3: git init / commit / push =="
if [ ! -d .git ]; then
  git init
fi
if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "$REMOTE_URL"
fi
git add -A -- ':!*.csv'   # never stage raw CSVs even if a .gitignore is missing
if ! git diff --cached --quiet; then
  git commit -m "Deploy dashboard"
fi
git branch -M main
git push -u origin main

echo "== Step 4: enabling GitHub Pages =="
gh api "repos/${OWNER_REPO}/pages" -X POST -f "source[branch]=main" -f "source[path]=/" \
  || echo "(Pages may already be enabled for this repo — continuing.)"

echo "== Step 5: waiting for the build to finish =="
for i in $(seq 1 30); do
  STATUS=$(gh api "repos/${OWNER_REPO}/pages/builds/latest" --jq .status 2>/dev/null || echo "pending")
  echo "  status: $STATUS"
  if [ "$STATUS" = "built" ] || [ "$STATUS" = "errored" ]; then
    break
  fi
  sleep 5
done

LIVE_URL="https://$(echo "$OWNER_REPO" | cut -d/ -f1).github.io/$(echo "$OWNER_REPO" | cut -d/ -f2)/"
echo ""
echo "Repo:  https://github.com/${OWNER_REPO}"
echo "Live:  ${LIVE_URL}"
echo ""
echo "Fetch the live URL yourself (or ask the user to) to confirm it actually renders —"
echo "a 'built' status only means GitHub finished copying files."
