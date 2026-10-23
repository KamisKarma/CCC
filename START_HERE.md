# Start here

**Goal: under 15,100 lines in total (medium + large + enormous).** Current best is in `best/`. Upload these three files.
Shared repo (private, two-way sync every 5 min): https://github.com/d4v1dexe/CCC (ask David for access).

## Run the strongest optimizer immediately (C#, .NET 9)
```
cd cs_beam
dotnet build -c Release
dotnet bin/Release/net9.0/L6.dll check
dotnet bin/Release/net9.0/L6.dll opt 3-large,4-enormous,2-medium 1800 8 W=400 wH=100 wC=2 wS=0 dbl=1 seed=101
```
- The data folder `cs_root/` is found automatically. To use another folder, set the `L6_ROOT` environment variable.
- Improvements are saved continuously to `cs_root/Lösungen/level6_cs/out_level-6_<name>.txt`. Every program is checked with the simulator.
- Other good runs:
  - `... W=400 wH=60 wC=1 wS=0 dbl=0`
  - `suf=3` re-searches the end of existing programs
  - `minlen=50 W=1200` gives the longest programs a wider search
- Use a different `seed=` than David so you don't search the same paths.

## Hand improvements back
- Copy `cs_root/Lösungen/level6_cs/out_level-6_*.txt` to `best/`, or write individual cases to `contrib/<name>/<2|3|4>/case_<i>.txt`.
- Then run `python tools/merge_best.py`. It keeps the shortest valid program per case.
- Push to the repo, or send the three files to David. On our side everything is merged per case, so nothing gets lost.

More details in `README.md` and `notes/TIPPS_FUER_NAECHSTE_KI.md`.
