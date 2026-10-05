# Ethernet MII TX Module Specification Document

## Introduction

The **Ethernet MII TX Module** is responsible for transmitting Ethernet frames over the Media Independent Interface (MII). It accepts Ethernet payload data over a 32-bit AXI-stream interface and outputs serialized 4-bit MII data, compliant with IEEE 802.3 standards. The module autonomously handles Ethernet frame formatting, including preamble and start-of-frame delimiter (SFD) generation, payload serialization, and CRC-32 checksum calculation and appending. A dual-clock FIFO ensures safe and efficient clock domain crossing from the AXI-stream domain to the MII transmission domain.


## Functional Overview

### Frame Transmission

The module begins each frame with a 7-byte preamble (`0x55`) followed by a 1-byte SFD (`0xD5`). It then serializes the AXI-stream data payload into MII-compliant 4-bit nibbles (LSB first) and appends a computed 4-byte CRC. The entire frame is transmitted via the MII interface using the `mii_txd_out` and `mii_tx_en_out` signals.

### CRC Generation

The module uses a streaming CRC-32 generator compliant with IEEE 802.3. The CRC is calculated over the AXI payload data and transmitted at the end of each frame. The module performs per-byte bit reversal before CRC computation and final bit reversal and inversion before transmission.

### Clock Domain Crossing (CDC)

To decouple the AXI-stream interface from the MII interface, the module integrates a dual-clock FIFO. This FIFO buffers complete Ethernet frames and synchronizes data across independent clock domains, maintaining data integrity and flow control.


## Module Interface

```verilog
module ethernet_mii_tx (
    input               clk_in,           // MII Clock Input
    input               rst_in,           // Asynchronous reset for MII logic (Active HIGH)

    output [3:0]        mii_txd_out,      // MII 4-bit data output
    output              mii_tx_en_out,    // MII Transmit Enable signal (Active HIGH)

    input               axis_clk_in,      // AXI-Stream Clock Input
    input               axis_rst_in,      // AXI-Stream reset (Active HIGH)
    input               axis_valid_in,    // AXI-Stream valid signal (Active HIGH)
    input  [31:0]       axis_data_in,     // AXI-Stream data input
    input  [3:0]        axis_strb_in,     // AXI-Stream byte strobes
    input               axis_last_in,     // AXI-Stream end-of-frame indicator (Active HIGH)
    output              axis_ready_out    // AXI-Stream ready signal (Active HIGH)
);
```

### Port Descriptions

- **clk_in**: The input clock is synchronized with the MII interface.
- **rst_in**: Active-high reset signal for the MII domain.
- **mii_txd_out**: 4-bit MII transmit data output.
- **mii_tx_en_out**: Indicates valid data is being transmitted on the MII interface (Active HIGH).
- **axis_clk_in**: Clock for input AXI-stream interface.
- **axis_rst_in**: Active-high reset signal for the AXI-stream domain.
- **axis_valid_in**: Indicates that AXI-stream input data is valid (Active HIGH).
- **axis_data_in**: 32-bit AXI-stream input data.
- **axis_strb_in**: Byte-enable signals indicating valid bytes in the input word (Active HIGH).
- **axis_last_in**: Marks the last AXI-stream word in an Ethernet frame (Active HIGH).
- **axis_ready_out**: Indicates the module is ready to accept AXI-stream input data (Active HIGH).

## MII Interface (PHY Side)

The **`ethernet_mii_tx` module** is responsible for **converting Ethernet frame data received via an AXI-stream interface** into **MII-compatible transmit signals** that are sent to the physical layer (PHY). This includes not just payload serialization but also automatic preamble generation, CRC calculation, and correct signal timing for the MII interface.

**Frame Construction and Serialization**  
Once the MII side detects a complete frame in the FIFO, it begins building the MII transmission:

