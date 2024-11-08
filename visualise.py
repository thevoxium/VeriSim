import os
import re
import subprocess

import plotly.graph_objects as go
import streamlit as st
import vcdvcd
from plotly.subplots import make_subplots
from streamlit_ace import st_ace


def configure_page():
    st.set_page_config(
        page_title="Verilog Simulator",
        layout="wide",
        initial_sidebar_state="collapsed"
    )
    
    st.markdown("""
        <style>
        .stApp {
            max-width: 100%;
        }
        .main {
            padding: 2rem;
        }
        .ace-editor-container {
            border-radius: 4px;
            margin-bottom: 1rem;
        }
        </style>
    """, unsafe_allow_html=True)

def inject_vcd_commands(test_code):
    """
    Injects VCD dump commands into the testbench code if they're not already present.
    """
    # Check if VCD commands already exist
    if "$dumpfile" in test_code and "$dumpvars" in test_code:
        return test_code
    
    # Find the module name
    module_pattern = r'\bmodule\s+(\w+)\s*[;(]'
    match = re.search(module_pattern, test_code)
    module_name = match.group(1) if match else "test"
    
    # Find the first initial block
    initial_pattern = r'(\s*initial\s*begin\s*\n)'
    
    if re.search(initial_pattern, test_code):
        # Add VCD commands after the first initial begin
        modified_code = re.sub(
            initial_pattern,
            f'\\1        $dumpfile("waveform.vcd");\n        $dumpvars(0, {module_name});\n',
            test_code,
            count=1
        )
    else:
        # If no initial block exists, add one with VCD commands
        # Find the module content start
        module_start = re.search(r'module.*?[;)]', test_code)
        if module_start:
            insert_pos = module_start.end()
            modified_code = (
                test_code[:insert_pos] +
                f"\n\n    // Auto-inserted VCD dump commands\n    initial begin\n" +
                f"        $dumpfile(\"waveform.vcd\");\n        $dumpvars(0, {module_name});\n    end\n" +
                test_code[insert_pos:]
            )
        else:
            modified_code = test_code
    
    return modified_code

def visualize_vcd(vcd_file_path):
    """
    Visualize signals from VCD file with improved styling
    """
    try:
        vcd = vcdvcd.VCDVCD(vcd_file_path)
        signals = list(vcd.references_to_ids.keys())
        
        if not signals:
            st.error("No signals found in the VCD file.")
            return None
        
        fig = make_subplots(
            rows=len(signals),
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.05,
            subplot_titles=[s.replace("_tb", "") for s in signals]
        )
        
        colors = ['#2E91E5', '#E15F99', '#1CA71C', '#FB0D0D', '#DA16FF', '#ffc100']
        
        for idx, signal_name in enumerate(signals, 1):
            signal = vcd[signal_name]
            tv = signal.tv
            
            times, values = [], []
            for t, v in tv:
                times.append(t)
                values.append(v)
            
            try:
                numeric_values = [int(v, 2) if isinstance(v, str) and v.strip('01') == '' 
                                else float(v) if isinstance(v, str)
                                else v for v in values]
            except ValueError:
                numeric_values = [0 if v == '0' else 1 if v == '1' 
                                else 0.5 for v in values]
            
            t_steps, v_steps = [], []
            for i in range(len(times)):
                if i > 0:
                    t_steps.append(times[i])
                    v_steps.append(numeric_values[i-1])
                t_steps.append(times[i])
                v_steps.append(numeric_values[i])
            
            fig.add_trace(
                go.Scatter(
                    x=t_steps,
                    y=v_steps,
                    name=signal_name.replace("_tb", ""),
                    mode='lines',
                    line=dict(
                        shape='hv',
                        color=colors[idx % len(colors)],
                        width=2
                    ),
                    showlegend=True
                ),
                row=idx,
                col=1
            )
            
            if numeric_values:
                y_min, y_max = min(numeric_values), max(numeric_values)
                padding = (y_max - y_min) * 0.2 if y_max != y_min else 0.2
                fig.update_yaxes(
                    range=[y_min - padding, y_max + padding],
                    row=idx,
                    col=1,
                    tickmode='linear',
                    tick0=0,
                    dtick=1
                )
        
        fig.update_layout(
            height=250 * len(signals),
            width=1200,
            title_text="Waveform Visualization",
            title_x=0.5,
            showlegend=True,
            legend=dict(
                yanchor="top",
                y=1.1,
                xanchor="right",
                x=1,
                orientation="h"
            ),
            plot_bgcolor='rgb(25, 25, 25)',
            paper_bgcolor='rgb(25, 25, 25)',
            font=dict(color='white'),
            margin=dict(l=50, r=50, t=100, b=50)
        )
        
        fig.update_xaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128, 128, 128, 0.2)',
            zeroline=True,
            zerolinecolor='rgba(128, 128, 128, 0.5)'
        )
        fig.update_yaxes(
            showgrid=True,
            gridwidth=1,
            gridcolor='rgba(128, 128, 128, 0.2)',
            zeroline=True,
            zerolinecolor='rgba(128, 128, 128, 0.5)'
        )
        
        return fig
        
    except Exception as e:
        st.error(f"Error processing VCD file: {str(e)}")
        return None

