// Decade Counter module (0-9)
module decade_counter (
    input wire clk,          // Clock input
    input wire rst_n,        // Active low reset
    input wire enable,       // Counter enable
    output reg [3:0] count,  // 4-bit counter output
    output wire tc          // Terminal count (high when count = 9)
);

    // Terminal count detection
    assign tc = (count == 4'd9) ? 1'b1 : 1'b0;

    // Counter logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            count <= 4'd0;   // Reset to 0
        end
        else if (enable) begin
            if (count == 4'd9)
                count <= 4'd0;   // Roll over to 0
            else
                count <= count + 1'b1;  // Increment
        end
    end

endmodule

