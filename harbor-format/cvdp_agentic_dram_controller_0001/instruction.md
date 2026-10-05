Design a `dramcntrl` module in SystemVerilog (filename: **dramcntrl.sv**) according to the specification detailed in `docs/specs.md`. The design must support DRAM initialization—including a 100 µs power-up delay, precharge, two auto-refresh cycles, and mode register programming—followed by normal read/write operations. Parameterize the module with:

- **del:** Delay counter width for initialization and auto-refresh.
- **len_auto_ref:** Width for the auto-refresh counter.
- **len_small:** Width for timing delays (tRCD, tRP, tRFC, etc.).
- **addr_bits_to_dram, addr_bits_from_up, ba_bits:** For DRAM and upstream addressing.

The controller must drive DRAM control signals (`addr`, `ba`, `clk`, `cke`, `cs_n`, `ras_n`, `cas_n`, `we_n`, `dqm`) via an internal FSM that sequences commands (`ACTIVE`, `READ`, `WRITE`, `BURST TERMINATE`, `PRECHARGE`, `AUTO-REFRESH`). After a defined CAS latency for read commands, it must generate a read-data-ready signal. Include functions for vector increment and decrement, proper reset handling, edge detection for new read/write requests, and auto-refresh scheduling with saturation logic.

Additionally, provide a comprehensive SystemVerilog testbench (filename: **dramcntrl_tb.sv**) aligned with the provided testbench code requirements. The testbench must:

- Generate a 100 MHz clock.
- Apply reset, verify initialization (`dram_init_done` asserted), and simulate basic write and read operations.
- Test concurrent read/write requests.
- Stress auto-refresh scheduling (including saturating the auto-refresh counter) and verify `dram_busy`.
- Force operations while busy and cover all branches of the RTL, ensuring 100% code coverage.

Provide complete RTL (`dramcntrl.sv`) and testbench (`dramcntrl_tb.sv`) code that simulates and validates all functionality together.

