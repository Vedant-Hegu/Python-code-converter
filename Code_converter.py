import os
import sys
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import matplotlib.pyplot as plt
from dotenv import load_dotenv
from google import genai

# --- 1. CONFIGURATION & API SETUP ---

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

# Basic error handling for API Key
if not api_key:
    # Create a dummy root to show message box if init fails
    root = tk.Tk()
    root.withdraw()
    messagebox.showerror("Error", "API Key not found. Please check your .env file.")
    raise ValueError("API Key not found.")

client = genai.Client(api_key=api_key)

# --- 2. VISUALIZATION ENGINE (Modified from visualization.py) ---

class GuiCodeVisualizer:
    """
    Runs Python code locally using sys.settrace.
    Outputs text trace to a Tkinter widget and graphs arrays using Matplotlib.
    """
    def __init__(self, output_widget):
        self.last_vars = {}
        self.output_widget = output_widget
        plt.ion()  # Interactive mode for dynamic graphing

    def trace(self, frame, event, arg):
        if event == "line":
            local_vars = frame.f_locals.copy()
            # Filter out internal python variables
            clean_vars = {k: v for k, v in local_vars.items() if not k.startswith('__')}

            # Show only when variables change
            if clean_vars != self.last_vars:
                self.last_vars = clean_vars
                self.display_vars(clean_vars, frame.f_lineno)
        return self.trace

    def display_vars(self, variables, line_no):
        if not variables:
            return

        # Format output for the GUI Text Widget
        log_entry = f"\n--- Step at Line {line_no} ---\n"
        for var, val in variables.items():
            val_type = type(val).__name__
            log_entry += f"  {var} ({val_type}) = {val}\n"
        
        # Update Text Widget safely
        self.output_widget.insert(tk.END, log_entry)
        self.output_widget.see(tk.END)
        self.output_widget.update()

        # Update Graphs
        self.visualize_arrays(variables)

    def visualize_arrays(self, variables):
        # Find lists/arrays to graph
        arrays = {k: v for k, v in variables.items() if isinstance(v, list) and all(isinstance(x, (int, float)) for x in v)}
        
        if arrays:
            plt.clf()
            
            # Simple plotting of the first found array for demonstration
            # In a complex app, you might want subplots
            for i, (name, data) in enumerate(arrays.items()):
                plt.title(f"Live Data: {name}")
                plt.bar(range(len(data)), data, color='skyblue')
                break # Only plot the first array found to prevent window flickering
            
            plt.draw()
            plt.pause(0.5) # Pause to make the animation visible

    def run(self, user_code):
        try:
            compiled = compile(user_code, "<user_code>", "exec")
            sys.settrace(self.trace)
            exec(compiled, {})
        except Exception as e:
            self.output_widget.insert(tk.END, f"\n❌ Runtime Error: {e}\n")
        finally:
            sys.settrace(None)
            self.output_widget.insert(tk.END, "\n--- Execution Finished ---\n")

# --- 3. MAIN APPLICATION LOGIC ---

def ask_gemini(prompt):
    """Sends the prompt to Gemini and retrieves the response."""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash", contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Error: {e}"

def perform_conversion():
    """Reads input, constructs the dynamic prompt, and updates the output."""
    source_code = input_text.get("1.0", tk.END).strip()
    
    if not source_code:
        messagebox.showwarning("Warning", "Please paste some code first!")
        return

    source_lang = source_combo.get()
    target_lang = target_combo.get()

    if not source_lang or not target_lang:
        messagebox.showwarning("Warning", "Please select both source and target languages.")
        return

    convert_btn.config(text=f"Converting...", state=tk.DISABLED)
    root.update()

    prompt = (
        f"Act as a code converter. Convert this {source_lang} code to {target_lang}.\n"
        f"Provide ONLY the {target_lang} code, no markdown or explanations.\n\n"
        f"{source_code}"
    )

    result = ask_gemini(prompt)

    output_text.delete("1.0", tk.END)
    output_text.insert(tk.END, result)
    
    convert_btn.config(text="Convert Code", state=tk.NORMAL)

def swap_languages():
    src = source_combo.get()
    tgt = target_combo.get()
    source_combo.set(tgt)
    target_combo.set(src)

# --- 4. VISUALIZATION FUNCTIONS ---

def generate_ascii_flowchart():
    """Button 1: Asks Gemini for an ASCII Flowchart (Static Analysis)."""
    code = output_text.get("1.0", tk.END).strip()
    lang = target_combo.get()
    
    if not code:
        messagebox.showwarning("Warning", "No converted code to analyze!")
        return

    # UI Feedback
    btn_flowchart.config(text="Generating...", state=tk.DISABLED)
    root.update()

    prompt = (
        f"Act as a code visualizer for this {lang} code.\n"
        f"Create a text-based ASCII art flowchart showing the logic flow (decisions, loops, start/end).\n"
        f"Use boxes [Process], diamonds <Decision>, and arrows -->.\n"
        f"Provide ONLY the ASCII art.\n\n"
        f"Code:\n{code}"
    )
    
    result = ask_gemini(prompt)
    
    # Show in new window
    top = tk.Toplevel(root)
    top.title(f"ASCII Flowchart ({lang})")
    top.geometry("600x600")
    
    tk.Label(top, text=f"Flowchart for {lang}", font=("Arial", 14, "bold")).pack(pady=10)
    text_area = scrolledtext.ScrolledText(top, height=30, width=70, font=("Consolas", 10))
    text_area.pack(fill=tk.BOTH, expand=True, padx=15, pady=10)
    
    text_area.insert(tk.END, result)
    text_area.config(state=tk.DISABLED)
    
    btn_flowchart.config(text="Generate Flowchart (AI)", state=tk.NORMAL)