- **Preamble and SFD**:
  - The module first sends **7 bytes of `0x55`** as preamble and **1 byte of `0xD5`** as the Start Frame Delimiter (SFD).
  - Each byte is serialized into **two 4-bit nibbles**, sent **LSB (low nibble) first** over `mii_txd_out[3:0]`.

- **Payload Transmission**:
  - AXI input data (32-bit words) is unpacked into 8-bit bytes.
   - Each byte is split into two nibbles and transmitted over MII using the same nibble order (low nibble first).
   - Only valid bytes (based on `axis_strb_in`) are transmitted.
   - This continues until the last word, as marked by `axis_last_in`.

- **CRC Appending**:
   - While payload is being sent, a **CRC-32 checksum** is computed in parallel.
   - This uses the standard Ethernet polynomial and performs per-byte bit reversal before CRC computation.
   - After the last payload byte, the computed CRC is inverted, bit-reversed again, and transmitted as 4 additional bytes (8 nibbles) using the same serialization method.

- **Transmission Control (`mii_tx_en_out`)**:
   - `mii_tx_en_out` is asserted HIGH during transmission of:
     - The preamble
     - SFD
     - Payload
     - CRC
   - It is deasserted after the final CRC nibble is sent, signaling the **end of the frame** to the PHY.
   - While LOW, the MII interface is idle.

## AXI4-Stream Interface (User Side)

The AXI-Stream (AXIS) interface is a standard, unidirectional data bus optimized for high-speed streaming data. In the `ethernet_mii_tx` module, this interface is used to accept Ethernet frame data from upstream logic, which is then transmitted over the MII interface. The AXI and MII domains operate asynchronously and are connected via an internal FIFO for safe and lossless clock domain crossing.

- **axis_clk_in & axis_rst_in:**  
  These provide the clock and reset for the AXI-Stream domain. This domain is decoupled from the MII transmit clock, allowing the AXI-stream input to run at arbitrary speeds. The FIFO handles data synchronization between the two domains.
- **axis_valid_in:**  
  Asserted HIGH to indicate that a valid AXI-stream input word is present on `axis_data_in`, `axis_strb_in`, and `axis_last_in`. The data is accepted only when `axis_ready_out` is also HIGH, completing the handshake.

- **axis_data_in (32 bits):**  
  Carries up to 4 bytes of Ethernet frame payload data per clock cycle. The data is aligned to the least significant byte, and any unused bytes must be masked using the strobe input.

- **axis_strb_in (4 bits):**  
  Active HIGH. Byte strobe indicating which bytes in the 32-bit input word are valid. Each bit corresponds to one byte. This is especially important for the final word in a frame, which may contain fewer than 4 bytes.

- **axis_last_in:**  
  Asserted HIGH to indicate that the current data word is the last in the Ethernet frame. Used internally to trigger CRC generation and transition the MII transmit FSM to the end-of-frame sequence.

- **axis_ready_out:**  
  Active HIGH signal. Indicates that the module is ready to accept the next AXI-stream word. When deasserted, upstream logic must stall and wait. It is typically deasserted when the internal FIFO is full.

**Clock and Reset:**
- `axis_clk_in`: Clock signal for the AXI-stream interface (user domain).
- `axis_rst_in`: Asynchronous active-high reset for the AXI-stream side.

**Data Path:**
- `axis_data_in[31:0]`: 32-bit input data word (little-endian).
- `axis_strb_in[3:0]`: Byte strobes (1 = valid byte).
- `axis_valid_in`: Indicates the input word is valid.
- `axis_last_in`: Marks the final word of the frame.
- `axis_ready_out`: Indicates the module is ready to accept new input.

**Packet Format:**
- Data is aligned to the least significant byte (`axis_data_in[7:0]` is the first byte of the frame).
- Partial words at the end of a frame are indicated by `axis_strb_in`.
- CRC is not required or accepted on the AXI-stream interface; it is automatically calculated and appended by the module.

## Frame Structure

Each Ethernet frame transmitted via MII includes:

