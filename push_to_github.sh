#!/usr/bin/env bash
# Publish this folder to the private GitHub repo.
# Run on your Mac, from inside the "Disease ontologies" folder:
#     cd "<this folder>" && bash push_to_github.sh
#
# .gitignore (already present) excludes the copyrighted PDFs in "Disease onto papers/".

set -euo pipefail
REMOTE="https://github.com/Strubbelig/Disease_onto.git"

# Safety check: are we in the right folder?
if [ ! -f "Disease proposal 2.ttl" ]; then
  echo "ERROR: run this from inside the 'Disease ontologies' folder (Disease proposal 2.ttl not found)." >&2
  exit 1
fi

# Remove any incomplete .git left by the earlier (sandbox) attempt — there are no commits to lose.
if [ -d .git ] && ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  echo "Removing incomplete .git from the earlier attempt..."
  rm -rf .git
fi

# Init
git init -b main 2>/dev/null || { git init; git branch -M main; }

# Identity fallback (only sets if you have none configured globally)
git config user.name  >/dev/null 2>&1 || git config user.name  "Moritz Milewski"
git config user.email >/dev/null 2>&1 || git config user.email "moritz.milewski@yale.edu"

git add -A
echo "Files to be committed (PDFs should NOT appear):"
git status --short | grep -i "\.pdf" && { echo "WARNING: PDFs are staged — check .gitignore"; } || echo "  ok: no PDFs staged"

git commit -m "Initial commit: disease ontology proposal, modules, and accompanying research"
git remote add origin "$REMOTE" 2>/dev/null || git remote set-url origin "$REMOTE"
git push -u origin main

echo
echo "Done → https://github.com/Strubbelig/Disease_onto"
