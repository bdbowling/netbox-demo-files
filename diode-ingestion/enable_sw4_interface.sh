#!/usr/bin/env bash
set -euo pipefail

# activate project venv
# shellcheck disable=SC1091
source venv/bin/activate

# env vars (note: these will be in your shell history if you edit interactively)
export DIODE_CLIENT_ID="diode-a340eea3d2d7ee9a"
export DIODE_CLIENT_SECRET="VjFWtb0YmSvEIUrwtQBkCtV86Ewx3KoMlYq7vmz5QfE="

set -a
source .env
set +a

python enable_interface.sw4_demo.py