| Field                       | Length  | Description                         |
|-----------------------------|---------|-------------------------------------|
| Preamble                    | 7 bytes | 0x55 repeating pattern              |
| Start Frame Delimiter (SFD) | 1 byte  | 0xD5                                |
| Payload                     | N bytes | AXI-stream data                     |
| CRC                         | 4 bytes | IEEE 802.3 CRC32 (auto-appended)    |

- Payload length is determined dynamically by `axis_last_in` and `axis_strb_in`.
- CRC is computed automatically and inserted after the payload.

## CRC Calculation

### Polynomial Specification

Ethernet uses a 32-bit CRC (Cyclic Redundancy Check) defined by the following standard polynomial:

```
G(x) = x^32 + x^26 + x^23 + x^22 + x^16 + x^12 + x^11 +
       x^10 + x^8 + x^7 + x^5 + x^4 + x^2 + x^1 + 1
```

### Hardware-oriented LFSR Operation

- The CRC logic on the TX side is implemented using a 32-bit LFSR that updates its internal state based on incoming frame data bytes.
- Initially, at the start of each frame (after the SFD has been transmitted), the CRC register is initialized to all ones (`0xFFFFFFFF`).
- Each byte of the payload is sequentially fed into the CRC generator, which updates the internal CRC state. 
- The LFSR logic implements XOR feedback based on the polynomial taps, calculated combinatorially within one clock cycle for every byte processed.
- The internal CRC register continuously updates with each data byte until all payload bytes have been processed.

### CRC Byte Input Ordering and Bit Reversal

- Ethernet CRC logic assumes bitwise input **MSB-first**. However, Ethernet frames transmitted via MII interface carry data **LSB-first** at the bit-level. 
- Therefore, each byte from the AXI-stream input must be **bit-reversed** before being fed into the CRC logic.
- For example, input byte `0x2D (00101101)` is bit-reversed to `0xB4 (10110100)` before CRC computation.

### CRC Calculation Steps

#### 1. Initialization
- CRC register is initialized to `0xFFFFFFFF` at the start of each new Ethernet frame, immediately after the Start Frame Delimiter (SFD).

#### 2. Data Processing
- Every payload byte from the input data stream is processed sequentially:
  - Reverse the bits within each byte.
  - Feed the reversed byte into the CRC logic (`nextCRC32_D8` function) along with the current CRC register state.
  - Update the CRC register to the newly computed value within one clock cycle.

#### 3. Finalization
- After processing all payload bytes, perform a bitwise inversion (`~CRC`) of the CRC register's contents.
- The resulting 32-bit inverted CRC is transmitted immediately after the payload data as the Frame Check Sequence (FCS).

### CRC Transmission over MII

- After the last byte of payload is sent, the CRC transmission phase begins.
- The CRC is transmitted over the MII interface in little-endian nibble order:
  - The least significant nibble (bits `[3:0]`) of the CRC is transmitted first.
  - Each subsequent nibble is transmitted in ascending bit order, finishing with the most significant nibble of the CRC (bits `[31:28]`).
- The total CRC transmission duration is exactly 8 MII clock cycles (since CRC is 32 bits, transmitted 4 bits at a time).

### CRC Calculation Function (`nextCRC32_D8`)

The `nextCRC32_D8` function computes CRC for an 8-bit data input (bit-reversed) given the current CRC state, based on the standard Ethernet polynomial. This combinational function allows byte-wise CRC computation within one cycle:

