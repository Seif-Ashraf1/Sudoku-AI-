import random

class SudokuLogic:
    """Helper functions for Sudoku rules and board generation."""
    
    @staticmethod
    def get_block_dims(N):
        if N == 6: return (2, 3)
        b = int(N**0.5)
        return (b, b)

    @staticmethod
    def make_empty_board(N):
        return [[0]*N for _ in range(N)]

    @staticmethod
    def clone_board(board):
        return [row[:] for row in board]

    @staticmethod
    def valid_in_cell(board, r, c, val):
        N = len(board)
        br_h, bc_w = SudokuLogic.get_block_dims(N)
        
        if val == 0: return True
        if any(board[r][j] == val for j in range(N)): return False
        if any(board[i][c] == val for i in range(N)): return False
        
        start_r, start_c = (r // br_h) * br_h, (c // bc_w) * bc_w
        for i in range(start_r, start_r + br_h):
            for j in range(start_c, start_c + bc_w):
                if board[i][j] == val: return False
        return True

    @staticmethod
    def generate_puzzle(N, difficulty=0.5):
        board = SudokuLogic.make_empty_board(N)
        
        def fill(b):
            for i in range(N):
                for j in range(N):
                    if b[i][j] == 0:
                        nums = list(range(1, N+1))
                        random.shuffle(nums)
                        for n in nums:
                            if SudokuLogic.valid_in_cell(b, i, j, n):
                                b[i][j] = n
                                if fill(b): return True
                                b[i][j] = 0
                        return False
            return True
        fill(board)
        
        puzzle = SudokuLogic.clone_board(board)
        remove_count = int(N * N * difficulty)
        cells = [(r,c) for r in range(N) for c in range(N)]
        random.shuffle(cells)
        
        for r,c in cells[:remove_count]:
            puzzle[r][c] = 0
        return puzzle