# test_runner.py

import os
from cocotb_tools.runner import get_runner
import pytest
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Fetch environment variables
verilog_sources = os.getenv("VERILOG_SOURCES", "").split()
toplevel_lang   = os.getenv("TOPLEVEL_LANG", "verilog")
sim             = os.getenv("SIM", "icarus")
toplevel        = os.getenv("TOPLEVEL")
module          = os.getenv("MODULE")

def runner(TAP_NUM, DATA_WIDTH, COEFF_WIDTH, MU):
    # Initialize the simulator runner
    runner = get_runner(sim)

    # Build the simulation with the specified TAP_NUM, DATA_WIDTH, COEFF_WIDTH, and MU parameters
    runner.build(
        sources=verilog_sources,
        hdl_toplevel=toplevel,
        parameters={
            "TAP_NUM": TAP_NUM,
            "DATA_WIDTH": DATA_WIDTH,
            "COEFF_WIDTH": COEFF_WIDTH,
            "MU": MU},
        # Simulator Arguments
        always=True,
        clean=True,
        waves=True,        # Disable waveform generation for faster runs
        verbose=True,      # Set to True for detailed simulator logs
        timescale=("1ns", "1ps"),
        log_file=f"sim_{toplevel}.log"
    )

    # Run the simulation
    runner.test(
        hdl_toplevel=toplevel,
        test_module=module,
        waves=True
    )

    logger.info(f"Completed simulation with TAP_NUM, DATA_WIDTH, COEFF_WIDTH, and MU = {TAP_NUM, DATA_WIDTH, COEFF_WIDTH, MU}")

@pytest.mark.parametrize("TAP_NUM, DATA_WIDTH, COEFF_WIDTH, MU", [(7, 16, 16, 15)])
def test_cvdp_agentic_dynamic_equalizer(TAP_NUM, DATA_WIDTH, COEFF_WIDTH, MU):
    try:
        runner(TAP_NUM, DATA_WIDTH, COEFF_WIDTH, MU)
    except Exception as e:
        logger.error(f"Simulation failed for TAP_NUM, DATA_WIDTH, COEFF_WIDTH, MU = {TAP_NUM, DATA_WIDTH, COEFF_WIDTH, MU}: {e}")
        # Using assert False to report failure without halting other tests
        assert False, f"Simulation failed for TAP_NUM, DATA_WIDTH, COEFF_WIDTH, MU = {TAP_NUM, DATA_WIDTH, COEFF_WIDTH, MU}: {e}"