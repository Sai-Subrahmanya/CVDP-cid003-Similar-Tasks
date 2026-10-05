import os
import re
import subprocess
import pytest

# ----------------------------------------
# - Simulate
# ----------------------------------------

@pytest.mark.usefixtures(scope='session')
def test_simulate():

    cmd = "xrun -coverage all /src/*.sv /code/verif/*.sv -covtest test -seed random -covoverwrite"
    assert(subprocess.run(cmd, shell=True)), "Simulation didn't ran correctly."

# ----------------------------------------
# - Generate Coverage
# ----------------------------------------

@pytest.mark.usefixtures(scope='test_simulate')
def test_coverage():

    cmd = "imc -load /code/rundir/cov_work/scope/test -exec /src/coverage.cmd"
    assert(subprocess.run(cmd, shell=True)), "Coverage merge didn't ran correctly."

# ----------------------------------------
# - Report
# ----------------------------------------

@pytest.mark.usefixtures(scope='test_coverage')
def test_report():

    metrics = {}

    with open("/code/rundir/coverage.log") as f:
        lines = f.readlines()

    # ----------------------------------------
    # - Evaluate Report
    # ----------------------------------------

    for line in lines[2:]:
        info = line.split()

        inst = info [0]
        avg  = info [1]
        cov  = info [2]

        inst = re.sub(r'[\W]', '', inst)

        metrics [inst] = {
            "Average" : float(avg[:-1]),
            "Covered" : float(cov[:-1])
        }

    assert metrics ["DUT"]["Average"] >= float(os.getenv("TARGET")), "Didn't achieved the required coverage result."