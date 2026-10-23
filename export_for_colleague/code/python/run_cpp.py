"""Run the C++ six-emitter beam on the heaviest cases (incumbents in optimized_cpp_claude).

Usage: python run_cpp.py <keys e.g. 3,4> <width> <seed> <procs> [top N per key] [mask]
"""
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

S = Path(__file__).parent
D = S.parent / "levels" / "level6"
EXE = S / "level6_sixbeam_round2p.exe"


def lines_of(p):
    return len([l for l in p.read_text().splitlines() if l.strip()])


def main():
    keys = [int(k) for k in sys.argv[1].split(",")]
    width, seed, procs = int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4])
    top = int(sys.argv[5]) if len(sys.argv) > 5 else 10 ** 6
    mask = sys.argv[6] if len(sys.argv) > 6 else "63"
    jobs = []
    for k in keys:
        fin = next(D.glob(f"in_level-6_{k}-*.txt"))
        out = D / "optimized_cpp_claude" / str(k)
        files = sorted(out.glob("case_*.txt"), key=lambda p: -lines_of(p))[:top]
        for p in files:
            jobs.append((k, fin, out, int(p.stem.split("_")[1])))
    gain = 0
    t0 = time.time()

    def run(job):
        k, fin, out, i = job
        q = out / f"case_{i}.txt"
        before = lines_of(q)
        subprocess.run([str(EXE), str(fin), str(out), str(width), str(i), str(i + 1), mask, str(seed)],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return k, i, before, lines_of(q)

    with ThreadPoolExecutor(procs) as ex:
        for k, i, before, after in ex.map(run, jobs):
            if after < before:
                gain += before - after
                print(f"key{k} case{i}: {before} -> {after} (gain {gain}, {time.time() - t0:.0f}s)", flush=True)
    print(f"DONE keys={keys} width={width} seed={seed}: gain {gain} in {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
