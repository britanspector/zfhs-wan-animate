#!/usr/bin/env bash
# Push zfhs-wan-animate to GitHub (requires SSH key on github.com/settings/keys).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${ROOT}"

if [[ -f /etc/network_turbo ]]; then
  # shellcheck disable=SC1091
  source /etc/network_turbo
fi

if [[ -z "${SSH_AUTH_SOCK:-}" ]] && [[ -f "${HOME}/.ssh/id_ed25519" ]]; then
  eval "$(ssh-agent -s)" >/dev/null
  ssh-add "${HOME}/.ssh/id_ed25519" 2>/dev/null || true
fi

echo "Testing GitHub SSH..."
ssh -o StrictHostKeyChecking=accept-new -T git@github.com || true

git push -u origin main
echo "Push complete: https://github.com/britanspector/zfhs-wan-animate"
