import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge, FallingEdge, ClockCycles
import zlib
import random

# ---------------------------------------------------------------
# Reference CRC calculation
# ---------------------------------------------------------------
def calculate_ethernet_crc(data: bytes) -> list[int]:
    """Calculate Ethernet CRC32 (as sent on MII, i.e., ~zlib.crc32(data)), little-endian"""
    raw_crc = zlib.crc32(data) ^ 0xFFFFFFFF  # Ethernet CRC
    transmitted_crc = ~raw_crc & 0xFFFFFFFF  # Invert again to match what DUT sends
    return list(transmitted_crc.to_bytes(4, 'little'))

# ---------------------------------------------------------------
# MII Monitor: Capture TX_EN, MII_TXD and reconstruct bytes
# ---------------------------------------------------------------
async def monitor_mii_output(dut, axi_payload: bytes, max_cycles=3000):
    print("\nMII Output (TX_EN=1):")

    nibble_buffer = []
    received_bytes = []

    for cycle in range(max_cycles):
        await RisingEdge(dut.clk_in)
        if int(dut.mii_tx_en_out.value) == 1:
            nibble = int(dut.mii_txd_out.value)
            nibble_buffer.append(nibble)
            # Combine every 2 nibbles into a full byte
            if len(nibble_buffer) % 2 == 0:
                lsn = nibble_buffer[-2]
                msn = nibble_buffer[-1]
                byte = (msn << 4) | lsn
                received_bytes.append(byte)

    # ----------------------------
    # Compare Preamble and SFD
    # ----------------------------
    # Expected preamble: 7 bytes of 0x55; expected SFD: 0xD5
    expected_preamble = [0x55] * 7
    expected_sfd = 0xD5

    received_preamble = received_bytes[0:7]
    received_sfd = received_bytes[7]

    assert received_preamble == expected_preamble, (
        f"Preamble mismatch!\n  Received: {', '.join(f'0x{b:02X}' for b in received_preamble)}\n"
        f"  Expected: {', '.join(f'0x{b:02X}' for b in expected_preamble)}"
    )
    assert received_sfd == expected_sfd, (
        f"SFD mismatch!\n  Received: 0x{received_sfd:02X}\n  Expected: 0x{expected_sfd:02X}"
    )
    print("Preamble and SFD verified: Received preamble and SFD match expected values.")

    # ----------------------------
    # Extract Payload and CRC
    # ----------------------------
    # Skip the first 8 bytes (7 preamble bytes + 1 SFD byte)
    start_index = 8  
    payload_len = len(axi_payload)

    received_payload = received_bytes[start_index:start_index + payload_len]
    received_crc     = received_bytes[start_index + payload_len : start_index + payload_len + 4]

    # Calculate reference CRC based on the AXI payload
    ref_crc = calculate_ethernet_crc(axi_payload)

    # Format results for printing
    axi_print     = ', '.join(f'0x{b:02X}' for b in axi_payload)
    mii_print     = ', '.join(f'0x{b:02X}' for b in received_payload)
    dut_crc_print = ', '.join(f'0x{b:02X}' for b in received_crc)
    ref_crc_print = ', '.join(f'0x{b:02X}' for b in ref_crc)

    # Assert that the received payload exactly matches the AXI payload.
    assert bytes(received_payload) == axi_payload, (
        f"Data mismatch!\n  MII Payload: {mii_print}\n  AXI Payload: {axi_print}"
    )
    print("Payload match verified: MII payload matches transmitted AXI payload.")

    # Assert that the received CRC matches the reference CRC.
    assert received_crc == ref_crc, (
        f"CRC mismatch!\n  DUT: {dut_crc_print}\n  REF: {ref_crc_print}"
    )
    print("CRC match verified: DUT CRC matches reference CRC.")

    # Print additional summary if both pass
    print("\nPass Summary:")
    print("AXI Data:    ", axi_print)
    print("MII Data:    ", mii_print)
    print("DUT CRC:     ", dut_crc_print)
    print("Ref CRC:     ", ref_crc_print)

