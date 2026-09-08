#!/usr/bin/env bash
set -euo pipefail
# Compatibility entry point. The root setup owns new-host provisioning.
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd -P)"
exec "$repo/setup" "$@"
