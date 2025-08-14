#!/usr/bin/env bash
# Uso: ./release_prod.sh v1.0.0
set -euo pipefail
VER="${1:-}"; [[ "$VER" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { echo "Versione attesa: vX.Y.Z"; exit 1; }
git fetch --tags
git tag -a "$VER" -m "Release $VER"
git push origin "$VER"
echo "Tag $VER pubblicato. La GitHub Action deployerà PROD (stage=prod)."