async def run_payload_test(dut, payload: bytes):
    """Drive AXI with given payload and monitor MII output and CRC"""
    
    # Restart clocks if needed
    cocotb.start_soon(Clock(dut.clk_in, 20, unit="ns").start())
    cocotb.start_soon(Clock(dut.axis_clk_in, 20, unit="ns").start())

    # Reset DUT
    dut.rst_in.value = 1
    dut.axis_rst_in.value = 1
    dut.axis_valid_in.value = 0
    dut.axis_last_in.value = 0
    await ClockCycles(dut.clk_in, 4)
    dut.rst_in.value = 0
    dut.axis_rst_in.value = 0
    await RisingEdge(dut.axis_clk_in)

    # Start monitor
    monitor_task = cocotb.start_soon(monitor_mii_output(dut, payload, max_cycles=6000))

    # Drive AXI payload
    for i in range(0, len(payload), 4):
        word = payload[i:i+4]
        padded = word + bytes(4 - len(word))
        strb = (1 << len(word)) - 1

        dut.axis_data_in.value = int.from_bytes(padded, 'little')
        dut.axis_strb_in.value = strb
        dut.axis_last_in.value = 1 if (i + 4) >= len(payload) else 0
        dut.axis_valid_in.value = 1

        while not dut.axis_ready_out.value:
            await RisingEdge(dut.axis_clk_in)
        await RisingEdge(dut.axis_clk_in)
        dut.axis_valid_in.value = 0

    # Wait for MII TX
    await FallingEdge(dut.mii_tx_en_out)

    # Await monitor
    await monitor_task

# ---------------------------------------------------------------
# Test 1: Ethernet Payload (64 bytes), Incremental Data
# ---------------------------------------------------------------
@cocotb.test()
async def test_tx_64byte_payload(dut):
    payload = bytes(range(64))
    await run_payload_test(dut, payload)

# ---------------------------------------------------------------
# Test 2: Max Ethernet Payload (1518 bytes), Incremental Data
# ---------------------------------------------------------------
@cocotb.test()
async def test_max_payload_incremental(dut):
    payload = bytes(i % 256 for i in range(1518))
    await run_payload_test(dut, payload)

# ---------------------------------------------------------------
# Test 3: Fixed-Length Random Data (512 bytes)
# ---------------------------------------------------------------
@cocotb.test()
async def test_fixed_length_random_data(dut):
    payload = bytes(random.getrandbits(8) for _ in range(512))
    await run_payload_test(dut, payload)

# ---------------------------------------------------------------
# Test 4: Random Length (64–1518), Incremental Data
# ---------------------------------------------------------------
@cocotb.test()
async def test_random_length_incremental(dut):
    length = random.randint(64, 1518)
    payload = bytes(i % 256 for i in range(length))
    await run_payload_test(dut, payload)

# ---------------------------------------------------------------
# Test 5: Random Length + Random Data (64–1518)
# ---------------------------------------------------------------
@cocotb.test()
async def test_random_length_random_data(dut):
    length = random.randint(64, 1518)
    payload = bytes(random.getrandbits(8) for _ in range(length))
    await run_payload_test(dut, payload)

# ---------------------------------------------------------------
# Helper: Send a single frame on AXI with out reset between frames
# ---------------------------------------------------------------
async def send_frame(dut, payload: bytes):
    """Send a single frame (payload on AXI) in 4-byte chunks and print debug info."""
    for i in range(0, len(payload), 4):
        word = payload[i:i+4]
        padded = word + bytes(4 - len(word))
        strb = (1 << len(word)) - 1

        # Convert the padded bytes into an integer (little-endian)
        data_int = int.from_bytes(padded, 'little')

        # Drive signals to DUT
        dut.axis_data_in.value = data_int
        dut.axis_strb_in.value = strb
        dut.axis_last_in.value = 1 if (i + 4) >= len(payload) else 0
        dut.axis_valid_in.value = 1

        # Wait until DUT indicates ready
        while not dut.axis_ready_out.value:
            await RisingEdge(dut.axis_clk_in)
        await RisingEdge(dut.axis_clk_in)

        # Deassert valid and last signals
        dut.axis_valid_in.value = 0
        dut.axis_last_in.value = 0

    # Optionally flush signals at end of frame.
    dut.axis_data_in.value = 0
    dut.axis_strb_in.value = 0

