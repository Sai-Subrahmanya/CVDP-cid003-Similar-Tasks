import cocotb
from cocotb.triggers import RisingEdge, FallingEdge, Timer
from cocotb.clock import Clock
import logging
import random

def check_condition(condition, fail_msg, pass_msg, test_failures):
    """Helper function to log test results"""
    if not condition:
        logging.getLogger().error(fail_msg)
        test_failures.append(fail_msg)
    else:
        logging.getLogger().info(pass_msg)

@cocotb.test()
async def test_equalizer_learns_identity(dut):
    """Test if output equals input after 3 cycles when input == desired"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test if output equals input after 3 cycles when input == desired")

    # Start clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.rst_n.value = 0
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1

    # History buffer
    in_history_real = []
    in_history_imag = []

    for i in range(20):
        # Random input: 8192 or -8192
        value_real = random.choice([8192, -8192])
        value_imag = random.choice([8192, -8192])
        
        # Apply to input and desired
        dut.data_in_real.value = value_real
        dut.data_in_imag.value = value_imag
        dut.desired_real.value = value_real
        dut.desired_imag.value = value_imag

        # Store input for comparison later
        in_history_real.append(value_real)
        in_history_imag.append(value_imag)
        
        # Initialize list to collect failures
        test_failures = []

        # After 3 cycles, expect output = input (since input == desired)
        if i >= 5:
            expected_real = in_history_real[i - 5]
            expected_imag = in_history_imag[i - 5]
            out_real = dut.data_out_real.value.signed_integer
            out_imag = dut.data_out_imag.value.signed_integer

            # Check Data Output Real
            check_condition(
                out_real == expected_real,
                f"FAIL: Data Output Real mismatch. Expected: {expected_real}, "
                f"Got: {out_real}",
                f"PASS: Data Output Real value: {out_real}",
                test_failures
            )

            # Check Data Output Imaginary
            check_condition(
                out_imag == expected_imag,
                f"FAIL: Data Output Imaginary mismatch. Expected: {expected_imag}, "
                f"Got: {out_imag}",
                f"PASS: Data Output Imaginary value: {out_imag}",
                test_failures
            )
            
        await RisingEdge(dut.clk)

    # Report failures if any
    if test_failures:
        failure_message = "\n".join(test_failures)
        logger.error(f"Test identity completed with failures:\n{failure_message}")
        assert False, f"Some test cases failed. Check the log for details:\n{failure_message}"
    else:
        logger.info("Test identity completed successfully")

@cocotb.test()
async def test_equalizer_data_quadrant(dut):
    """Test if output data quadrant is the desired"""

    logger = dut._log
    logger.setLevel(logging.INFO)
    logger.info("Test if output data quadrant is the desired")

    # Start clock
    clock = Clock(dut.clk, 10, unit="ns")
    cocotb.start_soon(clock.start())

    # Reset
    dut.rst_n.value = 0
    for _ in range(2):
        await RisingEdge(dut.clk)
    dut.rst_n.value = 1

    # History buffer
    in_history_real = []
    in_history_imag = []

    for i in range(20):
        # Random input with error
        value_real = random.choice([8390, 8192, 7800, -8390, -8192, -7800])
        value_imag = random.choice([8390, 8192, 7800, -8390, -8192, -7800])
        
        # Apply to input and desired
        dut.data_in_real.value = value_real
        dut.data_in_imag.value = value_imag
        
        if value_real > 0:
            dut.desired_real.value = 8192
        else :
            dut.desired_real.value = -8192
        
        if value_imag > 0:
            dut.desired_imag.value = 8192
        else :
            dut.desired_imag.value = -8192

        # Store input for comparison later
        in_history_real.append(value_real)
        in_history_imag.append(value_imag)
        
        # Initialize list to collect failures
        test_failures = []

        # After 3 cycles, expect output = input (since input == desired)
        if i >= 5:
            expected_real = in_history_real[i - 5]
            expected_imag = in_history_imag[i - 5]
            out_real = dut.data_out_real.value.signed_integer
            out_imag = dut.data_out_imag.value.signed_integer

            # Check Data Output Real
            check_condition(
                (out_real > 0) == (expected_real > 0),
                f"FAIL: Data Output Real Quadrant mismatch. Expected: {(expected_real > 0)}, "
                f"Got: {(out_real > 0)}",
                f"PASS: Data Output Real Quadrant value: {(out_real > 0)}",
                test_failures
            )

            # Check Data Output Imaginary
            check_condition(
                (out_imag > 0) == (expected_imag > 0),
                f"FAIL: Data Output Imaginary Quadrant mismatch. Expected: {(expected_imag > 0)}, "
                f"Got: {(out_imag > 0)}",
                f"PASS: Data Output Imaginary Quadrant value: {(out_imag > 0)}",
                test_failures
            )
            
        await RisingEdge(dut.clk)

    # Report failures if any
    if test_failures:
        failure_message = "\n".join(test_failures)
        logger.error(f"Test quadrant completed with failures:\n{failure_message}")
        assert False, f"Some test cases failed. Check the log for details:\n{failure_message}"
    else:
        logger.info("Test quadrant completed successfully")
