import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from Models.sudoku_logic import SudokuLogic

# Matplotlib imports
try:
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

class SudokuView:
    def __init__(self, root, controller):
        self.root = root
        self.controller = controller
        self.board_widgets = []
        
        # Plotting State
        self.plot_data_x = []
        self.plot_data_y = []
        
        self.root.title("Sudoku AI Solver")
        self.root.geometry("1000x750")
        
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        self._build_sidebar()
        self._build_grid_area()
        
        # Initial stats
        self.lbl_status.config(text="Ready")
        self.lbl_fitness.config(text="Fitness: --")
        self.lbl_generations.config(text="Generation: 0")
        self.lbl_time.config(text="Time: 0.00s")

    def _build_sidebar(self):
        frame = ttk.Frame(self.root, padding="10")
        frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Title
        ttk.Label(frame, text="Controls", font=("Arial", 16, "bold")).pack(pady=10)
        
        # Inputs
        ttk.Label(frame, text="Grid Size:").pack(anchor=tk.W)
        self.size_var = tk.IntVar(value=9)
        self.cb_size = ttk.Combobox(frame, textvariable=self.size_var, values=[4, 6, 9], state="readonly")
        self.cb_size.pack(fill=tk.X, pady=5)
        self.cb_size.bind("<<ComboboxSelected>>", lambda e: self.controller.request_new_puzzle(self.size_var.get()))
        
        ttk.Label(frame, text="Algorithm:").pack(anchor=tk.W, pady=(10,0))
        self.algo_var = tk.StringVar(value="Backtracking Algorithm")
        self.cb_algo = ttk.Combobox(frame, textvariable=self.algo_var, 
                                    values=["Backtracking Algorithm", "Cultural Algorithm"], 
                                    state="readonly")
        self.cb_algo.pack(fill=tk.X, pady=5)
        
        ttk.Label(frame, text="Speed (Delay):").pack(anchor=tk.W, pady=(10,0))
        self.speed_scale = ttk.Scale(frame, from_=0.0, to=1.0, orient=tk.HORIZONTAL, 
                                     command=lambda v: self.controller.set_speed(v))
        self.speed_scale.set(0.05)
        self.speed_scale.pack(fill=tk.X, pady=5)
        
        # Buttons
        ttk.Button(frame, text="New Puzzle", 
                   command=lambda: self.controller.request_new_puzzle(self.size_var.get())).pack(fill=tk.X, pady=(20, 5))
        self.btn_solve = ttk.Button(frame, text="Solve!", command=self.controller.start_solving)
        self.btn_solve.pack(fill=tk.X, pady=5)
        ttk.Button(frame, text="Stop", command=self.controller.stop_solving).pack(fill=tk.X, pady=5)
        
        # --- NEW: Final Plot Button (Initially Disabled) ---
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        self.btn_plot = ttk.Button(frame, text="Show Fitness Graph", command=self.show_final_plot, state="disabled")
        self.btn_plot.pack(fill=tk.X, pady=5)

        # Stats
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        self.lbl_fitness = ttk.Label(frame, text="Fitness: --", foreground="blue", font=("Arial", 11))
        self.lbl_fitness.pack(pady=2)
        self.lbl_generations = ttk.Label(frame, text="Generation: 0", font=("Arial", 11))
        self.lbl_generations.pack(pady=2)
        self.lbl_time = ttk.Label(frame, text="Time: 0.00s", font=("Arial", 11, "bold"))
        self.lbl_time.pack(pady=10)
        self.lbl_status = ttk.Label(frame, text="Ready", font=("Arial", 12))
        self.lbl_status.pack(pady=5)
        
        # Legend
        ttk.Separator(frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=20)
        ttk.Label(frame, text="Legend:", font=("Arial", 10, "bold")).pack(anchor=tk.W)
        self._add_legend_item(frame, "#99ff99", "Backtrack: Try / Cultural: Solved")
        self._add_legend_item(frame, "#ff9999", "Backtrack: Undo / Cultural: Error")
        self._add_legend_item(frame, "#ffcc99", "Cultural: Swap Attempt")

    def _add_legend_item(self, parent, color, text):
        f = tk.Frame(parent)
        f.pack(fill=tk.X, pady=2)
        tk.Label(f, bg=color, width=3).pack(side=tk.LEFT, padx=5)
        tk.Label(f, text=text, font=("Arial", 9)).pack(side=tk.LEFT)

    def _build_grid_area(self):
        self.grid_frame = ttk.Frame(self.root, padding="20")
        self.grid_frame.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

    def draw_grid(self, N, puzzle_data):
        for widget in self.grid_frame.winfo_children(): widget.destroy()
        self.board_widgets = []
        br_h, bc_w = SudokuLogic.get_block_dims(N)
        for r in range(N):
            row_widgets = []
            for c in range(N):
                pad_y = (10, 0) if r % br_h == 0 and r != 0 else (0, 0) 
                pad_x = (10, 0) if c % bc_w == 0 and c != 0 else (0, 0) 
                cell_frame = tk.Frame(self.grid_frame, bg="gray", bd=1)
                cell_frame.grid(row=r, column=c, padx=pad_x, pady=pad_y, sticky="nsew")
                val = puzzle_data[r][c]
                text = str(val) if val != 0 else ""
                color = "#e0e0e0" if val != 0 else "white"
                lbl = tk.Label(cell_frame, text=text, bg=color, font=("Arial", 14 if N<16 else 10), width=4, height=2)
                lbl.pack(fill=tk.BOTH, expand=True)
                row_widgets.append(lbl)
            self.board_widgets.append(row_widgets)
        for i in range(N):
            self.grid_frame.rowconfigure(i, weight=1)
            self.grid_frame.columnconfigure(i, weight=1)

    # --- Plotting Logic ---
    def enable_plot_button(self, x_data, y_data):
        """Called by Controller when solving is finished."""
        self.plot_data_x = x_data
        self.plot_data_y = y_data
        self.btn_plot.config(state="normal")

    def disable_plot_button(self):
        self.btn_plot.config(state="disabled")

    def show_final_plot(self):
        if not HAS_MATPLOTLIB:
            messagebox.showerror("Error", "Matplotlib is not installed.\nRun: pip install matplotlib")
            return

        # Create a popup window
        plot_window = tk.Toplevel(self.root)
        plot_window.title("Final Fitness Graph")
        plot_window.geometry("600x400")
        
        # Setup Figure
        fig = Figure(figsize=(5, 4), dpi=100)
        ax = fig.add_subplot(111)
        ax.set_title("Cultural Algorithm Convergence")
        ax.set_xlabel("Generations")
        ax.set_ylabel("Fitness (Conflicts)")
        
        # Plot the stored data
        ax.plot(self.plot_data_x, self.plot_data_y, 'b-', marker='o', markersize=2)
        ax.grid(True)

        canvas = FigureCanvasTkAgg(fig, master=plot_window)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

    # --- Existing Helper Methods ---
    def update_cell_value(self, r, c, val):
        text = str(val) if val != 0 else ""
        self.board_widgets[r][c].config(text=text)

    def set_cell_color(self, r, c, color):
        self.board_widgets[r][c].config(bg=color)

    def update_cell(self, r, c, val, color="white"):
        self.update_cell_value(r, c, val)
        self.set_cell_color(r, c, color)

    def update_stats(self, status=None, time_s=None, fitness=None, gen=None, color="black"):
        if status: self.lbl_status.config(text=status, foreground=color)
        if time_s is not None: self.lbl_time.config(text=f"Time: {time_s:.2f}s")
        if fitness is not None: self.lbl_fitness.config(text=f"Fitness: {fitness}")
        if gen is not None: self.lbl_generations.config(text=f"Generation: {gen}")

    def clear_fitness(self):
        self.lbl_fitness.config(text="Fitness: --")

    def toggle_solve_btn(self, enable):
        self.btn_solve.config(state="normal" if enable else "disabled")

    def get_selected_algorithm(self):
        return self.algo_var.get()