# ---------------------------------------------------------------
# Test: Send n Back-to-Back Frames with Programmable Payload Length
# ---------------------------------------------------------------
@cocotb.test()
async def test_back_to_back_frames_constant(dut):
    # Configure the number of frames and payload length (same payload for all frames)
    num_frames = 5         # Number of frames
    payload_length = 128   # Payload length in bytes

    # Create a constant payload, e.g., bytes [0, 1, 2, ..., 127]
    payload = bytes(range(payload_length))

    # Setup clocks and reset DUT once
    cocotb.start_soon(Clock(dut.clk_in, 20, unit="ns").start())
    cocotb.start_soon(Clock(dut.axis_clk_in, 20, unit="ns").start())
    dut.rst_in.value = 1
    dut.axis_rst_in.value = 1
    dut.axis_valid_in.value = 0
    dut.axis_last_in.value = 0
    await ClockCycles(dut.clk_in, 4)
    dut.rst_in.value = 0
    dut.axis_rst_in.value = 0
    await RisingEdge(dut.axis_clk_in)

    # Loop: Send and verify each frame individually
    for idx in range(num_frames):
        print(f"\nTransmitting Frame {idx+1} of {num_frames}")

        monitor_task = cocotb.start_soon(monitor_mii_output(dut, payload, max_cycles=6000))
        await RisingEdge(dut.axis_clk_in)
        await send_frame(dut, payload)
        # Wait for TX to complete: detect falling edge of mii_tx_en_out, then add a short delay
        await FallingEdge(dut.mii_tx_en_out)
        await ClockCycles(dut.clk_in, 10)
        await monitor_task
        # Insert an additional idle period between frames to flush any residual signals
        await ClockCycles(dut.clk_in, 10)

    print("\nBack-to-back constant frame test PASSED for all frames.")


# ---------------------------------------------------------------
# Test: Send n Back-to-Back Frames with Programmable (Random) Payload
# ---------------------------------------------------------------
@cocotb.test()
async def test_back_to_back_frames_random(dut):
    # Configure the number of frames and payload length
    num_frames = 5         # Number of frames
    payload_length = 256    # Payload length in bytes

    # Setup clocks and reset DUT once
    cocotb.start_soon(Clock(dut.clk_in, 20, unit="ns").start())
    cocotb.start_soon(Clock(dut.axis_clk_in, 20, unit="ns").start())
    dut.rst_in.value = 1
    dut.axis_rst_in.value = 1
    dut.axis_valid_in.value = 0
    dut.axis_last_in.value = 0
    await ClockCycles(dut.clk_in, 4)
    dut.rst_in.value = 0
    dut.axis_rst_in.value = 0
    await RisingEdge(dut.axis_clk_in)

    # Loop: For each frame, generate a random payload and send/verify it.
    for idx in range(num_frames):
        # Generate a random payload of defined length
        payload = bytes(random.getrandbits(8) for _ in range(payload_length))
        print(f"\nTransmitting Frame {idx+1} of {num_frames}")
        
        monitor_task = cocotb.start_soon(monitor_mii_output(dut, payload, max_cycles=6000))
        await RisingEdge(dut.axis_clk_in)
        await send_frame(dut, payload)
        # Wait for TX to complete: detect falling edge of mii_tx_en_out, then add a short delay
        await FallingEdge(dut.mii_tx_en_out)
        await ClockCycles(dut.clk_in, 10)
        await monitor_task
        # Insert an additional idle period between frames to flush residual signals.
        await ClockCycles(dut.clk_in, 10)

    print("\nBack-to-back random frame test PASSED for all frames.")
