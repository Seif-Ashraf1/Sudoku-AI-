import tkinter as tk
from Controllers.controller import SudokuController

if __name__ == "__main__":
    root = tk.Tk()
    app = SudokuController(root)
    root.mainloop()