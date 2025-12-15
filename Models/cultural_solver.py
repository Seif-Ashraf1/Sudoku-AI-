import random
from .sudoku_logic import SudokuLogic

class BeliefSpace:
    """
    Stores cultural knowledge derived from the best individuals (elites).
    
    Knowledge Types:
    1. Situational: Keeps track of the global best solution found so far.
    2. Normative/Domain: Tracks a 'Conflict Matrix'—a heat map of cells 
       that frequently cause conflicts in high-performing individuals.
    """
    def __init__(self, N):
        self.N = N
        self.global_best = None
        self.global_best_fit = float('inf')
        # Heat map: How often is cell (r,c) involved in a conflict among elites?
        self.conflict_matrix = [[0] * N for _ in range(N)]
        # Track total conflicts per row to speed up mutation selection
        self.row_conflict_scores = [0] * N

    def update(self, elites, fitness_map, get_conflicted_cells_func):
        """
        Acceptance Function: Incorporate knowledge from the current elites.
        """
        # 1. Update Situational Knowledge (Global Best)
        best_elite = min(elites, key=lambda p: fitness_map[id(p)])
        best_fit = fitness_map[id(best_elite)]
        
        if best_fit < self.global_best_fit:
            self.global_best = [r[:] for r in best_elite]
            self.global_best_fit = best_fit

        # 2. Update Normative Knowledge (Conflict Matrix)
        # We reset scores slightly (decay) or clear them to reflect current generation state
        # Here we perform a full reset to adapt strictly to the current elite "culture"
        self.conflict_matrix = [[0] * self.N for _ in range(self.N)]
        self.row_conflict_scores = [0] * self.N

        for ind in elites:
            bad_cells = get_conflicted_cells_func(ind)
            for r, c in bad_cells:
                self.conflict_matrix[r][c] += 1
                self.row_conflict_scores[r] += 1

    def select_target_row(self):
        """
        Influence Function: Select a row to mutate based on conflict probability.
        Rows with higher conflict scores in the belief space are more likely to be selected.
        """
        total_conflicts = sum(self.row_conflict_scores)
        
        # If no conflicts or perfect state, return random (exploration)
        if total_conflicts == 0:
            return random.randint(0, self.N - 1)

        # Roulette Wheel Selection
        pick = random.uniform(0, total_conflicts)
        current = 0
        for r in range(self.N):
            current += self.row_conflict_scores[r]
            if current > pick:
                return r
        return random.randint(0, self.N - 1)