```verilog
function [31:0] nextCRC32_D8;

input [7:0] Data;
input [31:0] crc;
logic [7:0] d;
logic [31:0] c;
logic [31:0] newcrc;
begin
    d = Data;
    c = crc;

    newcrc[0] = d[6] ^ d[0] ^ c[24] ^ c[30];
    newcrc[1] = d[7] ^ d[6] ^ d[1] ^ d[0] ^ c[24] ^ c[25] ^ c[30] ^ c[31];
    newcrc[2] = d[7] ^ d[6] ^ d[2] ^ d[1] ^ d[0] ^ c[24] ^ c[25] ^ c[26] ^ c[30] ^ c[31];
    newcrc[3] = d[7] ^ d[3] ^ d[2] ^ d[1] ^ c[25] ^ c[26] ^ c[27] ^ c[31];
    newcrc[4] = d[6] ^ d[4] ^ d[3] ^ d[2] ^ d[0] ^ c[24] ^ c[26] ^ c[27] ^ c[28] ^ c[30];
    newcrc[5] = d[7] ^ d[6] ^ d[5] ^ d[4] ^ d[3] ^ d[1] ^ d[0] ^ c[24] ^ c[25] ^ c[27] ^ c[28] ^ c[29] ^ c[30] ^ c[31];
    newcrc[6] = d[7] ^ d[6] ^ d[5] ^ d[4] ^ d[2] ^ d[1] ^ c[25] ^ c[26] ^ c[28] ^ c[29] ^ c[30] ^ c[31];
    newcrc[7] = d[7] ^ d[5] ^ d[3] ^ d[2] ^ d[0] ^ c[24] ^ c[26] ^ c[27] ^ c[29] ^ c[31];
    newcrc[8] = d[4] ^ d[3] ^ d[1] ^ d[0] ^ c[0] ^ c[24] ^ c[25] ^ c[27] ^ c[28];
    newcrc[9] = d[5] ^ d[4] ^ d[2] ^ d[1] ^ c[1] ^ c[25] ^ c[26] ^ c[28] ^ c[29];
    newcrc[10] = d[5] ^ d[3] ^ d[2] ^ d[0] ^ c[2] ^ c[24] ^ c[26] ^ c[27] ^ c[29];
    newcrc[11] = d[4] ^ d[3] ^ d[1] ^ d[0] ^ c[3] ^ c[24] ^ c[25] ^ c[27] ^ c[28];
    newcrc[12] = d[6] ^ d[5] ^ d[4] ^ d[2] ^ d[1] ^ d[0] ^ c[4] ^ c[24] ^ c[25] ^ c[26] ^ c[28] ^ c[29] ^ c[30];
    newcrc[13] = d[7] ^ d[6] ^ d[5] ^ d[3] ^ d[2] ^ d[1] ^ c[5] ^ c[25] ^ c[26] ^ c[27] ^ c[29] ^ c[30] ^ c[31];
    newcrc[14] = d[7] ^ d[6] ^ d[4] ^ d[3] ^ d[2] ^ c[6] ^ c[26] ^ c[27] ^ c[28] ^ c[30] ^ c[31];
    newcrc[15] = d[7] ^ d[5] ^ d[4] ^ d[3] ^ c[7] ^ c[27] ^ c[28] ^ c[29] ^ c[31];
    newcrc[16] = d[5] ^ d[4] ^ d[0] ^ c[8] ^ c[24] ^ c[28] ^ c[29];
    newcrc[17] = d[6] ^ d[5] ^ d[1] ^ c[9] ^ c[25] ^ c[29] ^ c[30];
    newcrc[18] = d[7] ^ d[6] ^ d[2] ^ c[10] ^ c[26] ^ c[30] ^ c[31];
    newcrc[19] = d[7] ^ d[3] ^ c[11] ^ c[27] ^ c[31];
    newcrc[20] = d[4] ^ c[12] ^ c[28];
    newcrc[21] = d[5] ^ c[13] ^ c[29];
    newcrc[22] = d[0] ^ c[14] ^ c[24];
    newcrc[23] = d[6] ^ d[1] ^ d[0] ^ c[15] ^ c[24] ^ c[25] ^ c[30];
    newcrc[24] = d[7] ^ d[2] ^ d[1] ^ c[16] ^ c[25] ^ c[26] ^ c[31];
    newcrc[25] = d[3] ^ d[2] ^ c[17] ^ c[26] ^ c[27];
    newcrc[26] = d[6] ^ d[4] ^ d[3] ^ d[0] ^ c[18] ^ c[24] ^ c[27] ^ c[28] ^ c[30];
    newcrc[27] = d[7] ^ d[5] ^ d[4] ^ d[1] ^ c[19] ^ c[25] ^ c[28] ^ c[29] ^ c[31];
    newcrc[28] = d[6] ^ d[5] ^ d[2] ^ c[20] ^ c[26] ^ c[29] ^ c[30];
    newcrc[29] = d[7] ^ d[6] ^ d[3] ^ c[21] ^ c[27] ^ c[30] ^ c[31];
    newcrc[30] = d[7] ^ d[4] ^ c[22] ^ c[28] ^ c[31];
    newcrc[31] = d[5] ^ c[23] ^ c[29];
    nextCRC32_D8 = newcrc;
end
endfunction
```

