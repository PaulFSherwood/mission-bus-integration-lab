#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python -m tools.mbil_control_center
