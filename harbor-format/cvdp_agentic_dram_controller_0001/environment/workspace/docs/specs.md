## Overview

An SDRAM controller that manages DRAM initialization, auto-refresh, and read/write operations. It uses counters, state machines, and vector arithmetic (`incr_vec`/`dcr_vec`) to schedule commands and generate DRAM control signals (`addr`, `ba`, `clk`, `cke`, `cs`, `ras`, `cas`, `we`, `dqm`) based on defined timing parameters and external inputs.

The module implements an SDRAM controller that handles power-up initialization, periodic auto-refresh, and read/write command sequencing for a DRAM device. The design is fully parameterized to allow flexibility in timing, address width, and bank selection.

---

## Parameterization

- **del:** Delay counter width for 100 µs initialization and subsequent auto-refresh intervals.
- **len_auto_ref:** Width of the counter tracking pending auto-refresh cycles.
- **len_small:** Width of the small timing counter used to generate delays for `tRCD`, `tRP`, `tRFC`, etc.
- **addr_bits_to_dram:** Width of the DRAM address bus.
- **addr_bits_from_up:** Width of the upstream address input.
- **ba_bits:** Bank address width.

---

## Interfaces

### DRAM Pins

- **addr:** DRAM address output.
- **ba:** Bank address output.
- **clk:** DRAM clock (synchronized to `clk_in`).
- **cke:** Clock enable for DRAM.
- **cs_n, ras_n, cas_n, we_n:** DRAM command signals.
- **dqm:** Data mask signals.

### Clock and Reset

- **clk_in:** System clock input.
- **reset:** Synchronous reset.

### Upstream Control

- **addr_from_up:** Address input from external logic.
- **rd_n_from_up, wr_n_from_up:** Read and write control signals.
- **bus_term_from_up:** Bus termination signal.
- **dram_init_done:** Indicates completion of DRAM initialization.
- **dram_busy:** Indicates the controller is busy (e.g., during auto-refresh cycles).

---

## Detailed Functionality

### 1. Initialization Sequence

- **Step 1:** On reset, a 100 µs delay is generated using the delay counter (`delay_reg`). During this period, the controller issues either NOP or INHIBIT commands as required by the SDRAM power-up specification.
- **Step 2:** A PRECHARGE command is issued to precharge all banks.
- **Step 3:** Two AUTO-REFRESH commands are executed (each triggered after a delay interval, typically 7.81 µs) to properly refresh all cells.
- **Step 4:** The Mode Register is programmed with a predefined value (`mod_reg_val`). After a short wait (`tmrd` cycles), initialization is complete, and the signal **`dram_init_done`** is asserted.

### 2. Auto-Refresh Scheduling

Once initialized, the delay counter generates periodic 7.81 µs intervals. A saturating counter (`no_of_refs_needed`) counts the number of auto-refreshes required. When pending, the controller issues AUTO-REFRESH commands and decrements the counter.

### 3. Read/Write Operation

- **Write Operation:**
  - On a write request (`wr_n_from_up` low) and when the previous transaction is complete (`rd_wr_just_terminated` is 0), the controller first issues an ACTIVE command to open the corresponding row (using part of the upstream address for row and bank selection).
  - After a delay of `tRCD`, the WRITE command is issued with the lower bits used as the column address.

- **Read Operation:**
  - Similarly, on a read request (`rd_n_from_up` low), an ACTIVE command is issued to open the row, followed after `tRCD` by a READ command.
  - A separate CAS latency pipeline asserts a read-data ready signal (`rd_dat_from_dram_ready`) after the defined CAS delay, and later the read operation is terminated with a BURST TERMINATE command and a precharge.

### 4. Timing and Counters

- **Delay Counter (`delay_reg`):** Implements the 100 µs initialization delay and counts auto-refresh intervals.
- **Small Counter (`small_count`):** Provides delays for command timing (`tRCD`, `tRP`, `tRFC`).
- **Increment/Decrement Functions:** Custom functions (`incr_vec` and `dcr_vec`) manipulate vector counters, rolling over or saturating as required.

### 5. Command Bus & Signal Generation

- A 6-bit command bus encodes DRAM commands (`cs`, `ras`, `cas`, `we`, and two `dqm` bits).
- Output signals (`addr`, `ba`, `clk`, `cke`, `cs_n`, `ras_n`, `cas_n`, `we_n`, `dqm`) are driven based on the command bus state.
- The clock input (`clk_in`) is directly mapped to the output clock (`clk`).

### 6. Control and Edge Detection

- Edge detection circuits generate pulses (e.g., `wr_n_from_up_pulse`) based on upstream read/write signals to detect new requests.
- A busy signal (`dram_busy`) indicates the controller is processing auto-refresh cycles or otherwise occupied.

---

## Summary

The DRAM controller module provides robust DRAM initialization, periodic auto-refresh, and precise read/write command sequencing. Its parameterized design and internal timing counters enable flexible integration with various DRAM devices and system clock frequencies, ensuring reliable operation in page burst mode with minimal CPU intervention.