### Throughput and Timing

- One byte is processed every two MII clock cycles (since each byte is serialized into two 4-bit nibbles).
- CRC is updated in real-time while payload bytes are transmitted — no additional delay or buffering is needed.
- CRC calculation begins immediately after the SFD and continues until the last payload byte is processed.
- After that, the CRC is inverted, reversed, and transmitted over the next 4 bytes (8 clocks).

## Submodule: FIFO (ethernet_fifo_cdc)

The FIFO buffer is integrated into the `ethernet_mii_tx` module to safely transfer frame data from the AXI-stream input domain to the MII transmit domain. It provides a clean decoupling between the two asynchronous clock domains and ensures smooth, lossless streaming of Ethernet frames from user logic to the MAC transmission pipeline.

### FIFO Submodule Interface

```verilog
module ethernet_fifo_cdc (
    input                   wr_clk_i,       // FIFO write clock
    input                   wr_rst_i,       // FIFO write reset
    input                   wr_push_i,      // Write enable signal
    input  [WIDTH-1:0]      wr_data_i,      // Input data to FIFO
    output                  wr_full_o,      // FIFO full indicator

    input                   rd_clk_i,       // FIFO read clock
    input                   rd_rst_i,       // FIFO read reset
    input                   rd_pop_i,       // Read enable signal
    output [WIDTH-1:0]      rd_data_o,      // Output data from FIFO
    output                  rd_empty_o      // FIFO empty indicator
);
```

### Clock Domains

- **Write Domain (AXI Side)**:
  - `wr_clk_i`: Clock signal for writing data into the FIFO. Connected to `axis_clk_in` from the user system.
  - `wr_rst_i`: Asynchronous active-high reset for the write-side logic. Connected to `axis_rst_in`.

- **Read Domain (MII Side)**:
  - `rd_clk_i`: Clock signal for reading data from the FIFO. Connected to `clk_in`, the MII transmit clock.
  - `rd_rst_i`: Asynchronous active-high reset for the read-side logic. Connected to `rst_in`.

### Write Interface (AXI Domain)

- `wr_push_i`: Asserted HIGH to push a new word into the FIFO. Data is accepted only when the FIFO is not full (`wr_full_o` is LOW).
- `wr_data_i [WIDTH-1:0]`: Input data word to be stored in the FIFO. In the TX design, each word includes:
  - 32-bit Ethernet payload data
  - 4-bit byte strobe mask
  - 1-bit frame boundary flag (`axis_last_in`)
  Total width = 32 + 4 + 1 = 37 bits.
- `wr_full_o`: Asserted HIGH when the FIFO is full. When this is HIGH, `axis_ready_out` is deasserted to block further AXI input.

### Read Interface (MII Domain)

- `rd_pop_i`: Asserted HIGH to request a data word from the FIFO. Data is read when the FIFO is not empty, first when entering SFD transmission state then every time the transmitter is transmitting the last nibble of a previous 32-bit word. (Data read from the FIFO is stored and transmitted nibble by nibble in the TX module)
- `rd_data_o [WIDTH-1:0]`: Output data word from the FIFO, carrying Ethernet payload and metadata. Used directly by the MII transmit FSM for serialization and CRC calculation.
- `rd_empty_o`: Asserted HIGH when the FIFO is empty and there is no data available to transmit.

