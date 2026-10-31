#!/usr/bin/env bash
# Fetch a GitHub repo as a tarball. No git required, nothing from the repo runs.
#
#   bash fetch.sh owner/repo [dest]
#   bash fetch.sh https://github.com/owner/repo [dest]
set -euo pipefail

raw="${1:?usage: fetch.sh owner/repo [dest]}"
slug="$(printf '%s' "$raw" | sed -E 's#^https?://github\.com/##; s#\.git$##; s#/+$##')"
dest="${2:-/tmp/teardown/$(basename "$slug")}"

case "$slug" in
  */*) ;;
  *) echo "expected owner/repo, got: $raw" >&2; exit 2 ;;
esac

mkdir -p "$dest"
echo "fetching $slug -> $dest" >&2
curl -fsSL "https://api.github.com/repos/$slug/tarball/HEAD" \
  | tar xz -C "$dest" --strip-components=1

# Metadata worth having next to the checkout: age, license, and the star count
# you are going to refuse to treat as evidence.
curl -fsSL "https://api.github.com/repos/$slug" > "$dest/.teardown-meta.json" || true
echo "done: $dest" >&2
