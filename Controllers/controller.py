import threading
import time
from Models.sudoku_logic import SudokuLogic
from Models.strategies import BacktrackingStrategy, CulturalStrategy
from Views.view import SudokuView

class SudokuController:
    def __init__(self, root):
        self.root = root
        self.view = SudokuView(root, self)
        
        self.N = 9
        self.puzzle = []
        self.speed_delay = 0.05
        self.solving = False
        self.stop_event = threading.Event()
        self.start_time = 0.0
        
        self.current_bad_cells = set() 
        self.previous_bad_cells = set()
        
        # Data storage for the plot
        self.fitness_history = []
        
        self.request_new_puzzle(9)

    def request_new_puzzle(self, N):
        self.stop_solving()
        self.N = N
        self.puzzle = SudokuLogic.generate_puzzle(N)
        self.view.draw_grid(N, self.puzzle)
        self.view.update_stats(status="Generated New Puzzle", fitness="--", gen="0", time_s=0.0)
        self.view.disable_plot_button()

    def set_speed(self, val):
        self.speed_delay = float(val)

    def start_solving(self):
        if self.solving: return
        self.solving = True
        self.stop_event.clear()
        self.view.toggle_solve_btn(False)
        self.view.disable_plot_button() # Disable plot while solving
        self.view.update_stats(status="Solving...", color="orange", time_s=0.0)
        
        self.fitness_history = [] 
        
        algo_name = self.view.get_selected_algorithm()
        
        if algo_name == "Backtracking Algorithm":
            self.view.clear_fitness()
            strategy = BacktrackingStrategy()
        else:
            strategy = CulturalStrategy()
            self.previous_bad_cells = set()
            self.current_bad_cells = set()

        thread = threading.Thread(target=self._solve_loop, args=(strategy, algo_name))
        thread.daemon = True
        thread.start()

    def stop_solving(self):
        self.solving = False
        self.stop_event.set()
        self.view.toggle_solve_btn(True)

    def _solve_loop(self, strategy, algo_name):
        self.start_time = time.time()
        work_board = SudokuLogic.clone_board(self.puzzle)
        step_generator = strategy.get_generator(work_board)

        try:
            for step in step_generator:
                if self.stop_event.is_set(): break
                self.root.after(0, lambda s=step: self._handle_step(s, algo_name))
                if self.speed_delay > 0:
                    time.sleep(self.speed_delay)
        except Exception as e:
            print(f"Error in solver thread: {e}")

        self.root.after(0, lambda: self._finish_solve())

    def _handle_step(self, step, algo_name):
        elapsed = time.time() - self.start_time
        stype = step[0]
        
        if algo_name == "Backtracking Algorithm":
            if stype in ['update', 'backtrack']:
                r, c, val, step_cnt = step[1], step[2], step[3], step[4]
                color = "#99ff99" if stype == 'update' else "#ff9999"
                self.view.update_cell(r, c, val, color)
                self.view.update_stats(time_s=elapsed, gen=step_cnt)
            elif stype == 'done':
                board = step[1]
                self._draw_full_board(board, "#ccffcc")
                self.view.update_stats(status="SOLVED!", color="green", time_s=elapsed)
            elif stype == 'fail':
                self.view.update_stats(status="No Solution Found", color="red", time_s=elapsed)

        else: # Cultural Algorithm
            if stype == 'init':
                board, fit, it, bad_cells_list = step[1], step[2], step[3], step[4]
                self._draw_full_board(board, "white")
                self.current_bad_cells = set(bad_cells_list)
                self.previous_bad_cells = self.current_bad_cells
                
                # Record Data
                self.fitness_history.append((it, fit))
                self.view.update_stats(fitness=fit, gen=it, time_s=elapsed, status="Initializing...")

            elif stype == 'iter':
                board, fit, it, bad_cells_list = step[1], step[2], step[3], step[4]
                new_bad_cells = set(bad_cells_list)
                
                self._update_board_values(board)
                
                # Smart Coloring
                to_white = self.previous_bad_cells - new_bad_cells
                for (r, c) in to_white: self.view.set_cell_color(r, c, "white")
                to_red = new_bad_cells - self.previous_bad_cells
                for (r, c) in to_red: self.view.set_cell_color(r, c, "#ff9999")
                
                self.current_bad_cells = new_bad_cells
                self.previous_bad_cells = new_bad_cells
                
                # Record Data (Silent)
                self.fitness_history.append((it, fit))
                self.view.update_stats(fitness=fit, gen=it, time_s=elapsed, status="Evolving...")
                
            elif stype == 'swap_try':
                r, c1, v1, c2, v2 = step[1], step[2], step[3], step[4], step[5]
                self.view.update_cell_value(r, c1, v1)
                self.view.set_cell_color(r, c1, "#ffcc99")
                self.view.update_cell_value(r, c2, v2)
                self.view.set_cell_color(r, c2, "#ffcc99")
                
            elif stype == 'swap_reset':
                r, c1, c2 = step[1], step[2], step[3]
                c1_col = "#ff9999" if (r, c1) in self.current_bad_cells else "white"
                c2_col = "#ff9999" if (r, c2) in self.current_bad_cells else "white"
                self.view.set_cell_color(r, c1, c1_col)
                self.view.set_cell_color(r, c2, c2_col)
                
            elif stype == 'done':
                board = step[1]
                self._draw_full_board(board, "#ccffcc")
                self.fitness_history.append((step[3], 0))
                self.view.update_stats(status="SOLVED!", color="green", fitness=0, time_s=elapsed)
                
                # ENABLE PLOT
                self._enable_plot_in_view()
            
            elif stype == 'fail':
                best_board, final_fit, final_bad_cells = step[1], step[2], step[4]
                self._update_board_values(best_board)
                self._draw_full_board(best_board, "white")
                for (r, c) in final_bad_cells: self.view.set_cell_color(r, c, "#ff9999")
                
                self.view.update_stats(status="STUCK (Local Optima)", color="red", fitness=final_fit, time_s=elapsed)
                
                # ENABLE PLOT
                self._enable_plot_in_view()

    def _enable_plot_in_view(self):
        if self.fitness_history:
            x = [d[0] for d in self.fitness_history]
            y = [d[1] for d in self.fitness_history]
            self.view.enable_plot_button(x, y)

    def _draw_full_board(self, board, color):
        for r in range(self.N):
            for c in range(self.N):
                if self.puzzle[r][c] == 0:
                    self.view.update_cell(r, c, board[r][c], color)

    def _update_board_values(self, board):
        for r in range(self.N):
            for c in range(self.N):
                if self.puzzle[r][c] == 0:
                    self.view.update_cell_value(r, c, board[r][c])

    def _finish_solve(self):
        self.stop_solving()
        elapsed = time.time() - self.start_time
        self.view.update_stats(time_s=elapsed)