### Data Width and Depth

- The FIFO is parameterized to support a required data width (`WIDTH`) of 37 bits and a depth of 512 entries.
- This allows full buffering of complete Ethernet frames, including the maximum transmission unit (MTU) of 1518 bytes.
- Since each word carries 4 bytes of data, a complete MTU frame requires ~380 FIFO words. A 512-word depth ensures a safe margin for variable frame sizes and inter-frame delays.

### FIFO Integration in TX

In the `ethernet_mii_tx` module, the FIFO is used to buffer AXI input data before it is serialized and sent over the MII interface. Each word written into the FIFO includes:

- Frame payload data (32 bits)
- Byte-enable strobes (4 bits)
- End-of-frame flag (1 bit)

This information is used during MII transmission to:
- Determine how many bytes to send per AXI word
- Correctly handle partial words at the end of the frame
- Trigger the CRC generation and transmission process

### Data Word Format (`wr_data_i` / `rd_data_o`)

Each FIFO word is a 37-bit vector structured as follows:

| Bit Range | Width | Description                                       |
|-----------|--------|--------------------------------------------------|
| [31:0]    | 32     | AXI-stream payload data (up to 4 bytes)          |
| [35:32]   | 4      | Byte-enable strobes (`axis_strb_in`)             |
| [36]      | 1      | End-of-frame flag (`axis_last_in`)               |

- **Bits [31:0]**: Carry the actual Ethernet payload bytes, aligned to the least significant byte.
- **Bits [35:32]**: Indicate which bytes in the word are valid. Used to detect partial words and correctly terminate the frame.
- **Bit [36]**: Set HIGH on the last word of a frame. Used to initiate CRC generation and transition the internal transmit state machine.

## Data Validity and Frame Boundary Management

- The TX module accepts Ethernet frames via AXI-stream input interface (`axis_data_in`).
- AXI-stream byte strobes (`axis_strb_in`) indicate the valid bytes within each 32-bit data input word:
  - `axis_strb_in = 4'b1111`: All 4 bytes valid.
  - `axis_strb_in` values `4'b0111`, `4'b0011`, `4'b0001` represent partial last words with 3, 2, or 1 byte(s), respectively.
- The frame boundary is indicated by the `axis_last_in` signal. This signal is asserted alongside the final data word of each Ethernet frame.
- The internal logic ensures proper CRC calculation over exactly the valid bytes indicated by `axis_strb_in`.
- The module correctly handles frames of arbitrary length (minimum Ethernet frame 64 bytes to maximum Ethernet frame 1518 bytes) by following AXI stream signals and strobes accurately.

## Timing and Latency

- The latency from AXI-stream input to MII output primarily depends on:
  - The relative frequencies of AXI-stream and MII clock domains.
  - The TX path is fully pipelined, supporting continuous one-byte-per-cycle throughput on the MII side once the frame has started transmission.

## Constraints and Assumptions (TX Side)

- Input data strictly adheres to IEEE 802.3 Ethernet frame format (payload length, data alignment, AXI-stream strobes).
- AXI-stream and MII clock domains are asynchronous, managed safely by a dual-clock FIFO.
- AXI-stream does not include CRC. The Ethernet MII TX module generates and appends CRC automatically to transmitted frames.
- After MII Frame transmission is completed, it is required to add a 96-bit Inter-Frame Gap after each Ethernet frame transmission (24 MII clock cycles).
- TX module generates exactly 7 preamble bytes (`0x55`) followed immediately by a Start-of-Frame Delimiter byte (`0xD5`) at the start of each transmitted frame.
- Internal logic strictly maintains AXI-stream handshaking protocol:
  - Frame begins when valid data is received (`axis_valid_in = 1`).
  - Frame ends when `axis_last_in = 1` and the associated data word has been fully processed according to `axis_strb_in`.