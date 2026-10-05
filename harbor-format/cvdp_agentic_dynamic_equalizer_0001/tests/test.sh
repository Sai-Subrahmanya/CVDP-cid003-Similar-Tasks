#!/bin/bash
set -uo pipefail
mkdir -p /logs/verifier
printf '%s\n' '0' > /logs/verifier/reward.txt
export SIM=icarus
export WAVE=False
export TOPLEVEL_LANG=verilog
export VERILOG_SOURCES="/app/rtl/dynamic_equalizer.sv /app/rtl/error_calc.sv /app/rtl/coeff_update.sv"
export TOPLEVEL="dynamic_equalizer"
export MODULE="test_dynamic_equalizer_harness"
export PYTHONPATH=/tests/harness/src
cd /app
if timeout 540 pytest -o cache_dir=/tmp/cvdp-pytest-cache /tests/harness/src/test_runner.py -v -s; then
  printf '%s\n' '1' > /logs/verifier/reward.txt
fi
