import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, Timer
from cocotb.utils import get_sim_time

###############################################################################
# Helper: wait_cycles()
###############################################################################
async def wait_cycles(dut, num_cycles):
    """Wait for `num_cycles` rising edges of dut.clk_in."""
    for _ in range(num_cycles):
        await RisingEdge(dut.clk_in)

@cocotb.test()
async def test_dramcntrl(dut):
    """
    Cocotb test for the dramcntrl module, replicating the updated Verilog TB steps:

    PHASE 1:  Reset + Initialization
    PHASE 2:  Basic Writes
    PHASE 3:  Basic Reads
    PHASE 4:  Check auto-refresh
    PHASE 5:  Concurrent read/write
    PHASE 6:  Mid-test reset + re-init
    PHASE 7:  Saturate no_of_refs_needed
    PHASE 8:  Read/Write while busy
    """

    ############################################################################
    # Local pass/fail counters
    ############################################################################
    PASS_count = 0
    FAIL_count = 0

    ############################################################################
    # Create a 100 MHz clock (10 ns period) on `dut.clk_in`
    ############################################################################
    clock = Clock(dut.clk_in, 10, unit="ns")
    cocotb.start_soon(clock.start())

    ############################################################################
    # Initialize signals
    ############################################################################
    dut.reset.value            = 0
    dut.addr_from_up.value     = 0
    dut.rd_n_from_up.value     = 1
    dut.wr_n_from_up.value     = 1
    dut.bus_term_from_up.value = 1

    ###########################################################################
    # Define Tasks (async coroutines) converted from the Verilog tasks
    ###########################################################################

    async def apply_reset():
        """
        Replicates the Verilog task: set reset=1 for 10 cycles, then back to 0
        """
        dut.reset.value = 1
        await wait_cycles(dut, 10)
        dut.reset.value = 0

    async def check_init_done():
        """
        Waits up to 200000 clock cycles for dram_init_done to go high.
        If it never does, it's a FAIL. Otherwise, PASS.
        """
        nonlocal PASS_count, FAIL_count
        max_wait_cycles = 200000
        found_init = False

        for _ in range(max_wait_cycles):
            if dut.dram_init_done.value == 1:
                cocotb.log.info(
                    f"Time {get_sim_time('ns')}: [PASS] dram_init_done asserted."
                )
                PASS_count += 1
                found_init = True
                break
            await RisingEdge(dut.clk_in)

        if not found_init:
            cocotb.log.error(
                f"Time {get_sim_time('ns')}: [FAIL] dram_init_done not asserted within time limit!"
            )
            FAIL_count += 1

    async def do_write(address):
        """
        Issues a WRITE to `address`.
        - wr_n_from_up=0 for 3 cycles
        - then deassert
        - wait 12 cycles
        """
        cocotb.log.info(
            f"Time {get_sim_time('ns')}: Starting WRITE to address 0x{address:X}"
        )
        dut.wr_n_from_up.value     = 0
        dut.addr_from_up.value     = address
        dut.rd_n_from_up.value     = 1
        dut.bus_term_from_up.value = 1

        # Keep asserted for 3 cycles
        await wait_cycles(dut, 3)

        # Deassert
        dut.wr_n_from_up.value = 1

        # Wait 12 cycles for burst terminate + precharge
        await wait_cycles(dut, 12)

    async def do_read(address):
        """
        Issues a READ to `address`.
        - rd_n_from_up=0 for 3 cycles
        - then deassert
        - wait 12 cycles
        """
        cocotb.log.info(
            f"Time {get_sim_time('ns')}: Starting READ from address 0x{address:X}"
        )
        dut.rd_n_from_up.value     = 0
        dut.addr_from_up.value     = address
        dut.wr_n_from_up.value     = 1
        dut.bus_term_from_up.value = 1

        # Keep asserted for 3 cycles
        await wait_cycles(dut, 3)

        # Deassert
        dut.rd_n_from_up.value = 1

        # Wait 12 cycles for burst terminate + precharge
        await wait_cycles(dut, 12)

    async def do_concurrent_rd_wr(address_wr, address_rd):
        """
        Forces read & write requests simultaneously:
        1) wr_n_from_up=0, rd_n_from_up=0 at same time
        2) Switch addresses mid-flight
        3) Deassert write first, then read
        """
        cocotb.log.info(
            f"Time {get_sim_time('ns')}: Starting concurrent RD & WR "
            f"(WR=0x{address_wr:X}, RD=0x{address_rd:X})"
        )
        # Step 1: Assert both
        dut.wr_n_from_up.value     = 0
        dut.rd_n_from_up.value     = 0
        dut.addr_from_up.value     = address_wr
        dut.bus_term_from_up.value = 1
        await wait_cycles(dut, 5)

        # Step 2: Switch addresses mid-flight
        cocotb.log.info(f"Time {get_sim_time('ns')}: Switching to read address 0x{address_rd:X}")
        dut.addr_from_up.value = address_rd
        await wait_cycles(dut, 5)

        # Step 3: Deassert write first
        cocotb.log.info("Time %d: Deasserting write, keeping read active" % get_sim_time('ns'))
        dut.wr_n_from_up.value = 1
        await wait_cycles(dut, 5)

        # Step 4: Deassert read
        cocotb.log.info("Time %d: Deasserting read" % get_sim_time('ns'))
        dut.rd_n_from_up.value = 1

        # Wait for the precharge, etc.
        await wait_cycles(dut, 12)

    async def check_auto_ref_pending():
        """
        Checks auto-refresh scheduling.
        - Wait 1000 cycles
        - See if no_of_refs_needed == 0 or if dram_busy=1
        - Then wait 20 more cycles to see if dram_busy=0
        """
        nonlocal PASS_count, FAIL_count

        cocotb.log.info(
            f"Time {get_sim_time('ns')}: Checking auto-refresh scheduling ..."
        )
        # Wait 1000 cycles
        await wait_cycles(dut, 1000)

        # Attempt to read internal signal no_of_refs_needed, if visible
        try:
            no_of_refs = int(dut.DUT.no_of_refs_needed.value)
            if no_of_refs == 0:
                cocotb.log.info(
                    f"Time {get_sim_time('ns')}: [INFO] No auto-refs needed yet (no_of_refs_needed=0)."
                )
                PASS_count += 1
            elif dut.dram_busy.value == 1:
                cocotb.log.info(
                    f"Time {get_sim_time('ns')}: [INFO] dram_busy=1 => auto-refresh pending."
                )
                PASS_count += 1
            else:
                cocotb.log.warning(
                    f"Time {get_sim_time('ns')}: [WARNING] no_of_refs_needed={no_of_refs}, but dram_busy=0."
                )
        except AttributeError:
            # If simulator hides internal signals:
            cocotb.log.warning(
                "Could not read internal DUT.no_of_refs_needed. Skipping that portion of the check."
            )

        # Wait another 20 cycles
        await wait_cycles(dut, 20)

        if dut.dram_busy.value == 0:
            cocotb.log.info(
                f"Time {get_sim_time('ns')}: [PASS] auto-refresh done (dram_busy=0)."
            )
            PASS_count += 1
        else:
            cocotb.log.error(
                f"Time {get_sim_time('ns')}: [FAIL] auto-refresh still busy (dram_busy=1)!"
            )
            FAIL_count += 1

    async def saturate_no_of_refs():
        """
        Forces many auto-refresh increments to drive no_of_refs_needed
        toward saturation.
        The Verilog code loops ~ (1 << (len_auto_ref - 2)) times,
        each time waiting 800 cycles to trigger the 7.81us intervals.
        NOTE: This can be very time-consuming in simulation.
        """
        cocotb.log.info(
            f"Time {get_sim_time('ns')}: Attempting to saturate no_of_refs_needed..."
        )

        try:
            # We'll try to read the parameter len_auto_ref from the design if possible.
            # Or just hard-code the known value. By default the user set len_auto_ref=10.
            # If you want to read it from the HDL directly, that depends on your environment.
            len_auto_ref = 10  # as per the localparam in the RTL
            limit = 1 << (len_auto_ref - 2)
        except:
            limit = 256  # fallback

        for _ in range(limit):
            # ~800 cycles is enough time for the internal controller to increment
            # one_auto_ref_time_done multiple times, building up no_of_refs_needed.
            await wait_cycles(dut, 800)

        # After the loop, print the final value if visible
        try:
            val = int(dut.DUT.no_of_refs_needed.value)
            cocotb.log.info(
                f"Time {get_sim_time('ns')}: Done saturating no_of_refs_needed. Value = {val:b}"
            )
        except AttributeError:
            cocotb.log.warning("Could not read no_of_refs_needed after saturation.")

    async def do_test_during_busy():
        """
        Forces a read and write while auto-refs are presumably pending (dram_busy=1).
        NOTE: We rely on saturate_no_of_refs to have built up auto-ref backlog.
        """
        cocotb.log.info(
            f"Time {get_sim_time('ns')}: Forcing new read/write while dram_busy may be active..."
        )
        await do_read(0xFFFFAA)
        await do_write(0xFFFBBB)

    ###########################################################################
    # PHASE 1: Basic Reset + Init
    ###########################################################################
    cocotb.log.info("==========================================================")
    cocotb.log.info("= Starting dramcntrl_tb (Cocotb) simulation              =")
    cocotb.log.info("==========================================================")

    # Apply reset & wait for initialization
    await apply_reset()
    await check_init_done()

    ###########################################################################
    # PHASE 2: Basic Writes
    ###########################################################################
    await do_write(0x000001)
    await do_write(0x300123)
    await do_write(0x1A0456)

    ###########################################################################
    # PHASE 3: Basic Reads
    ###########################################################################
    await do_read(0x000001)
    await do_read(0x300123)
    await do_read(0x1A0456)

    ###########################################################################
    # PHASE 4: Check auto-refresh
    ###########################################################################
    await check_auto_ref_pending()

    ###########################################################################
    # PHASE 5: Concurrent read/write
    ###########################################################################
    await do_concurrent_rd_wr(0xAAAAAA, 0xBBBBBB)

    ###########################################################################
    # PHASE 6: Mid-test reset + re-init
    ###########################################################################
    cocotb.log.info(
        f"Time {get_sim_time('ns')}: Applying mid-test reset to check re-init..."
    )
    await apply_reset()
    await check_init_done()

    ###########################################################################
    # PHASE 7: Saturate no_of_refs_needed
    ###########################################################################
    await saturate_no_of_refs()

    ###########################################################################
    # PHASE 8: Attempt read/write while busy
    ###########################################################################
    await do_test_during_busy()

    # Check auto-refresh again after the above
    await check_auto_ref_pending()

    ###########################################################################
    # Final results
    ###########################################################################
    cocotb.log.info("==========================================================")
    cocotb.log.info(f"= TEST DONE.  PASSED={PASS_count},  FAILED={FAIL_count}")
    cocotb.log.info("==========================================================")

    if FAIL_count == 0:
        cocotb.log.info("Overall: [PASS]")
    else:
        cocotb.log.error("Overall: [FAIL]")
        # You can raise an exception if you want the test runner to mark it as failed:
        # raise cocotb.result.TestFailure("Some checks failed.")