def run_execution_visualizer():
    """Button 2: Runs the local Python tracer (Dynamic Analysis)."""
    code = output_text.get("1.0", tk.END).strip()
    lang = target_combo.get()

    # CONSTRAINT CHECK: This visualizer only works if the target code is Python
    if lang != "Python":
        messagebox.showerror(
            "Language Error", 
            f"The Live Execution Visualizer runs locally and supports Python only.\n"
            f"Current converted code is {lang}.\n\n"
            f"Tip: Select 'Python' as the Target Language to use this feature."
        )
        return

    if not code:
        messagebox.showwarning("Warning", "No code to run!")
        return

    # Create a pop-up window for the trace logs
    top = tk.Toplevel(root)
    top.title("Live Execution Trace")
    top.geometry("500x600")
    
    tk.Label(top, text="Variable Memory Trace", font=("Arial", 12, "bold")).pack(pady=5)
    log_area = scrolledtext.ScrolledText(top, height=30, width=60, font=("Consolas", 10), bg="#1e1e1e", fg="#00ff00")
    log_area.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    # Initialize and run the visualizer
    # Note: We strip markdown ticks if Gemini added them
    clean_code = code.replace("```python", "").replace("```", "").strip()
    
    vis = GuiCodeVisualizer(output_widget=log_area)
    
    # Run slightly delayed to allow UI to render
    top.after(100, lambda: vis.run(clean_code))


# --- 5. UI LAYOUT ---

if __name__ == "__main__":
    
    root = tk.Tk()
    root.title("AI Code Converter & Dual Visualizer")
    root.geometry("700x850") 

    LANGUAGES = ["Python", "C++", "C", "Java", "JavaScript"]

    # --- Header ---
    tk.Label(root, text="DevTool Suite", font=("Arial", 18, "bold"), fg="#333").pack(pady=(15, 5))

    # --- Selection Area ---
    selection_frame = tk.Frame(root)
    selection_frame.pack(pady=10)

    tk.Label(selection_frame, text="From:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
    source_combo = ttk.Combobox(selection_frame, values=LANGUAGES, state="readonly", width=12)
    source_combo.current(1) # Default C++
    source_combo.pack(side=tk.LEFT, padx=5)

    swap_btn = tk.Button(selection_frame, text="⇄", command=swap_languages, font=("Arial", 12, "bold"), bg="#ddd")
    swap_btn.pack(side=tk.LEFT, padx=15)

    tk.Label(selection_frame, text="To:", font=("Arial", 11)).pack(side=tk.LEFT, padx=5)
    target_combo = ttk.Combobox(selection_frame, values=LANGUAGES, state="readonly", width=12)
    target_combo.current(0) # Default Python
    target_combo.pack(side=tk.LEFT, padx=5)

    # --- Input ---
    tk.Label(root, text="Source Code:", font=("Arial", 10, "bold")).pack(pady=(5, 0))
    input_text = scrolledtext.ScrolledText(root, height=10, width=80)
    input_text.pack(padx=15, pady=5)

    # --- Convert ---
    convert_btn = tk.Button(root, text="Convert Code", command=perform_conversion, 
                            font=("Arial", 11, "bold"), bg="#4CAF50", fg="white", height=1, width=20)
    convert_btn.pack(pady=5)

    # --- Output ---
    tk.Label(root, text="Converted Code:", font=("Arial", 10, "bold")).pack(pady=(5, 0))
    output_text = scrolledtext.ScrolledText(root, height=10, width=80, bg="#f0f0f0")
    output_text.pack(padx=15, pady=5)

    # --- Visualization Panel ---
    vis_frame = tk.LabelFrame(root, text="Visualization Suite", font=("Arial", 10, "bold"), padx=10, pady=10)
    vis_frame.pack(fill=tk.X, padx=15, pady=10)

    # Button 1: AI Flowchart (Works for all languages)
    btn_flowchart = tk.Button(vis_frame, text="📄 Generate Flowchart (AI)", command=generate_ascii_flowchart,
                           font=("Arial", 10), bg="#2196F3", fg="white", height=2, width=25)
    btn_flowchart.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)

    # Button 2: Live Trace (Works for Python only)
    btn_trace = tk.Button(vis_frame, text="📊 Visualize Execution (Local)", command=run_execution_visualizer,
                           font=("Arial", 10), bg="#FF9800", fg="white", height=2, width=25)
    btn_trace.pack(side=tk.LEFT, padx=10, expand=True, fill=tk.X)

    tk.Label(vis_frame, text="* 'Visualize Execution' requires Target Language: Python", 
             font=("Arial", 8, "italic"), fg="#555").pack(side=tk.BOTTOM, pady=(5,0))

    root.mainloop()
