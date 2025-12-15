from .sudoku_logic import SudokuLogic
from .cultural_solver import CulturalSolverImpl

class SolverStrategy:
    """Interface for different solving algorithms."""
    def get_generator(self, board):
        raise NotImplementedError

class BacktrackingStrategy(SolverStrategy):
    def get_generator(self, board):
        N = len(board)
        step_count = 0  # <--- NEW: Track steps

        def find_empty(b):
            for r in range(N):
                for c in range(N):
                    if b[r][c] == 0: return r, c
            return None

        def recurse():
            nonlocal step_count
            cell = find_empty(board)
            if cell is None: return True
            r, c = cell
            for val in range(1, N+1):
                if SudokuLogic.valid_in_cell(board, r, c, val):
                    board[r][c] = val
                    
                    # Increment and yield step count
                    step_count += 1
                    yield ('update', r, c, val, step_count) 
                    
                    if (yield from recurse()): return True
                    
                    board[r][c] = 0
                    
                    # Increment and yield step count (backtracking is a step)
                    step_count += 1
                    yield ('backtrack', r, c, 0, step_count)
            return False

        yield ('start', None, None, None, 0)
        
        if (yield from recurse()):
            yield ('done', SudokuLogic.clone_board(board), 0, None, step_count)
        else:
            yield ('fail', None, 0, None, step_count)

class CulturalStrategy(SolverStrategy):
    def get_generator(self, board):
        iters = 2000 if len(board) > 6 else 1000
        solver = CulturalSolverImpl(board, pop_size=150, max_iters=iters)
        return solver.solve_gen()