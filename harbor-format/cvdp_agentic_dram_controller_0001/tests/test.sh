#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
printf '%s\n' '0' > /logs/verifier/reward.txt
export SIM=icarus
export WAVE=False
export TOPLEVEL_LANG=verilog
export VERILOG_SOURCES="/app/rtl/dramcntrl.sv"
export TOPLEVEL="dramcntrl"
export MODULE="test_dramcntrl"
export PYTHONPATH=/tests/harness/src
cd /app
if timeout 540 pytest -o cache_dir=/tmp/cvdp-pytest-cache /tests/harness/src/test_runner.py -v -s; then
  printf '%s\n' '1' > /logs/verifier/reward.txt
fi
