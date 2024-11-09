// Testbench
module decade_counter_tb;
    // Test signals
    reg clk;
    reg rst_n;
    reg enable;
    wire [3:0] count;
    wire tc;

    // Counter instance
    decade_counter counter (
        .clk(clk),
        .rst_n(rst_n),
        .enable(enable),
        .count(count),
        .tc(tc)
    );

    // Clock generation (20ns period)
    initial begin
        $dumpfile("waveform.vcd");
        $dumpvars(0, decade_counter_tb);
        clk = 0;
        forever #10 clk = ~clk;
    end

    // Test stimulus
    initial begin
        // Initialize waveform dump


        // Initialize signals
        rst_n = 0;
        enable = 0;

        // Test Case 1: Reset Check
        #20;
        rst_n = 1;
        if (count !== 4'd0) begin
            $display("Error: Counter should be 0 after reset");
            $finish;
        end

        // Test Case 2: Basic Counting
        enable = 1;
        repeat(12) @(posedge clk); // Count through 0-9 and roll over
        if (count !== 4'd2) begin
            $display("Error: Counter should be 2 after 12 clocks");
            $finish;
        end

        // Test Case 3: Disable Check
        enable = 0;
        repeat(5) @(posedge clk);
        if (count !== 4'd2) begin
            $display("Error: Counter should maintain value when disabled");
            $finish;
        end

        // Test Case 4: Reset During Operation
        enable = 1;
        repeat(3) @(posedge clk);
        rst_n = 0;
        @(posedge clk);
        if (count !== 4'd0) begin
            $display("Error: Counter should reset to 0");
            $finish;
        end

        // Test Case 5: Terminal Count Check
        rst_n = 1;
        enable = 1;
        repeat(9) @(posedge clk);
        if (tc !== 1'b1) begin
            $display("Error: Terminal count should be high at count 9");
            $finish;
        end
        @(posedge clk);
        if (tc !== 1'b0) begin
            $display("Error: Terminal count should be low after rollover");
            $finish;
        end

        // Extended Test: Full Counting Sequence
        $display("Starting full sequence test...");
        rst_n = 1;
        enable = 1;
        repeat(20) begin
            @(posedge clk);
            $display("Time=%0d Count=%d TC=%b", $time, count, tc);
        end

        // Test Complete
        #20;
        $display("All tests completed successfully!");
        $finish;
    end

    // Monitor changes
    initial begin
        $monitor("Time=%0d rst_n=%b enable=%b count=%d tc=%b",
                 $time, rst_n, enable, count, tc);
    end

    // Timeout watchdog
    initial begin
        #2000;  // Timeout after 2000 time units
        $display("Error: Simulation timeout");
        $finish;
    end

    // Additional checking tasks
    always @(posedge clk) begin
        // Verify count never exceeds 9
        if (count > 4'd9) begin
            $display("Error: Counter exceeded maximum value of 9");
            $finish;
        end
    end

endmodule