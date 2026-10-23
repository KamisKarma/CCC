# CCC 2026 Level 6 (Nanofabricator): shared optimization

**Goal: under 15,100 lines in total (medium + large + enormous). First place currently has 15,200.**
Small and example don't count. The contest ends at 19:00.

## Status
| File | Lines (best/) |
|---|---|
| medium | see `python tools/merge_best.py` |
| large | |
| enormous | |

Starting point when this repo was created: 15,640 in total.

## Layout
- `inputs/`: the three scored inputs plus the task PDF.
- `best/`: **current best valid outputs**. Upload these three files to the contest platform.
- `contrib/<who>/<key>/case_<i>.txt`: improvements from each participant. `key` is 2 (medium), 3 (large) or 4 (enormous); `i` is the case index starting at 0. One instruction row per line, 6 tokens separated by spaces.
- `tools/merge_best.py`: takes the shortest valid program per case from `best/` and every `contrib/*`, then rewrites `best/`.
- `code/python/validate_level6_optimized.py`: independent validator. `simulate(case, program)["valid"]` means the pattern was submitted exactly `count` times.
- `code/cs_beam/`: the strongest optimizer, a C# beam search (.NET 9). Before running it, set `Root` in `Program.cs` to a local folder that contains `level6/in_level-6_<name>.txt`, `Lösungen/level6_cs/out_level-6_<name>.txt` (working outputs) and `Lösungen/level6/out_level-6_<name>.txt` (seed outputs). Seed both with `best/`.
  - Build: `dotnet build -c Release`
  - Run: `dotnet bin/Release/net9.0/L6.dll opt 3-large,4-enormous,2-medium <seconds> <threads> W=400 wH=100 wC=2 wS=0 dbl=1`
  - Useful extras: `suf=3` (re-search the end of existing programs from 3 cut points), `minlen=50` (only long programs), `seed=<n>`, `W=1200`.
  - `tune <name> <step> <threads> k=v...` measures settings on every step-th case.
- `code/python/level6e.py`, `opt6e.py`: Python numpy beam (good settings: `W=32 cap=1 w_prog=10 w_min=7 w_mean=1.5 w_far=2.2`).
- `code/python/periodic_k.py`, `level6_periodic.py`: CP-SAT cycle search for repeated patterns (needs OR-Tools).
- `code/cpp/`: C++ beam variants (g++ -O2).
- `notes/TIPPS_FUER_NAECHSTE_KI.md`: rules, pitfalls and what did or didn't work (German).

## How two Claudes work together without conflicts
1. Each side writes only to its own folder `contrib/<name>/...`, never directly to `best/`.
2. Before writing a program: check it with `simulate(...)["valid"]` and make sure it's shorter than the case in `best/`.
3. `git pull`, run `python tools/merge_best.py`, commit, `git push`. On merge conflicts in `best/`: just run `merge_best.py` again and commit; it always takes the shortest valid program.
4. Agree on who works on what. Good split: one side on medium (many repetitions; cycle/chain search helps there), the other on large/enormous (wide beams, suffix polish).

## Rules in short
Hex board with radius r. 6 emitters on a ring of 6r border positions, starting at 0, r, 2r, 3r, 4r, 5r. Per tick each emitter gets exactly one instruction: F (+1), B (-1), T (on/off) or -. Active emitters shoot straight beams.
- Exactly 2 beams on a cell: it becomes matter.
- 3 or more beams: the cell is cleared.
- When all pattern cells are matter and no halo cell (neighbour of the pattern) is matter, the pattern is submitted and its cells are cleared.
- Matter outside pattern and halo doesn't matter.
- Exactly `count` submissions required. Score = number of lines.