def run_verilog_simulation(test_code, design_code):
    """
    Run Verilog simulation using iverilog and vvp
    """
    try:
        # Inject VCD commands into test code
        modified_test_code = inject_vcd_commands(test_code)
        
        # Show the modified code if changes were made
        if modified_test_code != test_code:
            st.info("VCD dump commands were automatically added to your testbench")
        
        with open("test.v", "w") as f:
            f.write(modified_test_code)
        with open("design.v", "w") as f:
            f.write(design_code)
        
        compile_result = subprocess.run(
            ["iverilog", "-o", "simulation", "test.v", "design.v"],
            capture_output=True,
            text=True
        )
        
        if compile_result.returncode != 0:
            st.error("Compilation Error:")
            st.code(compile_result.stderr, language="verilog")
            return False
        
        sim_result = subprocess.run(
            ["vvp", "simulation"],
            capture_output=True,
            text=True
        )
        
        if sim_result.stdout:
            st.text("Simulation Output:")
            st.code(sim_result.stdout, language="verilog")
        
        if sim_result.stderr:
            st.error("Simulation Error:")
            st.code(sim_result.stderr, language="verilog")
            
        if sim_result.returncode != 0:
            return False
            
        if not os.path.exists("waveform.vcd"):
            st.error("No waveform.vcd file was generated. There might be an issue with the simulation.")
            return False
            
        return True
        
    except Exception as e:
        st.error(f"Error during simulation: {str(e)}")
        return False

def main():
    configure_page()
    
    st.title("VeriSim")
    
    tab1, tab2 = st.tabs(["Simulator", "Help"])
    
    with tab1:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("test.v")
            test_code = st_ace(
                value="""module test;
    reg clk;
    reg rst;
    
    // Instantiate your design here
    
    // Clock generation
    initial begin
        clk = 0;
        forever #10 clk = ~clk;
    end
    
    initial begin
        rst = 1;
        #100 rst = 0;
        
        #1000 $finish;
    end
endmodule""",
                language="verilog",
                theme="dracula",
                key="test_v",
                height=600,
                font_size=14,
                tab_size=4,
                show_gutter=True,
                show_print_margin=True,
                wrap=False,
                auto_update=True,
                readonly=False,
                placeholder="Write your test bench code here..."
            )
        
        with col2:
            st.subheader("design.v")
            design_code = st_ace(
                value="""module design(
    input wire clk,
    input wire rst
    // Add your ports here
);
    
    // Your design code here
    
endmodule""",
                language="verilog",
                theme="dracula",
                key="design_v",
                height=600,
                font_size=14,
                tab_size=4,
                show_gutter=True,
                show_print_margin=True,
                wrap=False,
                auto_update=True,
                readonly=False,
                placeholder="Write your design code here..."
            )
        
        col1, col2, col3 = st.columns([2,1,2])
        with col2:
            run_button = st.button("Run Simulation", type="primary", use_container_width=True)
        
        if run_button:
            if not test_code.strip() or not design_code.strip():
                st.error("Please enter both test bench and design code")
                return
            
            with st.spinner("Running simulation..."):
                if run_verilog_simulation(test_code, design_code):
                    st.success("Simulation completed successfully!")
                    
                    fig = visualize_vcd("waveform.vcd")
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)
                        
                        col1, col2, col3 = st.columns([2,1,2])
                        with col2:
                            st.download_button(
                                label="Download Visualization",
                                data=fig.to_html(),
                                file_name="waveform_visualization.html",
                                mime="text/html",
                                use_container_width=True
                            )
    
    with tab2:
        st.markdown("""
        ### How to Use
        1. Enter your test bench code in the left editor
        2. Enter your design code in the right editor
        3. Click "Run Simulation" to execute
        
        ### Editor Features
        - Syntax highlighting for Verilog
        - Auto-indentation
        - Line numbers
        - Tab support
        - Code folding
        - Dark theme for better readability
        
        ### VCD Generation
        The simulator automatically adds the necessary VCD dump commands to your testbench. You don't need to add these lines manually:
        ```verilog
        $dumpfile("waveform.vcd");
        $dumpvars(0, module_name);
        ```
        Just focus on writing your test stimulus and module instantiation.
        
        ### Important Requirements
        1. Include a simulation end statement:
        ```verilog
        #<time> $finish;
        ```
        2. Remember to instantiate your design module in the test bench
        """)

    # Cleanup temporary files
    for file in ["test.v", "design.v", "simulation", "waveform.vcd"]:
        if os.path.exists(file):
            try:
                os.remove(file)
            except:
                pass

if __name__ == "__main__":
    main()
