`timescale 1ns / 1ps

module dramcntrl 
#(
    //==========================================================================
    // Parameters
    //==========================================================================
    parameter integer del               = 15, // for the delay counter width
    parameter integer len_auto_ref      = 10, // auto-refresh scheduling counter
    parameter integer len_small         = 8,  // small timings counter (tRCD, tRP, etc.)
    parameter integer addr_bits_to_dram = 13,
    parameter integer addr_bits_from_up = 24,
    parameter integer ba_bits           = 2
)
(
    //==========================================================================
    // Ports
    //==========================================================================

    // -- DRAM pins
    output reg [addr_bits_to_dram-1 : 0] addr,
    output reg [ba_bits-1 : 0]          ba,
    output reg                          clk,
    output reg                          cke,
    output reg                          cs_n,
    output reg                          ras_n,
    output reg                          cas_n,
    output reg                          we_n,
    output reg [1:0]                    dqm,

    // -- Clock and reset inputs
    input  wire                         clk_in,
    input  wire                         reset,

    // -- Interface from "up" to DRAM controller
    input  wire [addr_bits_from_up-1:0] addr_from_up,
    input  wire                         rd_n_from_up,
    input  wire                         wr_n_from_up,
    input  wire                         bus_term_from_up,
    output wire                         dram_init_done,
    output wire                         dram_busy
);

//
//=============================================================================
// Function Definitions: incr_vec and dcr_vec for different widths
//=============================================================================

function [del-1 : 0] incr_vec_15;
    input [del-1 : 0] s1;
    reg   [del-1 : 0] V, tb;
    integer i;
begin
    tb[0] = 1'b1;
    V     = s1;
    for (i = 1; i < del; i = i + 1) begin
        tb[i] = V[i-1] & tb[i-1];
    end
    for (i = 0; i < del; i = i + 1) begin
        if (tb[i] == 1'b1) V[i] = ~V[i];
    end
    incr_vec_15 = V;
end
endfunction

function [len_auto_ref-1 : 0] incr_vec_10;
    input [len_auto_ref-1 : 0] s1;
    reg   [len_auto_ref-1 : 0] V, tb;
    integer i;
begin
    tb[0] = 1'b1;
    V     = s1;
    for (i = 1; i < len_auto_ref; i = i + 1) begin
        tb[i] = V[i-1] & tb[i-1];
    end
    for (i = 0; i < len_auto_ref; i = i + 1) begin
        if (tb[i] == 1'b1) V[i] = ~V[i];
    end
    incr_vec_10 = V;
end
endfunction

function [len_small-1 : 0] incr_vec_8;
    input [len_small-1 : 0] s1;
    reg   [len_small-1 : 0] V, tb;
    integer i;
begin
    tb[0] = 1'b1;
    V     = s1;
    for (i = 1; i < len_small; i = i + 1) begin
        tb[i] = V[i-1] & tb[i-1];
    end
    for (i = 0; i < len_small; i = i + 1) begin
        if (tb[i] == 1'b1) V[i] = ~V[i];
    end
    incr_vec_8 = V;
end
endfunction

function [del-1 : 0] dcr_vec_15;
    input [del-1 : 0] s1;
    reg   [del-1 : 0] V, tb;
    integer i;
begin
    tb[0] = 1'b0;
    V     = s1;
    for (i = 1; i < del; i = i + 1) begin
        tb[i] = V[i-1] | tb[i-1];
    end
    for (i = 0; i < del; i = i + 1) begin
        if (tb[i] == 1'b0) V[i] = ~V[i];
    end
    dcr_vec_15 = V;
end
endfunction

function [len_auto_ref-1 : 0] dcr_vec_10;
    input [len_auto_ref-1 : 0] s1;
    reg   [len_auto_ref-1 : 0] V, tb;
    integer i;
begin
    tb[0] = 1'b0;
    V     = s1;
    for (i = 1; i < len_auto_ref; i = i + 1) begin
        tb[i] = V[i-1] | tb[i-1];
    end
    for (i = 0; i < len_auto_ref; i = i + 1) begin
        if (tb[i] == 1'b0) V[i] = ~V[i];
    end
    dcr_vec_10 = V;
end
endfunction

function [len_small-1 : 0] dcr_vec_8;
    input [len_small-1 : 0] s1;
    reg   [len_small-1 : 0] V, tb;
    integer i;
begin
    tb[0] = 1'b0;
    V     = s1;
    for (i = 1; i < len_small; i = i + 1) begin
        tb[i] = V[i-1] | tb[i-1];
    end
    for (i = 0; i < len_small; i = i + 1) begin
        if (tb[i] == 1'b0) V[i] = ~V[i];
    end
    dcr_vec_8 = V;
end
endfunction

//
//=============================================================================
// Internal Signals
//=============================================================================

// The "delay_reg" is 'del' bits wide
reg [del-1 : 0] delay_reg;

// For address and bank signals
reg [addr_bits_to_dram-1 : 0] addr_sig;
reg [ba_bits-1 : 0]           ba_sig;

// DRAM init done signals
reg dram_init_done_s;
reg dram_init_done_s_del;
reg reset_del_count;

// Scheduling auto‑ref
reg [len_auto_ref-1 : 0] no_of_refs_needed;
reg one_auto_ref_time_done;
reg one_auto_ref_complete;
reg auto_ref_pending;

// For small timing counters
reg [len_small-1 : 0] small_count;
reg small_all_zeros;

// Delayed wr_n signals to detect pulses
reg wr_n_from_up_del_1;
reg wr_n_from_up_del_2;
wire wr_n_from_up_pulse;  // purely combinational

// Control signals
reg rd_wr_just_terminated;
reg dram_busy_sig;

// Command bus [5:0]: bit5=cs, bit4=ras, bit3=cas, bit2=we, bit1=dqm(1), bit0=dqm(0)
reg [5:0] command_bus;

// 
//=============================================================================
// Localparams for constants
//=============================================================================
localparam [11:0] mod_reg_val  = 12'b000000100111; //  "000000100111"
localparam integer sd_init     = 10000;            // = 1000 * freq(100MHz) => ~100us
localparam integer trp         = 4;                // = ~20ns
localparam integer trfc        = 8;                // = ~66ns
localparam integer tmrd        = 3;                // wait after mode reg load
localparam integer trcd        = 2;                // ~15ns
localparam integer auto_ref_co = 780;              // ~7.81us at 100MHz

// Command patterns
localparam [5:0] inhibit         = 6'b111111;
localparam [5:0] nop             = 6'b011111;
localparam [5:0] active          = 6'b001111;
localparam [5:0] read_cmd        = 6'b010100;  
localparam [5:0] write_cmd       = 6'b010000;  
localparam [5:0] burst_terminate = 6'b011011;
localparam [5:0] precharge       = 6'b001011;
localparam [5:0] auto_ref_cmd    = 6'b000111;
localparam [5:0] load_mode_reg   = 6'b000011;
localparam [5:0] rd_wr_in_prog   = 6'b011100;  // command bus for ongoing RD/WR

//=============================================================================
// Main always blocks
//=============================================================================

// init_delay_reg:
//      increments a counter for 100 us during initialization,
//      then used for auto-ref scheduling (7.81 us).
//
always @(posedge clk_in) begin
    if (reset == 1'b1) begin
        delay_reg              <= {del{1'b0}};
        one_auto_ref_time_done <= 1'b0;
    end 
    else begin
        if (reset_del_count == 1'b1) begin
            delay_reg <= {del{1'b0}};
        end
        // once dram_init_done_s_del is '1', we track the 7.81 us intervals
        else if (dram_init_done_s_del == 1'b1) begin
            if ($unsigned(delay_reg) == auto_ref_co) begin
                delay_reg              <= {del{1'b0}};
                one_auto_ref_time_done <= 1'b1;
            end 
            else begin
                delay_reg              <= incr_vec_15(delay_reg);
                one_auto_ref_time_done <= 1'b0;
            end
        end
        else begin
            // still in initialization or counting up to init
            delay_reg              <= incr_vec_15(delay_reg);
            one_auto_ref_time_done <= 1'b0;
        end
    end
end

//
// init_auto_ref_count_reg:
//      Keeps track of how many auto-refs we still need to do.
//      This is the "typical" Verilog style without overshadowing assignments.
//
always @(posedge clk_in) begin
    if (reset == 1'b1) begin
        no_of_refs_needed <= {len_auto_ref{1'b0}};
    end 
    else begin
        // Only do increment/decrement if we have finished initialization
        if (dram_init_done_s == 1'b1) begin
            // saturate at all 1s if you want that behavior
            if (no_of_refs_needed == {len_auto_ref{1'b1}}) begin
                // remain saturated
                no_of_refs_needed <= no_of_refs_needed;
            end
            else begin
                // If we detect the 7.81us mark, increment
                if (one_auto_ref_time_done == 1'b1) begin
                    no_of_refs_needed <= incr_vec_10(no_of_refs_needed);
                end
                // If an auto-ref just finished, decrement
                else if (one_auto_ref_complete == 1'b1) begin
                    no_of_refs_needed <= dcr_vec_10(no_of_refs_needed);
                end
                else begin
                    // no change
                    no_of_refs_needed <= no_of_refs_needed;
                end
            end
        end
        else begin
            // still 0 until init completes
            no_of_refs_needed <= no_of_refs_needed;
        end
    end
end

//
// init_reg:
//      - SDRAM initialization steps
//      - normal read/write commands
//      - burst terminate & precharge
//      - auto-refresh
//
always @(posedge clk_in) begin
    if (reset == 1'b1) begin
        dram_init_done_s      <= 1'b0;
        command_bus           <= inhibit;
        one_auto_ref_complete <= 1'b0;
        rd_wr_just_terminated <= 1'b0;
        addr_sig              <= {addr_bits_to_dram{1'b0}};
        ba_sig                <= {ba_bits{1'b0}};
    end
    else begin
        //==========================================================
        // STILL IN INITIALIZATION PHASE
        //==========================================================
        if (dram_init_done_s == 1'b0) begin
            // Wait for ~100us => sd_init cycles
            if      ($unsigned(delay_reg) == sd_init) begin
                command_bus           <= precharge;
                // A10=1 => precharge all
                addr_sig              <= {addr_bits_to_dram{1'b0}};
                addr_sig[10]          <= 1'b1; 
            end
            else if ($unsigned(delay_reg) == (sd_init + trp)) begin
                command_bus           <= auto_ref_cmd;
            end
            else if ($unsigned(delay_reg) == (sd_init + trp + trfc)) begin
                command_bus           <= auto_ref_cmd;
            end
            else if ($unsigned(delay_reg) == (sd_init + trp + 2*trfc)) begin
                command_bus           <= load_mode_reg;
                // load mode reg => place mod_reg_val in addr[11:0]
                addr_sig              <= {addr_bits_to_dram{1'b0}};
                addr_sig[11:0]        <= mod_reg_val;
            end
            else if ($unsigned(delay_reg) == (sd_init + trp + 2*trfc + tmrd)) begin
                dram_init_done_s      <= 1'b1;
                command_bus           <= nop;
            end
            else begin
                command_bus           <= nop;
            end
        end
        //==========================================================
        // NORMAL OPERATION
        //==========================================================
        else begin
            //-------------------------
            // DRAM WRITE request
            //-------------------------
            if ((wr_n_from_up == 1'b0) && (rd_wr_just_terminated == 1'b0)) begin
                // Detect a "new" falling edge from idle => wr request
                if (wr_n_from_up_del_1 == 1'b1) begin
                    ba_sig      <= addr_from_up[23:22];
                    command_bus <= active;
                    // row address => 21:9
                    addr_sig    <= addr_from_up[21:9];
                end
                // after tRCD cycles, issue WRITE
                else if (small_count == trcd[len_small-1:0]) begin
                    ba_sig      <= addr_from_up[23:22];
                    command_bus <= write_cmd;
                    // col address => 8:0
                    addr_sig[8:0] <= addr_from_up[8:0];
                end
                else begin
                    // stay in read/write in progress => dqm=00
                    command_bus <= rd_wr_in_prog;
                end
            end

            //-------------------------
            // DRAM READ request
            //-------------------------
            else if ((rd_n_from_up == 1'b0) && (rd_wr_just_terminated == 1'b0)) begin
                if (wr_n_from_up_del_1 == 1'b1) begin
                    ba_sig      <= addr_from_up[23:22];
                    command_bus <= active;
                    addr_sig    <= addr_from_up[21:9];
                end
                else if (small_count == trcd[len_small-1:0]) begin
                    command_bus <= read_cmd;
                    addr_sig[8:0] <= addr_from_up[8:0];
                end
                else begin
                    command_bus <= rd_wr_in_prog;
                end
            end

            //-------------------------
            // Burst Terminate when 
            // read/write finishes
            //-------------------------
            else if (((wr_n_from_up == 1'b1) || (rd_n_from_up == 1'b1)) &&
                     (wr_n_from_up_del_1 == 1'b0)) begin
                command_bus           <= burst_terminate;
                rd_wr_just_terminated <= 1'b1;
            end

            //-------------------------
            // Precharge after 
            // read/write completes
            //-------------------------
            else if (rd_wr_just_terminated == 1'b1) begin
                // after 1 cycle, issue precharge
                if (small_count == 1) begin
                    ba_sig      <= addr_from_up[23:22];
                    command_bus <= precharge;
                end
                // after tRP cycles, done
                else if (small_count == trp[len_small-1:0]) begin
                    command_bus           <= nop;
                    rd_wr_just_terminated <= 1'b0;
                end
                else begin
                    command_bus <= nop;
                end
            end

            //-------------------------
            // AUTO-REFRESH 
            //-------------------------
            else if (auto_ref_pending == 1'b1) begin
                // if small_count=0 => issue auto_ref
                if (small_all_zeros == 1'b1) begin
                    command_bus           <= auto_ref_cmd;
                    one_auto_ref_complete <= 1'b0;
                end
                // after tRFC cycles => done
                else if (small_count == trfc[len_small-1:0]) begin
                    command_bus           <= nop;
                    one_auto_ref_complete <= 1'b1;
                end
                else begin
                    command_bus           <= nop;
                    one_auto_ref_complete <= 1'b0;
                end
            end
            else begin
                // idle
                command_bus <= nop;
            end
        end
    end
end

//
// reset_del_count_gen_reg:
//      used to generate a pulse on reset_del_count
//      when dram_init_done_s goes from 0 -> 1
//
always @(posedge clk_in) begin
    if (reset == 1'b1) begin
        dram_init_done_s_del <= 1'b0;
    end 
    else begin
        dram_init_done_s_del <= dram_init_done_s;
    end
end

// combinational pulse
always @(*) begin
    reset_del_count = dram_init_done_s & (~dram_init_done_s_del);
end

//
// gen_auto_ref_pending_cmb:
//      sets auto_ref_pending=1 if no_of_refs_needed != 0
//
always @(*) begin
    if (no_of_refs_needed == {len_auto_ref{1'b0}}) 
        auto_ref_pending = 1'b0;
    else
        auto_ref_pending = 1'b1;
end

//
// small_count_reg:
//      timing counter for tRCD, tRP, tRFC, etc.
//      resets on certain triggers
//
always @(posedge clk_in or posedge reset) begin
    if (reset == 1'b1) begin
        small_count <= {len_small{1'b0}};
    end 
    else begin
        integer i;
        reg all_ones;
        all_ones = small_count[0];
        for (i = 1; i < len_small; i = i + 1) begin
            all_ones = all_ones & small_count[i];
        end

        // Reset small_count on these conditions:
        if (
           // after a read/write + precharge is done
           ((one_auto_ref_time_done == 1'b1) && (wr_n_from_up == 1'b1) && (rd_n_from_up == 1'b1)) ||
           ((one_auto_ref_complete   == 1'b1) && (wr_n_from_up == 1'b1) && (rd_n_from_up == 1'b1)) ||
           ((wr_n_from_up_del_1     == 1'b0) && (rd_n_from_up == 1'b1) && (wr_n_from_up == 1'b1)) ||
           (wr_n_from_up_pulse == 1'b1) ||
           ((small_count == trp[len_small-1:0]) && (rd_wr_just_terminated == 1'b1))
          )
        begin
            small_count <= {len_small{1'b0}};
        end 
        else if (all_ones == 1'b1) begin
            // saturate
            small_count <= small_count;
        end 
        else begin
            // increment
            small_count <= incr_vec_8(small_count);
        end
    end
end

//
// gen_small_all_zeros_cmb:
//      asserts small_all_zeros=1 if small_count==0
//
always @(*) begin
    integer i;
    reg any_bit;
    any_bit = small_count[0];
    for (i = 1; i < len_small; i = i + 1) begin
        any_bit = any_bit | small_count[i];
    end
    small_all_zeros = ~any_bit;
end

//
// wr_n_from_up_del_reg:
//      used to produce pulses on wr_n_from_up 
//      for read/write requests (detect falling edge from (1,1))
// 
always @(posedge clk_in) begin
    // We combine wr_n_from_up & rd_n_from_up => 
    // "both high means idle or no request"
    wr_n_from_up_del_1 <= wr_n_from_up & rd_n_from_up;
    wr_n_from_up_del_2 <= wr_n_from_up_del_1;
end

// falling edge detect for wr_n_from_up & rd_n_from_up
assign wr_n_from_up_pulse = (~(wr_n_from_up & rd_n_from_up)) & (wr_n_from_up_del_1);

//
// dram_busy_gen:
//      Asserts dram_busy if auto-refs are pending
//      and no read/write is in progress
//
always @(posedge clk_in) begin
    if (reset == 1'b1) begin
        dram_busy_sig <= 1'b0;
    end 
    else begin
        // If we have pending auto-refs and the bus is idle
        if ((no_of_refs_needed != {len_auto_ref{1'b0}}) && 
            (wr_n_from_up_del_1 == 1'b0) &&
            (rd_n_from_up == 1'b1) && (wr_n_from_up == 1'b1)) 
        begin
            dram_busy_sig <= 1'b1;
        end 
        // If a new read/write request arrives, we drop busy
        else if ((no_of_refs_needed != {len_auto_ref{1'b0}}) &&
                 ((wr_n_from_up == 1'b0) || (rd_n_from_up == 1'b0))) 
        begin
            dram_busy_sig <= 1'b0;
        end
        // If no refs needed, not busy
        else if (no_of_refs_needed == {len_auto_ref{1'b0}}) begin
            dram_busy_sig <= 1'b0;
        end
        else begin
            dram_busy_sig <= 1'b1;
        end
    end
end

//
// cke_gen_reg:
//       cke = 1 after reset deasserts
//
always @(posedge clk_in) begin
    if (reset == 1'b1) begin
        cke <= 1'b0;
    end 
    else begin
        cke <= 1'b1;
    end
end

//
//=============================================================================
// Final Output Assignments
//=============================================================================

// Clock out
always @(*) begin
    clk = clk_in;
end

// From command_bus => chip selects, addresses, etc.
always @(*) begin
    cs_n  = command_bus[5];
    ras_n = command_bus[4];
    cas_n = command_bus[3];
    we_n  = command_bus[2];
    dqm   = command_bus[1:0];
end

// DRAM address and bank
always @(*) begin
    ba   = ba_sig;
    addr = addr_sig;
end

// Signals to "up"
assign dram_init_done        = dram_init_done_s;
assign dram_busy             = dram_busy_sig;

endmodule
