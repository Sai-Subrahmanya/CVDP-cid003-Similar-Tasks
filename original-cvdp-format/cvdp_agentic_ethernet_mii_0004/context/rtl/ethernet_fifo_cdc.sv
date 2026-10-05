// FIFO with separate read/write clocks, sized to hold full 1518-byte Ethernet frame
// 32-bit data width (4 bytes), so need at least 380 entries (1518 / 4)

module ethernet_fifo_cdc #(
    parameter WIDTH = 38,
    parameter DEPTH = 512,
    parameter ADDR_WIDTH = $clog2(DEPTH)
) (
    input                   wr_clk_i,       // FIFO write clock (MII domain)
    input                   wr_rst_i,       // FIFO write reset
    input                   wr_push_i,      // Write enable signal
    input  [WIDTH-1:0]      wr_data_i,      // Input data to FIFO
    output                  wr_full_o,      // FIFO full indicator

    input                   rd_clk_i,       // FIFO read clock (AXI domain)
    input                   rd_rst_i,       // FIFO read reset
    input                   rd_pop_i,       // Read enable signal
    output [WIDTH-1:0]      rd_data_o,      // Output data from FIFO
    output                  rd_empty_o      // FIFO empty indicator
);

    // Memory
    reg [WIDTH-1:0] mem [0:DEPTH-1];

    // Write side
    reg [ADDR_WIDTH:0] wr_ptr_q,wr_bin_q;
    wire [ADDR_WIDTH-1:0] wr_addr_w = wr_bin_q[ADDR_WIDTH-1:0];
    wire [ADDR_WIDTH:0] wr_ptr_next_w = wr_bin_q + 1'b1;
    integer i;
    wire [ADDR_WIDTH:0] wgray_next;   // Next write pointer in gray and binary code
    assign wgray_next = (wr_ptr_next_w>>1) ^ wr_ptr_next_w;    // Convert binary to gray code

    always @(posedge wr_clk_i or posedge wr_rst_i) begin
	if (wr_rst_i) begin
            wr_ptr_q <= 0;
            wr_bin_q <= 0;
            for (i = 0; i < DEPTH; i = i + 1)
                mem[i] <= {WIDTH{1'b0}};
        end
        else if (wr_push_i && !wr_full_o) begin
            mem[wr_addr_w] <= wr_data_i;
            {wr_bin_q, wr_ptr_q} <= {wr_ptr_next_w, wgray_next}; // assign memory address in binary and pointer in gray
        end
    end
    
    // Read side
    reg [ADDR_WIDTH:0] rd_ptr_q,rd_bin_q;
    wire [ADDR_WIDTH-1:0] rd_addr_w = rd_bin_q[ADDR_WIDTH-1:0];
    wire [ADDR_WIDTH:0] rd_ptr_next_w = rd_bin_q + 1'b1;
    wire [ADDR_WIDTH:0] rgray_next;
    
    assign rgray_next = (rd_bin_q>>1) ^ rd_bin_q;     // Convert binary to gray code

    reg [WIDTH-1:0] rd_data_r;
    always @(posedge rd_clk_i or posedge rd_rst_i) begin
        if (rd_rst_i) begin
            rd_ptr_q <= 0;
            rd_bin_q <= 0;
            rd_data_r <= 0;
        end else if (rd_pop_i && !rd_empty_o) begin
            rd_data_r <= mem[rd_addr_w];
            {rd_bin_q, rd_ptr_q} <= {rd_ptr_next_w, rgray_next}; // assign memory address in binary and pointer in gray
        end
    end
    assign rd_data_o = rd_data_r;

    // Cross-domain pointer sync
    reg [ADDR_WIDTH:0] wr_ptr_rdclk_1, wr_ptr_rdclk_2;
    reg [ADDR_WIDTH:0] rd_ptr_wrclk_1, rd_ptr_wrclk_2;

    always @(posedge rd_clk_i or posedge rd_rst_i) begin
        if (rd_rst_i) begin
            wr_ptr_rdclk_1 <= 0;
            wr_ptr_rdclk_2 <= 0;
        end else begin
            wr_ptr_rdclk_1 <= wr_ptr_q;
            wr_ptr_rdclk_2 <= wr_ptr_rdclk_1;
        end
    end

    always @(posedge wr_clk_i or posedge wr_rst_i) begin
        if (wr_rst_i) begin
            rd_ptr_wrclk_1 <= 0;
            rd_ptr_wrclk_2 <= 0;
        end else begin
            rd_ptr_wrclk_1 <= rd_ptr_q;
            rd_ptr_wrclk_2 <= rd_ptr_wrclk_1;
        end
    end

    // Full & empty detection
    assign wr_full_o = (wgray_next == {~rd_ptr_wrclk_2[ADDR_WIDTH:ADDR_WIDTH-1], rd_ptr_wrclk_2[ADDR_WIDTH-2:0]});
    assign rd_empty_o = (rgray_next == wr_ptr_rdclk_2);

endmodule