class CulturalSolverImpl:
    def __init__(self, puzzle, pop_size=100, elite_frac=0.1, max_iters=2000):
        self.puzzle = puzzle
        self.N = len(puzzle)
        self.br_h, self.bc_w = SudokuLogic.get_block_dims(self.N)
        self.pop_size = pop_size
        self.elite_frac = elite_frac
        self.max_iters = max_iters
        self.fixed = [[puzzle[i][j] != 0 for j in range(self.N)] for i in range(self.N)]
        self.missing_map = []
        
        # Initialize Belief Space
        self.belief_space = BeliefSpace(self.N)

        for r in range(self.N):
            present = set(puzzle[r]) - {0}
            missing = list(set(range(1, self.N + 1)) - present)
            self.missing_map.append(missing)

    def fitness(self, board):
        conflicts = 0
        N = self.N
        # Cols
        for c in range(N):
            seen = set()
            for r in range(N):
                val = board[r][c]
                if val in seen: conflicts += 1
                seen.add(val)
        # Blocks
        for br in range(0, N, self.br_h):
            for bc in range(0, N, self.bc_w):
                seen = set()
                for i in range(br, br+self.br_h):
                    for j in range(bc, bc+self.bc_w):
                        val = board[i][j]
                        if val in seen: conflicts += 1
                        seen.add(val)
        return conflicts

    def get_conflicted_cells(self, board):
        conflicts = set()
        N = self.N
        # Cols
        for c in range(N):
            seen = {}
            for r in range(N):
                val = board[r][c]
                seen.setdefault(val, []).append(r)
            for val, rows in seen.items():
                if len(rows) > 1:
                    for r in rows:
                        if not self.fixed[r][c]: conflicts.add((r, c))
        # Blocks
        for br in range(0, N, self.br_h):
            for bc in range(0, N, self.bc_w):
                seen = {}
                cells = [(i, j) for i in range(br, br+self.br_h) for j in range(bc, bc+self.bc_w)]
                for r, c in cells:
                    val = board[r][c]
                    seen.setdefault(val, []).append((r,c))
                for val, locs in seen.items():
                    if len(locs) > 1:
                        for (r,c) in locs:
                            if not self.fixed[r][c]: conflicts.add((r, c))
        return list(conflicts)

    def random_ind(self):
        board = SudokuLogic.clone_board(self.puzzle)
        for r in range(self.N):
            missing = self.missing_map[r][:]
            random.shuffle(missing)
            idx = 0
            for c in range(self.N):
                if not self.fixed[r][c]:
                    board[r][c] = missing[idx]
                    idx +=1
        return board

    def solve_gen(self):
        pop = [self.random_ind() for _ in range(self.pop_size)]
        fits = {id(p): self.fitness(p) for p in pop}
        
        # Initial best
        best = min(pop, key=lambda p: fits[id(p)])
        best_fit = fits[id(best)]
        yield ('init', SudokuLogic.clone_board(best), best_fit, 0, [])
        
        for it in range(1, self.max_iters+1):
            pop.sort(key=lambda p: fits[id(p)])
            
            # --- CULTURAL UPDATE (Acceptance) ---
            # Update Belief Space with the top performers (elites)
            num_elite = max(2, int(self.pop_size * self.elite_frac))
            elites = pop[:num_elite]
            self.belief_space.update(elites, fits, self.get_conflicted_cells)
            
            # Check current population best
            curr_best = pop[0]
            curr_fit = fits[id(curr_best)]
            bad_cells = self.get_conflicted_cells(curr_best) # For visualization

            # Update global best if needed
            if curr_fit < best_fit:
                best_fit = curr_fit
                best = SudokuLogic.clone_board(curr_best)

            yield ('iter', SudokuLogic.clone_board(curr_best), best_fit, it, bad_cells)

            # Greedy Polish (unchanged, acts on the best individual)
            if len(bad_cells) > 0:
                polished = SudokuLogic.clone_board(curr_best)
                start_f = fits[id(curr_best)]
                r, c1 = random.choice(bad_cells)
                mutable_cols = [c for c in range(self.N) if not self.fixed[r][c] and c != c1]
                if mutable_cols:
                    c2 = random.choice(mutable_cols)
                    yield ('swap_try', r, c1, polished[r][c2], c2, polished[r][c1]) 
                    polished[r][c1], polished[r][c2] = polished[r][c2], polished[r][c1]
                    yield ('swap_reset', r, c1, c2)
                    new_f = self.fitness(polished)
                    if new_f < start_f:
                        pop[0] = polished
                        fits[id(pop[0])] = new_f
                        if new_f < best_fit:
                            best_fit = new_f
                            best = SudokuLogic.clone_board(polished)
                            if best_fit == 0:
                                yield ('done', best, 0, it, [])
                                return

            # --- GENETIC OPERATIONS WITH CULTURAL INFLUENCE ---
            # Elites survive automatically
            elites = [SudokuLogic.clone_board(p) for p in pop[:num_elite]]
            for e in elites: fits[id(e)] = fits[id(pop[0])] # Approximate fitness copy
            
            new_pop = elites[:]
            while len(new_pop) < self.pop_size:
                # Crossover (unchanged)
                p1 = random.choice(elites)
                p2 = random.choice(pop[:self.pop_size//2])
                child = [r[:] for r in (p1 if random.random()<0.5 else p2)]
                for r in range(self.N):
                    if random.random() < 0.5: child[r] = p2[r][:]
                
                # Mutation (Influenced by Belief Space)
                if random.random() < 0.4:
                    # --- CULTURAL INFLUENCE ---
                    # Instead of a purely random row, ask Belief Space which row is problematic
                    r = self.belief_space.select_target_row()
                    
                    mutable = [c for c in range(self.N) if not self.fixed[r][c]]
                    if len(mutable) >= 2:
                        c1, c2 = random.sample(mutable, 2)
                        child[r][c1], child[r][c2] = child[r][c2], child[r][c1]
                
                new_pop.append(child)
                fits[id(child)] = self.fitness(child)
            
            pop = new_pop
            
            if best_fit == 0:
                yield ('done', best, 0, it, [])
                return
        
        final_bad_cells = self.get_conflicted_cells(best)
        yield ('fail', best, best_fit, self.max_iters, final_bad_cells)