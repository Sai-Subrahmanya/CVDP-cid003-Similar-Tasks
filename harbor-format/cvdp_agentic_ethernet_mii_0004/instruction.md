Design a SystemVerilog RTL module named `ethernet_mii_tx.sv` in the `rtl` directory. Refer to the specification in `docs/tx_specification.md`, which defines an Ethernet transmitter compatible with the MII interface. The module must accept Ethernet frame data via an AXI-Stream interface and transmit it over a 4-bit MII data interface (`mii_txd_out`) along with an accompanying transmit enable signal (`mii_tx_en_out`).

The design must include:

1. FIFO logic for clock domain crossing (CDC) between the AXI-Stream and MII transmit domains. Use the existing FIFO module (`rtl/ethernet_fifo_cdc.sv`) to instantiate and integrate into the `ethernet_mii_tx` top module. The FIFO should support full-frame buffering of up to 1518 bytes and maintain synchronization across domains using dual-clock FIFO techniques.

2. TX logic to convert AXI data into MII format. This includes sending the preamble, start frame delimiter (SFD), payload, and CRC. The CRC must be calculated using the Ethernet CRC-32 polynomial with bit reversal as per standard Ethernet conventions. The transmit state must be managed with a finite state machine (FSM).



