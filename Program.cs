using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Numerics;
using System.Text;
using System.Threading;
using System.Threading.Tasks;

class Pat { public int r, count; public string[] rows = Array.Empty<string>(); }

class Board
{
    public static readonly int[] DR = { 0, 1, 1, 0, -1, -1 };
    public static readonly int[] DC = { 2, 1, -1, -2, -1, 1 };
    public int r, H, Wc, n;
    public char[][] g;
    public List<(int y, int x)> ring = new();
    public int[] start = new int[6];
    public int[][] beam; // [e*n+p] -> cell ids y*Wc+x
    static readonly Dictionary<int, Board> cache = new();
    public static Board Get(int r) { lock (cache) { if (!cache.TryGetValue(r, out var b)) { b = new Board(r); cache[r] = b; } return b; } }
    Board(int r)
    {
        this.r = r; H = 2 * r + 1; Wc = 4 * r + 1;
        g = new char[H][];
        for (int i = 0; i < H; i++)
        {
            int d = Math.Abs(i - r), nn = 2 * r + 1 - d; bool edge = i == 0 || i == 2 * r;
            var row = new char[Wc]; Array.Fill(row, '-');
            for (int j = 0; j < nn; j++) row[d + 2 * j] = (edge || j == 0 || j == nn - 1) ? '*' : 'O';
            g[i] = row;
        }
        for (int k = 0; k <= r; k++) ring.Add((0, r + 2 * k));
        for (int i = 1; i <= r; i++) ring.Add((i, 3 * r + i));
        for (int i = 1; i <= r; i++) ring.Add((r + i, 4 * r - i));
        for (int k = 1; k <= r; k++) ring.Add((2 * r, 3 * r - 2 * k));
        for (int i = 1; i <= r; i++) ring.Add((2 * r - i, r - i));
        for (int i = 1; i < r; i++) ring.Add((r - i, i));
        n = ring.Count;
        var corners = new (int, int)[] { (r, 0), (0, r), (0, 3 * r), (r, 4 * r), (2 * r, 3 * r), (2 * r, r) };
        for (int e = 0; e < 6; e++) start[e] = ring.IndexOf(corners[e]);
        beam = new int[6 * n][];
        for (int e = 0; e < 6; e++)
            for (int p = 0; p < n; p++)
            {
                var l = new List<int>();
                var (y, x) = ring[p]; y += DR[e]; x += DC[e];
                while (y >= 0 && y < H && x >= 0 && x < Wc && (g[y][x] == 'O' || g[y][x] == 'M')) { l.Add(y * Wc + x); y += DR[e]; x += DC[e]; }
                beam[e * n + p] = l.ToArray();
            }
    }
}

static class Sim
{
    static readonly int[] NY = { 0, 0, 1, 1, -1, -1 }, NX = { 2, -2, 1, -1, 1, -1 };
    public static (List<int> pat, List<int> halo) PatHalo(Board b, string[] rows)
    {
        var pat = new List<int>();
        for (int y = 0; y < rows.Length; y++) for (int x = 0; x < rows[y].Length; x++) if (rows[y][x] == 'M') pat.Add(y * b.Wc + x);
        var ps = new HashSet<int>(pat); var hs = new HashSet<int>(); var halo = new List<int>();
        foreach (var c in pat)
        {
            int y = c / b.Wc, x = c % b.Wc;
            for (int k = 0; k < 6; k++)
            {
                int ny = y + NY[k], nx = x + NX[k];
                if (ny < 0 || ny >= b.H || nx < 0 || nx >= b.Wc) continue;
                int id = ny * b.Wc + nx;
                if (!ps.Contains(id) && hs.Add(id)) halo.Add(id);
            }
        }
        return (pat, halo);
    }
    public static List<int> SubTimes(int r, string[] rows, List<byte[]> prog, int stopAt)
    {
        var b = Board.Get(r);
        var (pat, halo) = PatHalo(b, rows);
        var M = new bool[b.H * b.Wc];
        var hits = new int[b.H * b.Wc];
        var pos = (int[])b.start.Clone(); var on = new bool[6];
        var res = new List<int>(); var touched = new List<int>();
        for (int t = 0; t < prog.Count; t++)
        {
            var line = prog[t];
            for (int e = 0; e < 6; e++)
            {
                if (line[e] == 1) pos[e] = (pos[e] + 1) % b.n;
                else if (line[e] == 2) pos[e] = (pos[e] - 1 + b.n) % b.n;
                else if (line[e] == 3) on[e] = !on[e];
            }
            touched.Clear();
            for (int e = 0; e < 6; e++)
            {
                if (!on[e]) continue;
                foreach (var c in b.beam[e * b.n + pos[e]]) { if (hits[c] == 0) touched.Add(c); hits[c]++; }
            }
            foreach (var c in touched) { if (hits[c] == 2) M[c] = true; else if (hits[c] >= 3) M[c] = false; hits[c] = 0; }
            bool ok = true;
            foreach (var c in pat) if (!M[c]) { ok = false; break; }
            if (ok) foreach (var c in halo) if (M[c]) { ok = false; break; }
            if (ok) { res.Add(t + 1); foreach (var c in pat) M[c] = false; if (res.Count >= stopAt) break; }
        }
        return res;
    }
    // exact port of level5.simulate
    public static int Simulate(int r, string[] rows, List<byte[]> prog)
    {
        var b = Board.Get(r);
        var (pat, halo) = PatHalo(b, rows);
        var M = new bool[b.H * b.Wc];
        var hits = new int[b.H * b.Wc];
        var pos = (int[])b.start.Clone(); var on = new bool[6];
        int count = 0; var touched = new List<int>();
        foreach (var line in prog)
        {
            for (int e = 0; e < 6; e++)
            {
                if (line[e] == 1) pos[e] = (pos[e] + 1) % b.n;
                else if (line[e] == 2) pos[e] = (pos[e] - 1 + b.n) % b.n;
                else if (line[e] == 3) on[e] = !on[e];
            }
            touched.Clear();
            for (int e = 0; e < 6; e++)
            {
                if (!on[e]) continue;
                foreach (var c in b.beam[e * b.n + pos[e]]) { if (hits[c] == 0) touched.Add(c); hits[c]++; }
            }
            foreach (var c in touched) { if (hits[c] == 2) M[c] = true; else if (hits[c] >= 3) M[c] = false; hits[c] = 0; }
            bool ok = true;
            foreach (var c in pat) if (!M[c]) { ok = false; break; }
            if (ok) foreach (var c in halo) if (M[c]) { ok = false; break; }
            if (ok) { count++; foreach (var c in pat) M[c] = false; }
        }
        return count;
    }
}

class Searcher
{
    readonly Board b; readonly int count, nP, nR, Wd, n;
    readonly ulong[] Pm, Hm, masks; readonly bool[] maskNZ; readonly int[] pe;
    static readonly int[] PE1 = { 0, 0, 0, 0, 1, 1, 1, 2, 2, 3, 3, 4, 0, 1, 2 }, PE2 = { 1, 2, 4, 5, 2, 3, 5, 3, 4, 4, 5, 5, 3, 4, 5 };
    static readonly int[][] PairsByE2;
    static Searcher()
    {
        PairsByE2 = new int[6][];
        for (int e = 0; e < 6; e++) { var l = new List<int>(); for (int k = 0; k < 15; k++) if (PE2[k] == e) l.Add(k); PairsByE2[e] = l.ToArray(); }
    }
    public long wP = 8, wH = 12, wS = 1, wMin = 2, wE = 3, wL1 = 0, wL2 = 0, wL3 = 0, wPar = 0, wC = 0, nuMax = 24; int curNu; bool useDbl; int dblPen; public int W = 100; public ulong seed = 1;
    public void SetW(Dictionary<string, long> d)
    {
        foreach (var kv in d)
            switch (kv.Key)
            {
                case "wP": wP = kv.Value; break; case "wH": wH = kv.Value; break; case "wS": wS = kv.Value; break; case "wMin": wMin = kv.Value; break;
                case "wE": wE = kv.Value; break; case "wL1": wL1 = kv.Value; break; case "wL2": wL2 = kv.Value; break; case "wL3": wL3 = kv.Value; break; case "wPar": wPar = kv.Value; break; case "wC": wC = kv.Value; break; case "la": la = kv.Value; break; case "laK": laK = (int)kv.Value; break; case "dbl": useDbl = kv.Value >= 0; dblPen = (int)kv.Value; break; case "nuMax": nuMax = kv.Value; break;
                case "W": W = (int)kv.Value; break; case "seed": seed = (ulong)kv.Value; break;
            }
    }
    int[] lineOf = Array.Empty<int>(); int[][] posOfLine = Array.Empty<int[]>(); int[] nLines = new int[3]; ulong[][] lineMask = Array.Empty<ulong[]>();
    readonly long[] axTab = new long[48]; readonly long[] lineVal = new long[128];
    public long leaves; public bool Debug;

    public Searcher(Pat pt)
    {
        b = Board.Get(pt.r); count = pt.count; n = b.n; rowsRef = pt.rows;
        var (pat, halo) = Sim.PatHalo(b, pt.rows);
        var inner = new List<int>();
        foreach (var c in halo) { int y = c / b.Wc, x = c % b.Wc; if (b.g[y][x] == 'O') inner.Add(c); }
        nP = pat.Count; nR = nP + inner.Count; Wd = (nR + 63) / 64;
        var id = new Dictionary<int, int>();
        for (int i = 0; i < nP; i++) id[pat[i]] = i;
        for (int i = 0; i < inner.Count; i++) id[inner[i]] = nP + i;
        Pm = new ulong[Wd]; Hm = new ulong[Wd];
        for (int i = 0; i < nR; i++) { if (i < nP) Pm[i >> 6] |= 1UL << (i & 63); else Hm[i >> 6] |= 1UL << (i & 63); }
        masks = new ulong[6 * n * Wd]; maskNZ = new bool[6 * n]; pe = new int[6 * nR];
        Array.Fill(pe, -1);
        for (int e = 0; e < 6; e++) for (int p = 0; p < n; p++)
            {
                foreach (var c in b.beam[e * n + p])
                    if (id.TryGetValue(c, out int k)) { masks[(e * n + p) * Wd + (k >> 6)] |= 1UL << (k & 63); maskNZ[e * n + p] = true; pe[e * nR + k] = p; }
            }
        lineOf = new int[6 * n]; Array.Fill(lineOf, -1); posOfLine = new int[6][]; lineMask = new ulong[3][];
        for (int ax = 0; ax < 3; ax++)
        {
            var key = new Dictionary<int, int>(); var lm = new List<ulong>();
            var pl0 = new List<int>(); var pl3 = new List<int>();
            for (int p = 0; p < n; p++)
            {
                var bc = b.beam[ax * n + p]; if (bc.Length == 0 || !maskNZ[ax * n + p]) continue;
                int kk = bc.Min(); int li = key.Count; key[kk] = li; lineOf[ax * n + p] = li; pl0.Add(p); pl3.Add(-1);
                for (int w = 0; w < Wd; w++) lm.Add(masks[(ax * n + p) * Wd + w]);
            }
            for (int p = 0; p < n; p++)
            {
                var bc = b.beam[(ax + 3) * n + p]; if (bc.Length == 0) continue;
                if (key.TryGetValue(bc.Min(), out int li)) { lineOf[(ax + 3) * n + p] = li; pl3[li] = p; }
            }
            nLines[ax] = key.Count; posOfLine[ax] = pl0.ToArray(); posOfLine[ax + 3] = pl3.ToArray(); lineMask[ax] = lm.ToArray();
        }
    }

    // ---- per-parent context ----
    ulong[] M = Array.Empty<ulong>(); int subs; int pOn; readonly int[] pPos = new int[6];
    readonly int[] vPos = new int[24]; readonly bool[] vOn = new bool[24]; readonly int[] vMask = new int[24];
    ulong[] ge1 = Array.Empty<ulong>(), ge2 = Array.Empty<ulong>(), ge3 = Array.Empty<ulong>(), tmp = Array.Empty<ulong>();
    readonly long[] psum = new long[7]; readonly long[] pmin = new long[7]; readonly int[] ops = new int[6];
    readonly int[] pairTab = new int[15 * 16];
    byte[] dd = Array.Empty<byte>(); int[] unm = Array.Empty<int>();
    int curParent; ulong parentSeed; int nhm; readonly int[] hmList = new int[16]; readonly byte[] axd = new byte[3 * 16 * 16];
    // heap
    long[] hScore = Array.Empty<long>(); ulong[] hHash = Array.Empty<ulong>(); int[] hPar = Array.Empty<int>(); short[] hCombo = Array.Empty<short>(); int hN, K;
    bool solFound; int solParent; int solCombo;

    static ulong Mix(ulong z) { z += 0x9E3779B97F4A7C15UL; z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9UL; z = (z ^ (z >> 27)) * 0x94D049BB133111EBUL; return z ^ (z >> 31); }
    int RD(int a, int c) { int d = Math.Abs(a - c); return Math.Min(d, n - d); }

    void HeapPush(long s, ulong h, int par, short combo)
    {
        if (hN < K)
        {
            int i = hN++;
            while (i > 0) { int p = (i - 1) >> 1; if (hScore[p] <= s) break; hScore[i] = hScore[p]; hHash[i] = hHash[p]; hPar[i] = hPar[p]; hCombo[i] = hCombo[p]; i = p; }
            hScore[i] = s; hHash[i] = h; hPar[i] = par; hCombo[i] = combo;
        }
        else
        {
            if (s <= hScore[0]) return;
            int i = 0;
            while (true)
            {
                int l = 2 * i + 1; if (l >= hN) break;
                int rr = l + 1; int m = (rr < hN && hScore[rr] < hScore[l]) ? rr : l;
                if (hScore[m] >= s) break;
                hScore[i] = hScore[m]; hHash[i] = hHash[m]; hPar[i] = hPar[m]; hCombo[i] = hCombo[m]; i = m;
            }
            hScore[i] = s; hHash[i] = h; hPar[i] = par; hCombo[i] = combo;
        }
    }

    void Rec(int e)
    {
        if (e == 6) { Leaf(); return; }
        int bo = e * Wd, no = (e + 1) * Wd;
        for (int o = 0; o < 4; o++)
        {
            if (solFound) return;
            ops[e] = o;
            int vi = e * 4 + o; int mo = vMask[vi];
            if (mo < 0) { for (int w = 0; w < Wd; w++) { ge1[no + w] = ge1[bo + w]; ge2[no + w] = ge2[bo + w]; ge3[no + w] = ge3[bo + w]; } }
            else
            {
                for (int w = 0; w < Wd; w++)
                {
                    ulong m = masks[mo + w], a1 = ge1[bo + w], a2 = ge2[bo + w];
                    ge3[no + w] = ge3[bo + w] | (a2 & m); ge2[no + w] = a2 | (a1 & m); ge1[no + w] = a1 | m;
                }
            }
            long ps = psum[e], pm = pmin[e];
            foreach (var k in PairsByE2[e]) { int v = pairTab[k * 16 + ops[PE1[k]] * 4 + o]; if (k < 12) { ps += 2 * v; if (v < pm) pm = v; } else if (wPar > 0) { ps += wPar * v; if (v < pm) pm = v; } }
            psum[e + 1] = ps; pmin[e + 1] = pm;
            Rec(e + 1);
        }
    }

    void Leaf()
    {
        leaves++;
        int bo = 6 * Wd; bool full = true, halo = false;
        for (int w = 0; w < Wd; w++)
        {
            ulong nm = (M[w] | ge2[bo + w]) & ~ge3[bo + w]; tmp[w] = nm;
            if ((nm & Pm[w]) != Pm[w]) full = false;
            if ((nm & Hm[w]) != 0) halo = true;
        }
        int ns = subs; int madeP = 0, haloM = 0;
        if (full && !halo)
        {
            ns++; for (int w = 0; w < Wd; w++) tmp[w] &= ~Pm[w];
            if (ns == count) { solFound = true; solParent = curParent; solCombo = Combo(); return; }
        }
        for (int w = 0; w < Wd; w++) { madeP += BitOperations.PopCount(tmp[w] & Pm[w]); haloM += BitOperations.PopCount(tmp[w] & Hm[w]); }
        long ec = 0;
        if (nhm > 0)
        {
            int c0 = (ops[0] * 4 + ops[3]) * 16, c1 = 256 + (ops[1] * 4 + ops[4]) * 16, c2 = 512 + (ops[2] * 4 + ops[5]) * 16; int best = 1000;
            for (int j = 0; j < nhm; j++) { int v = axd[c0 + j]; int v1 = axd[c1 + j]; if (v1 > v) v = v1; v1 = axd[c2 + j]; if (v1 > v) v = v1; if (v < best) best = v; }
            ec = best;
        }
        long lp = wL1 == 0 ? 0 : axTab[ops[0] * 4 + ops[3]] + axTab[16 + ops[1] * 4 + ops[4]] + axTab[32 + ops[2] * 4 + ops[5]];
        if (wC > 0 && curNu > 0 && curNu <= nuMax)
        {
            int o0 = ops[0] * nP, o1 = (4 + ops[1]) * nP, o2 = (8 + ops[2]) * nP, o3 = (12 + ops[3]) * nP, o4 = (16 + ops[4]) * nP, o5 = (20 + ops[5]) * nP;
            long cs = 0;
            for (int k = 0; k < curNu; k++)
            {
                int d0 = dd[o0 + k], d1 = dd[o1 + k], d2 = dd[o2 + k], d3 = dd[o3 + k], d4 = dd[o4 + k], d5 = dd[o5 + k];
                // axis mins
                int A = Math.Min(d0, d3), B = Math.Min(d1, d4), C = Math.Min(d2, d5);
                // second smallest of A,B,C = min over cross-axis pairs of max
                int mx = Math.Max(A, Math.Max(B, C)), mn = Math.Min(A, Math.Min(B, C));
                int cc = A + B + C - mx - mn;
                if (useDbl)
                {
                    int dA = Math.Max(d0, d3), dB = Math.Max(d1, d4), dC = Math.Max(d2, d5);
                    int dm = Math.Min(dA, Math.Min(dB, dC)) + dblPen; if (dm < cc) cc = dm;
                }
                cs += cc;
            }
            lp -= wC * cs;
        }
        long prim = ns * 1000000L + wP * madeP - wH * haloM - wS * psum[6] / 2 - wMin * pmin[6] - wE * ec + lp;
        int combo = Combo();
        long s = prim * 4096 + (long)(Mix(parentSeed + (ulong)combo) >> 52);
        if (hN == K && s <= hScore[0]) return;
        // hash
        ulong h = (ulong)ns * 0x9E3779B97F4A7C15UL;
        int onb = 0;
        for (int e = 0; e < 6; e++) { int vi = e * 4 + ops[e]; h = Mix(h ^ (ulong)vPos[vi] ^ ((ulong)e << 20)); if (vOn[vi]) onb |= 1 << e; }
        h = Mix(h ^ (ulong)onb << 32);
        for (int w = 0; w < Wd; w++) h = Mix(h ^ tmp[w]);
        HeapPush(s, h, curParent, (short)combo);
    }
    int Combo() => ops[0] | ops[1] << 2 | ops[2] << 4 | ops[3] << 6 | ops[4] << 8 | ops[5] << 10;

    // apply combo to a state (exact)
    void Step(int[] pos, ref int on, ulong[] m, ref int sb, int combo)
    {
        for (int e = 0; e < 6; e++)
        {
            int o = (combo >> (2 * e)) & 3;
            if (o == 1) pos[e] = (pos[e] + 1) % n; else if (o == 2) pos[e] = (pos[e] - 1 + n) % n; else if (o == 3) on ^= 1 << e;
        }
        Span<ulong> g1 = stackalloc ulong[Wd], g2 = stackalloc ulong[Wd], g3 = stackalloc ulong[Wd];
        for (int e = 0; e < 6; e++)
        {
            if ((on >> e & 1) == 0) continue;
            int mo = (e * n + pos[e]) * Wd;
            for (int w = 0; w < Wd; w++) { ulong mm = masks[mo + w]; g3[w] |= g2[w] & mm; g2[w] |= g1[w] & mm; g1[w] |= mm; }
        }
        bool full = true, halo = false;
        for (int w = 0; w < Wd; w++)
        {
            m[w] = (m[w] | g2[w]) & ~g3[w];
            if ((m[w] & Pm[w]) != Pm[w]) full = false;
            if ((m[w] & Hm[w]) != 0) halo = true;
        }
        if (full && !halo) { sb++; for (int w = 0; w < Wd; w++) m[w] &= ~Pm[w]; }
    }

    // run from the state reached after executing prefix (exact); returns suffix only
    public List<byte[]>? RunFrom(List<byte[]> prefix, int maxDepth, Func<bool>? cancel = null)
    {
        var pos = (int[])b.start.Clone(); int on = 0; var m = new ulong[Wd]; int sb = 0;
        foreach (var line in prefix)
        {
            int combo = line[0] | line[1] << 2 | line[2] << 4 | line[3] << 6 | line[4] << 8 | line[5] << 10;
            Step(pos, ref on, m, ref sb, combo);
        }
        if (sb >= count) return null;
        initPos = pos; initOn = on; initM = m; initSubs = sb;
        try { return Run(maxDepth, cancel); } finally { initPos = null; }
    }
    int[]? initPos; int initOn; ulong[]? initM; int initSubs;
    public List<byte[]>? Run(int maxDepth, Func<bool>? cancel = null)
    {
        if (nP == 0) return null;
        K = Math.Max(4 * W, 64);
        hScore = new long[K]; hHash = new ulong[K]; hPar = new int[K]; hCombo = new short[K];
        ge1 = new ulong[7 * Wd]; ge2 = new ulong[7 * Wd]; ge3 = new ulong[7 * Wd]; tmp = new ulong[Wd];
        dd = new byte[24 * nP]; unm = new int[nP];
        int bw = 1;
        var bPos = new int[W * 6]; var bOn = new int[W]; var bSubs = new int[W]; var bM = new ulong[W * Wd];
        var nPos = new int[W * 6]; var nOn = new int[W]; var nSubs = new int[W]; var nM = new ulong[W * Wd];
        for (int e = 0; e < 6; e++) bPos[e] = b.start[e];
        if (initPos != null) { for (int e = 0; e < 6; e++) bPos[e] = initPos[e]; bOn[0] = initOn; bSubs[0] = initSubs; Array.Copy(initM!, 0, bM, 0, Wd); }
        var histPar = new List<int[]>(); var histCombo = new List<short[]>();
        M = new ulong[Wd];
        var order = new int[K]; var seen = new HashSet<ulong>();
        for (int depth = 0; depth < maxDepth; depth++)
        {
            if (cancel != null && (depth & 7) == 0 && cancel()) return null;
            hN = 0; solFound = false;
            for (int i = 0; i < bw && !solFound; i++)
            {
                curParent = i; parentSeed = Mix(seed * 1315423911UL + (ulong)depth * 2654435761UL + (ulong)i);
                Array.Copy(bM, i * Wd, M, 0, Wd); subs = bSubs[i]; pOn = bOn[i];
                for (int e = 0; e < 6; e++) pPos[e] = bPos[i * 6 + e];
                for (int e = 0; e < 6; e++)
                {
                    bool on = (pOn >> e & 1) != 0;
                    for (int o = 0; o < 4; o++)
                    {
                        int vi = e * 4 + o; int p = pPos[e]; bool on2 = on;
                        if (o == 1) p = (p + 1) % n; else if (o == 2) p = (p - 1 + n) % n; else if (o == 3) on2 = !on;
                        vPos[vi] = p; vOn[vi] = on2; vMask[vi] = (on2 && maskNZ[e * n + p]) ? (e * n + p) * Wd : -1;
                    }
                }
                // unmade cells & pair table
                int nu = 0; curNu = 0;
                for (int c = 0; c < nP; c++) if ((M[c >> 6] >> (c & 63) & 1) == 0) unm[nu++] = c;
                curNu = nu;
                if (nu == 0) Array.Clear(pairTab);
                else
                {
                    for (int vi = 0; vi < 24; vi++)
                    {
                        int e = vi >> 2; int off = vOn[vi] ? 0 : 1; int p = vPos[vi]; int bo2 = vi * nP;
                        for (int k = 0; k < nu; k++) { int t = pe[e * nR + unm[k]]; dd[bo2 + k] = (byte)(t < 0 ? 250 : RD(p, t) + off); }
                    }
                    int npairs = wPar > 0 ? 15 : 12;
                    for (int k = 0; k < npairs; k++)
                    {
                        int e1 = PE1[k], e2 = PE2[k];
                        for (int o1 = 0; o1 < 4; o1++) for (int o2 = 0; o2 < 4; o2++)
                            {
                                int a = (e1 * 4 + o1) * nP, c2 = (e2 * 4 + o2) * nP; int best = 255;
                                for (int u = 0; u < nu; u++) { int v = dd[a + u]; int v2 = dd[c2 + u]; if (v2 > v) v = v2; if (v < best) { best = v; if (best == 0) break; } }
                                pairTab[k * 16 + o1 * 4 + o2] = best;
                            }
                    }
                }
                nhm = 0;
                for (int c = nP; c < nR && nhm < 16; c++) if ((M[c >> 6] >> (c & 63) & 1) != 0) hmList[nhm++] = c;
                for (int ax = 0; ax < 3 && nhm > 0; ax++)
                {
                    int e1 = ax, e2 = ax + 3;
                    for (int o1 = 0; o1 < 4; o1++) for (int o2 = 0; o2 < 4; o2++)
                        {
                            int v1i = e1 * 4 + o1, v2i = e2 * 4 + o2; int bo3 = ax * 256 + (o1 * 4 + o2) * 16;
                            for (int j = 0; j < nhm; j++)
                            {
                                int c = hmList[j]; int t1 = pe[e1 * nR + c], t2 = pe[e2 * nR + c];
                                int d1 = t1 < 0 ? 200 : RD(vPos[v1i], t1) + (vOn[v1i] ? 0 : 1);
                                int d2 = t2 < 0 ? 200 : RD(vPos[v2i], t2) + (vOn[v2i] ? 0 : 1);
                                axd[bo3 + j] = (byte)Math.Min(d1, d2);
                            }
                        }
                }
                if (wL1 != 0)
                {
                    for (int ax = 0; ax < 3; ax++)
                    {
                        int nl = nLines[ax]; var val = lineVal;
                        for (int l = 0; l < nl; l++)
                        {
                            int up = 0, ch = 0;
                            for (int w = 0; w < Wd; w++) { ulong lmw = lineMask[ax][l * Wd + w]; up += BitOperations.PopCount(lmw & Pm[w] & ~M[w]); ch += BitOperations.PopCount(lmw & Hm[w] & ~M[w]); }
                            val[l] = up == 0 ? long.MinValue : wL1 * up - wL2 * ch;
                        }
                        int e1 = ax, e2 = ax + 3;
                        for (int o1 = 0; o1 < 4; o1++) for (int o2 = 0; o2 < 4; o2++)
                            {
                                int v1i = e1 * 4 + o1, v2i = e2 * 4 + o2; long best = 0;
                                for (int l = 0; l < nl; l++)
                                {
                                    if (val[l] == long.MinValue) continue;
                                    int t1 = posOfLine[e1][l], t2 = posOfLine[e2][l]; if (t1 < 0 || t2 < 0) continue;
                                    int d1 = RD(vPos[v1i], t1) + (vOn[v1i] ? 0 : 1), d2 = RD(vPos[v2i], t2) + (vOn[v2i] ? 0 : 1);
                                    long v = val[l] - wL3 * Math.Max(d1, d2); if (v > best) best = v;
                                }
                                axTab[ax * 16 + o1 * 4 + o2] = best;
                            }
                    }
                }
                for (int w = 0; w < Wd; w++) { ge1[w] = 0; ge2[w] = 0; ge3[w] = 0; }
                psum[0] = 0; pmin[0] = 1000;
                Rec(0);
            }
            if (solFound)
            {
                var prog = new List<byte[]>();
                prog.Add(ComboOps(solCombo));
                int par = solParent;
                for (int d = histPar.Count - 1; d >= 0; d--) { prog.Add(ComboOps(histCombo[d][par])); par = histPar[d][par]; }
                prog.Reverse();
                return prog;
            }
            if (hN == 0) return null;
            // select top W unique
            for (int i = 0; i < hN; i++) order[i] = i;
            Array.Sort(order, 0, hN, Comparer<int>.Create((x, y) => hScore[y].CompareTo(hScore[x])));
            if (la > 0)
            {
                // 2-ply: re-score the best laK*W unique candidates by the best material gain of one more tick
                seen.Clear(); int kc = 0; int lim = laK * W;
                var cand = new List<int>();
                for (int t = 0; t < hN && kc < lim; t++) { int j = order[t]; if (!seen.Add(hHash[j])) continue; cand.Add(j); kc++; }
                var pos = new int[6]; var m = new ulong[Wd];
                foreach (var j in cand)
                {
                    int par = hPar[j]; int combo = hCombo[j];
                    for (int e = 0; e < 6; e++) pos[e] = bPos[par * 6 + e];
                    int on = bOn[par]; int sb = bSubs[par];
                    Array.Copy(bM, par * Wd, m, 0, Wd);
                    Step(pos, ref on, m, ref sb, combo);
                    long mat = Material(m, sb);
                    long bn = BestNext(pos, on, m, sb);
                    hScore[j] += la * Math.Max(0, bn - mat) * 4096;
                }
                for (int i = 0; i < cand.Count; i++) order[i] = cand[i];
                Array.Sort(order, 0, cand.Count, Comparer<int>.Create((x, y) => hScore[y].CompareTo(hScore[x])));
                hN = cand.Count;
            }
            seen.Clear(); int nw = 0;
            var hp = new int[W]; var hc = new short[W];
            for (int t = 0; t < hN && nw < W; t++)
            {
                int j = order[t];
                if (!seen.Add(hHash[j])) continue;
                int par = hPar[j]; int combo = hCombo[j];
                var pos = new int[6]; for (int e = 0; e < 6; e++) pos[e] = bPos[par * 6 + e];
                int on = bOn[par]; int sb = bSubs[par];
                var m = new ulong[Wd]; Array.Copy(bM, par * Wd, m, 0, Wd);
                Step(pos, ref on, m, ref sb, combo);
                for (int e = 0; e < 6; e++) nPos[nw * 6 + e] = pos[e];
                nOn[nw] = on; nSubs[nw] = sb; Array.Copy(m, 0, nM, nw * Wd, Wd);
                hp[nw] = par; hc[nw] = (short)combo; nw++;
            }
            histPar.Add(hp); histCombo.Add(hc);
            if (Debug && depth % 3 == 0)
            {
                int mp = 0, hm = 0; for (int w = 0; w < Wd; w++) { mp += BitOperations.PopCount(nM[w] & Pm[w]); hm += BitOperations.PopCount(nM[w] & Hm[w]); }
                Console.WriteLine($"d{depth} subs {nSubs[0]} madeP {mp}/{nP} haloM {hm}/{nR - nP} on {Convert.ToString(nOn[0], 2)} score {hScore[order[0]] >> 12}");
            }
            (bPos, nPos) = (nPos, bPos); (bOn, nOn) = (nOn, bOn); (bSubs, nSubs) = (nSubs, bSubs); (bM, nM) = (nM, bM);
            bw = nw;
        }
        return null;
    }
    // ---- L=1 static configurations: every tick submits ----
    // returns best program (setup + count ticks) or null
    public List<byte[]>? StaticSolve()
    {
        // per emitter choices: -1 = off, else ring position p with maskNZ
        var choices = new List<int>[6];
        for (int e = 0; e < 6; e++) { choices[e] = new List<int> { -1 }; for (int p = 0; p < n; p++) if (maskNZ[e * n + p]) choices[e].Add(p); }
        int bestCost = int.MaxValue; int[]? best = null;
        var cur = new int[6];
        var g1 = new ulong[7 * Wd]; var g2 = new ulong[7 * Wd]; var g3 = new ulong[7 * Wd];
        void Rec2(int e)
        {
            int bo = e * Wd, no = (e + 1) * Wd;
            if (e == 6)
            {
                for (int w = 0; w < Wd; w++)
                {
                    ulong ex2 = g2[bo + w] & ~g3[bo + w];
                    if ((ex2 & Pm[w]) != Pm[w]) return;
                    if ((ex2 & Hm[w]) != 0) return;
                }
                int cost = 0;
                for (int k = 0; k < 6; k++) if (cur[k] >= 0) cost = Math.Max(cost, RD(b.start[k], cur[k]) + 1);
                if (cost < bestCost) { bestCost = cost; best = (int[])cur.Clone(); }
                return;
            }
            foreach (var p in choices[e])
            {
                cur[e] = p;
                if (p < 0) { for (int w = 0; w < Wd; w++) { g1[no + w] = g1[bo + w]; g2[no + w] = g2[bo + w]; g3[no + w] = g3[bo + w]; } }
                else
                {
                    int mo = (e * n + p) * Wd; bool dead = false;
                    for (int w = 0; w < Wd; w++)
                    {
                        ulong m = masks[mo + w], a1 = g1[bo + w], a2 = g2[bo + w];
                        g3[no + w] = g3[bo + w] | (a2 & m); g2[no + w] = a2 | (a1 & m); g1[no + w] = a1 | m;
                        if ((g3[no + w] & Pm[w]) != 0) dead = true;
                    }
                    if (dead) continue;
                }
                Rec2(e + 1);
            }
        }
        Rec2(0);
        if (best == null) return null;
        // build program: move each on-emitter to its position (shortest way), toggle on in last setup tick
        var prog = new List<byte[]>();
        var pos = (int[])b.start.Clone();
        int T = bestCost; // setup ticks, last one includes toggles
        for (int t = 0; t < T; t++)
        {
            var line = new byte[6];
            for (int e = 0; e < 6; e++)
            {
                if (best[e] < 0) continue;
                if (t == T - 1) { line[e] = 3; continue; }
                int d = (best[e] - pos[e] + n) % n;
                if (d == 0) continue;
                if (d <= n - d) { line[e] = 1; pos[e] = (pos[e] + 1) % n; } else { line[e] = 2; pos[e] = (pos[e] - 1 + n) % n; }
            }
            prog.Add(line);
        }
        for (int c = 1; c < count; c++) prog.Add(new byte[6]);
        return prog;
    }
    // ---- period-2 cycles: configs A,B alternate ----
    struct EPair { public int iA, iB; public int posA, onA, op; public int cost; }
    public long cycNodes;
    public List<byte[]>? Cycle2Solve(int bestLen)
    {
        // per emitter candidate pairs
        var cand = new List<EPair>[6];
        for (int e = 0; e < 6; e++)
        {
            var dict = new Dictionary<long, EPair>();
            for (int p = 0; p < n; p++) for (int on = 0; on < 2; on++) for (int op = 0; op < 4; op++)
                    {
                        int pb = p, onb = on;
                        if (op == 1) pb = (p + 1) % n; else if (op == 2) pb = (p - 1 + n) % n; else if (op == 3) onb = 1 - on;
                        int iA = (on == 1 && maskNZ[e * n + p]) ? p : -1, iB = (onb == 1 && maskNZ[e * n + pb]) ? pb : -1;
                        int cost = RD(b.start[e], p) + on;
                        if (iA < 0 && iB < 0) cost = 0; // effectively off: keep it off at start
                        long key = (long)(iA + 1) * 1000 + (iB + 1);
                        if (!dict.TryGetValue(key, out var ex) || cost < ex.cost)
                            dict[key] = new EPair { iA = iA, iB = iB, posA = p, onA = on, op = op, cost = cost };
                    }
            cand[e] = dict.Values.OrderBy(x => x.cost).ToList();
            // the all-off option: emitter stays off at its start, op none
            for (int k = 0; k < cand[e].Count; k++) if (cand[e][k].iA < 0 && cand[e][k].iB < 0) cand[e][k] = new EPair { iA = -1, iB = -1, posA = b.start[e], onA = 0, op = 0, cost = 0 };
        }
        int[] order = { 0, 3, 1, 4, 2, 5 };
        var aG1 = new ulong[7 * Wd]; var aG2 = new ulong[7 * Wd]; var aG3 = new ulong[7 * Wd];
        var bG1 = new ulong[7 * Wd]; var bG2 = new ulong[7 * Wd]; var bG3 = new ulong[7 * Wd];
        var chosen = new EPair[6];
        var found = new List<(int est, EPair[] cfg)>();
        int limitEst = bestLen; // estimated total must beat this
        void Add(ulong[] g1, ulong[] g2, ulong[] g3, int bo, int no, int idx, int e)
        {
            if (idx < 0) { for (int w = 0; w < Wd; w++) { g1[no + w] = g1[bo + w]; g2[no + w] = g2[bo + w]; g3[no + w] = g3[bo + w]; } return; }
            int mo = (e * n + idx) * Wd;
            for (int w = 0; w < Wd; w++)
            {
                ulong m = masks[mo + w], a1 = g1[bo + w], a2 = g2[bo + w];
                g3[no + w] = g3[bo + w] | (a2 & m); g2[no + w] = a2 | (a1 & m); g1[no + w] = a1 | m;
            }
        }
        void Rec3(int lvl, int maxCost)
        {
            cycNodes++;
            int bo = lvl * Wd, no = (lvl + 1) * Wd;
            if (lvl == 6)
            {
                for (int w = 0; w < Wd; w++)
                {
                    ulong exA = aG2[bo + w] & ~aG3[bo + w], exB = bG2[bo + w] & ~bG3[bo + w], g3B = bG3[bo + w];
                    ulong okP = exB | (exA & ~g3B);
                    if ((okP & Pm[w]) != Pm[w]) return;
                    if ((exB & Hm[w]) != 0) return;
                    if ((exA & Hm[w] & ~g3B) != 0) return;
                }
                int est = maxCost + 2 * count - 1;
                if (est < limitEst) { found.Add((est, (EPair[])chosen.Clone())); if (found.Count > 200000) limitEst = Math.Min(limitEst, found.Min(f => f.est) + 2); }
                return;
            }
            if (lvl == 5)
            {
                // last emitter adds <=1 hit per tick: P cells with <1 hit at both ticks are dead
                for (int w = 0; w < Wd; w++) if ((~(aG1[bo + w] | bG1[bo + w]) & Pm[w]) != 0) return;
            }
            int e = order[lvl];
            foreach (var c in cand[e])
            {
                int mc = Math.Max(maxCost, c.cost);
                if (mc + 2 * count - 1 >= limitEst) continue;
                chosen[e] = c;
                Add(aG1, aG2, aG3, bo, no, c.iA, e);
                Add(bG1, bG2, bG3, bo, no, c.iB, e);
                bool dead = false;
                for (int w = 0; w < Wd; w++) if ((bG3[no + w] & Pm[w]) != 0) { dead = true; break; }
                if (dead) continue;
                Rec3(lvl + 1, mc);
            }
        }
        Rec3(0, 0);
        if (found.Count == 0) return null;
        found.Sort((x, y) => x.est.CompareTo(y.est));
        List<byte[]>? best = null;
        int tried = 0;
        foreach (var (est, cfg) in found)
        {
            if (best != null && est >= best.Count + 1) break;
            if (++tried > 400) break;
            for (int phase = 0; phase < 2; phase++)
            {
                var prog = BuildCycleProg(cfg, phase);
                if (prog == null) continue;
                if (best == null || prog.Count < best.Count) best = prog;
            }
        }
        return best;
    }
    List<byte[]>? BuildCycleProg(EPair[] cfg, int phase)
    {
        // phase 0: setup to A; phase 1: setup to B
        var tp = new int[6]; var ton = new int[6]; var opAB = new byte[6]; var opBA = new byte[6];
        for (int e = 0; e < 6; e++)
        {
            var c = cfg[e]; int pb = c.posA, onb = c.onA;
            if (c.op == 1) pb = (c.posA + 1) % n; else if (c.op == 2) pb = (c.posA - 1 + n) % n; else if (c.op == 3) onb = 1 - c.onA;
            opAB[e] = (byte)c.op; opBA[e] = (byte)(c.op == 1 ? 2 : c.op == 2 ? 1 : c.op);
            if (phase == 0) { tp[e] = c.posA; ton[e] = c.onA; } else { tp[e] = pb; ton[e] = onb; }
        }
        int T = 0;
        for (int e = 0; e < 6; e++) T = Math.Max(T, RD(b.start[e], tp[e]) + ton[e]);
        var prog = new List<byte[]>(); var pos = (int[])b.start.Clone();
        for (int t = 0; t < T; t++)
        {
            var line = new byte[6];
            for (int e = 0; e < 6; e++)
            {
                if (t == T - 1 && ton[e] == 1) { line[e] = 3; continue; }
                int d = (tp[e] - pos[e] + n) % n; if (d == 0) continue;
                if (d <= n - d) { line[e] = 1; pos[e] = (pos[e] + 1) % n; } else { line[e] = 2; pos[e] = (pos[e] - 1 + n) % n; }
            }
            prog.Add(line);
        }
        int total = T + 2 * count + 4;
        bool atA = phase == 0;
        while (prog.Count < total) { prog.Add((byte[])(atA ? opAB : opBA).Clone()); atA = !atA; }
        if (T == 0) { /* first tick must be a cycle tick already handled */ }
        var ts = Sim.SubTimes(b.r, rowsRef, prog, count);
        if (ts.Count < count) return null;
        prog.RemoveRange(ts[count - 1], prog.Count - ts[count - 1]);
        return prog;
    }
    public string[] rowsRef = Array.Empty<string>();
    // ---- chains of short segments (1 or 2 ticks per submission) over post-submission configs ----
    static ulong CfgKey(int[] pos, int on) { ulong k = (ulong)on; for (int e = 0; e < 6; e++) k = k * 64 + (ulong)pos[e]; return k; }
    void CfgFromKey(ulong k, int[] pos, out int on) { for (int e = 5; e >= 0; e--) { pos[e] = (int)(k % 64); k /= 64; } on = (int)k; }
    readonly Dictionary<ulong, List<(ulong y, int combo1, int combo2, int len)>> succCache = new();
    public long succEvals;
    // apply ops (combo) to config only
    void ApplyCfg(int[] pos, ref int on, int combo)
    {
        for (int e = 0; e < 6; e++)
        {
            int o = (combo >> (2 * e)) & 3;
            if (o == 1) pos[e] = (pos[e] + 1) % n; else if (o == 2) pos[e] = (pos[e] - 1 + n) % n; else if (o == 3) on ^= 1 << e;
        }
    }
    // hits for a config: returns ge2&~ge3 in ex2, ge3 in g3
    void Hits(int[] pos, int on, ulong[] ex2, ulong[] g3)
    {
        Span<ulong> a1 = stackalloc ulong[Wd], a2 = stackalloc ulong[Wd], a3 = stackalloc ulong[Wd];
        for (int e = 0; e < 6; e++)
        {
            if ((on >> e & 1) == 0 || !maskNZ[e * n + pos[e]]) continue;
            int mo = (e * n + pos[e]) * Wd;
            for (int w = 0; w < Wd; w++) { ulong m = masks[mo + w]; a3[w] |= a2[w] & m; a2[w] |= a1[w] & m; a1[w] |= m; }
        }
        for (int w = 0; w < Wd; w++) { ex2[w] = a2[w] & ~a3[w]; g3[w] = a3[w]; }
    }
    List<(ulong y, int combo1, int combo2, int len)> Successors(ulong x)
    {
        if (succCache.TryGetValue(x, out var cached)) return cached;
        var res = new List<(ulong, int, int, int)>(); var seenY = new HashSet<ulong>();
        var pos0 = new int[6]; CfgFromKey(x, pos0, out int on0);
        var pos1 = new int[6]; var pos2 = new int[6];
        var ex = new ulong[Wd]; var g3 = new ulong[Wd]; var m1 = new ulong[Wd];
        // per emitter variants from config 1 computed per m1
        var vP = new int[24]; var vO = new bool[24]; var vM = new int[24];
        var G1 = new ulong[7 * Wd]; var G2 = new ulong[7 * Wd]; var G3 = new ulong[7 * Wd];
        var opsL = new int[6];
        var S1 = new ulong[7 * Wd]; var S2 = new ulong[7 * Wd]; var S3 = new ulong[7 * Wd]; var Rn = new ulong[Wd]; var H1 = new ulong[Wd];
        for (int c1 = 0; c1 < 4096; c1++)
        {
            Array.Copy(pos0, pos1, 6); int on1 = on0; ApplyCfg(pos1, ref on1, c1);
            Hits(pos1, on1, ex, g3);
            bool full = true, halo = false;
            for (int w = 0; w < Wd; w++)
            {
                m1[w] = ex[w] & ~g3[w];
                if ((m1[w] & Pm[w]) != Pm[w]) full = false;
                if ((m1[w] & Hm[w]) != 0) halo = true;
            }
            if (full && !halo)
            {
                ulong y = CfgKey(pos1, on1);
                if (seenY.Add(y)) res.Add((y, c1, -1, 1));
                continue;
            }
            // enumerate c2
            for (int e = 0; e < 6; e++)
            {
                bool on = (on1 >> e & 1) != 0;
                for (int o = 0; o < 4; o++)
                {
                    int vi = e * 4 + o; int pp = pos1[e]; bool on2 = on;
                    if (o == 1) pp = (pp + 1) % n; else if (o == 2) pp = (pp - 1 + n) % n; else if (o == 3) on2 = !on;
                    vP[vi] = pp; vO[vi] = on2; vM[vi] = (on2 && maskNZ[e * n + pp]) ? (e * n + pp) * Wd : -1;
                }
            }
            for (int w = 0; w < Wd; w++) { G1[w] = 0; G2[w] = 0; G3[w] = 0; }
            // suffix coverage counts (>=1, >=2, >=3) of emitters e..5 over their 4 variants
            for (int w = 0; w < Wd; w++) { S1[6 * Wd + w] = 0; S2[6 * Wd + w] = 0; S3[6 * Wd + w] = 0; }
            for (int e = 5; e >= 0; e--)
                for (int w = 0; w < Wd; w++)
                {
                    ulong u = 0; for (int o = 0; o < 4; o++) { int mo = vM[e * 4 + o]; if (mo >= 0) u |= masks[mo + w]; }
                    ulong a1 = S1[(e + 1) * Wd + w], a2 = S2[(e + 1) * Wd + w], a3 = S3[(e + 1) * Wd + w];
                    S3[e * Wd + w] = a3 | (a2 & u); S2[e * Wd + w] = a2 | (a1 & u); S1[e * Wd + w] = a1 | u;
                }
            for (int w = 0; w < Wd; w++) { Rn[w] = Pm[w] & ~m1[w]; H1[w] = Hm[w] & m1[w]; }
            bool Feasible(int e)
            {
                int bo = e * Wd, so = e * Wd;
                for (int w = 0; w < Wd; w++)
                {
                    ulong g1 = G1[bo + w], g2 = G2[bo + w], g3 = G3[bo + w];
                    ulong s1 = S1[so + w], s2 = S2[so + w], s3 = S3[so + w];
                    if ((Rn[w] & ~g1 & ~s2) != 0) return false;
                    if ((Rn[w] & g1 & ~g2 & ~s1) != 0) return false;
                    if ((H1[w] & ~g1 & ~s3) != 0) return false;
                    if ((H1[w] & g1 & ~g2 & ~s2) != 0) return false;
                    if ((H1[w] & g2 & ~g3 & ~s1) != 0) return false;
                }
                return true;
            }
            if (!Feasible(0)) continue;
            // iterative DFS over 6 emitters
            void R2(int e)
            {
                int bo = e * Wd, no = (e + 1) * Wd;
                if (e < 6 && e > 0 && !Feasible(e)) return;
                if (e == 6)
                {
                    succEvals++;
                    for (int w = 0; w < Wd; w++)
                    {
                        ulong nm = (m1[w] | G2[bo + w]) & ~G3[bo + w];
                        if ((nm & Pm[w]) != Pm[w] || (nm & Hm[w]) != 0) return;
                    }
                    int c2 = opsL[0] | opsL[1] << 2 | opsL[2] << 4 | opsL[3] << 6 | opsL[4] << 8 | opsL[5] << 10;
                    int onn = 0; for (int k = 0; k < 6; k++) { pos2[k] = vP[k * 4 + opsL[k]]; if (vO[k * 4 + opsL[k]]) onn |= 1 << k; }
                    ulong y = CfgKey(pos2, onn);
                    if (seenY.Add(y)) res.Add((y, c1, c2, 2));
                    return;
                }
                for (int o = 0; o < 4; o++)
                {
                    opsL[e] = o; int mo = vM[e * 4 + o];
                    if (mo < 0) { for (int w = 0; w < Wd; w++) { G1[no + w] = G1[bo + w]; G2[no + w] = G2[bo + w]; G3[no + w] = G3[bo + w]; } }
                    else
                    {
                        bool dead = false;
                        for (int w = 0; w < Wd; w++)
                        {
                            ulong m = masks[mo + w], a1 = G1[bo + w], a2 = G2[bo + w];
                            G3[no + w] = G3[bo + w] | (a2 & m); G2[no + w] = a2 | (a1 & m); G1[no + w] = a1 | m;
                            // prune: a P cell already M or needed that now has >=3 hits is lost
                            if ((G3[no + w] & Pm[w]) != 0) dead = true;
                        }
                        if (dead) continue;
                    }
                    R2(e + 1);
                }
            }
            R2(0);
        }
        succCache[x] = res;
        return res;
    }
    readonly Dictionary<ulong, int> chainFail = new();
    int chainNodes;
    // find chain of exactly `need` submissions from x using segments; returns list of combos (lines) or null; maxTicks bound
    List<int>? Chain(ulong x, int need, int maxTicks)
    {
        if (need == 0) return new List<int>();
        if (maxTicks < need) return null;
        if (chainFail.TryGetValue(x, out int f) && f <= need) return null;
        if (++chainNodes > chainNodeLimit) return null;
        var succ = Successors(x);
        // prefer 1-tick edges
        foreach (var (y, c1, c2, len) in succ.OrderBy(t => t.len))
        {
            if (len > maxTicks - (need - 1)) continue;
            if (2 * (need - 1) + len > maxTicks && len == 2 && need > 1 && maxTicks < 2 * need) { }
            var rest = Chain(y, need - 1, maxTicks - len);
            if (rest != null)
            {
                var l = new List<int> { c1 }; if (len == 2) l.Add(c2); l.AddRange(rest); return l;
            }
            if (chainNodes > chainNodeLimit) return null;
        }
        if (!chainFail.TryGetValue(x, out int f2) || need < f2) chainFail[x] = need;
        return null;
    }
    public int chainNodeLimit = 3000;
    // use prefix of program up to j-th submission, then a chain with 2 ticks per submission
    public List<byte[]>? ChainImprove(List<byte[]> prog)
    {
        var ts = Sim.SubTimes(b.r, rowsRef, prog, count);
        if (ts.Count < count) return null;
        List<byte[]>? best = null; int bestLen = prog.Count;
        var pos = (int[])b.start.Clone(); int on = 0;
        int ti = 0;
        for (int t = 0; t < prog.Count && ti < count - 1; t++)
        {
            var line = prog[t];
            int combo = line[0] | line[1] << 2 | line[2] << 4 | line[3] << 6 | line[4] << 8 | line[5] << 10;
            ApplyCfg(pos, ref on, combo);
            if (t + 1 == ts[ti])
            {
                ti++;
                int need = count - ti;
                int budget = bestLen - (t + 1) - 1;
                if (budget < need) break;
                chainFail.Clear(); chainNodes = 0;
                var ch = Chain(CfgKey(pos, on), need, budget);
                if (ch != null && t + 1 + ch.Count < bestLen)
                {
                    var np = prog.Take(t + 1).Select(l => (byte[])l.Clone()).ToList();
                    foreach (var c in ch) np.Add(ComboOps(c));
                    best = np; bestLen = np.Count;
                }
            }
        }
        return best;
    }
    public long la = 0; public int laK = 4;
    long Material(ulong[] m, int sb)
    {
        int mp = 0, hm = 0;
        for (int w = 0; w < Wd; w++) { mp += BitOperations.PopCount(m[w] & Pm[w]); hm += BitOperations.PopCount(m[w] & Hm[w]); }
        return sb * 100000L + wP * mp - wH * hm;
    }
    readonly int[] bnP = new int[24]; readonly int[] bnM = new int[24];
    ulong[] bG1 = Array.Empty<ulong>(), bG2 = Array.Empty<ulong>(), bG3 = Array.Empty<ulong>();
    ulong[] bnMcur = Array.Empty<ulong>(); int bnSubs; long bnBest;
    long BestNext(int[] pos, int on, ulong[] m, int sb)
    {
        if (bG1.Length != 7 * Wd) { bG1 = new ulong[7 * Wd]; bG2 = new ulong[7 * Wd]; bG3 = new ulong[7 * Wd]; }
        for (int e = 0; e < 6; e++)
        {
            bool o0 = (on >> e & 1) != 0;
            for (int o = 0; o < 4; o++)
            {
                int p = pos[e]; bool on2 = o0;
                if (o == 1) p = (p + 1) % n; else if (o == 2) p = (p - 1 + n) % n; else if (o == 3) on2 = !o0;
                bnM[e * 4 + o] = (on2 && maskNZ[e * n + p]) ? (e * n + p) * Wd : -1;
            }
        }
        for (int w = 0; w < Wd; w++) { bG1[w] = 0; bG2[w] = 0; bG3[w] = 0; }
        bnMcur = m; bnSubs = sb; bnBest = long.MinValue;
        BN(0);
        return bnBest;
    }
    void BN(int e)
    {
        int bo = e * Wd;
        if (e == 6)
        {
            bool full = true, halo = false; int mp = 0, hm = 0;
            for (int w = 0; w < Wd; w++)
            {
                ulong nm = (bnMcur[w] | bG2[bo + w]) & ~bG3[bo + w];
                if ((nm & Pm[w]) != Pm[w]) full = false;
                if ((nm & Hm[w]) != 0) halo = true;
                mp += BitOperations.PopCount(nm & Pm[w]); hm += BitOperations.PopCount(nm & Hm[w]);
            }
            long v = (full && !halo) ? (bnSubs + 1) * 100000L - wH * hm : bnSubs * 100000L + wP * mp - wH * hm;
            if (v > bnBest) bnBest = v;
            return;
        }
        int no = (e + 1) * Wd;
        for (int o = 0; o < 4; o++)
        {
            int mo = bnM[e * 4 + o];
            if (mo < 0) { for (int w = 0; w < Wd; w++) { bG1[no + w] = bG1[bo + w]; bG2[no + w] = bG2[bo + w]; bG3[no + w] = bG3[bo + w]; } }
            else
                for (int w = 0; w < Wd; w++)
                {
                    ulong mm = masks[mo + w], a1 = bG1[bo + w], a2 = bG2[bo + w];
                    bG3[no + w] = bG3[bo + w] | (a2 & mm); bG2[no + w] = a2 | (a1 & mm); bG1[no + w] = a1 | mm;
                }
            BN(e + 1);
        }
    }
    static byte[] ComboOps(int c) { var l = new byte[6]; for (int e = 0; e < 6; e++) l[e] = (byte)((c >> (2 * e)) & 3); return l; }
}

static class Program
{
    // L6_ROOT overrides; default is the cs_root folder next to cs_beam (bin/Release/net9.0 -> ../../../../cs_root)
    static readonly string Root = Environment.GetEnvironmentVariable("L6_ROOT")
        ?? Path.GetFullPath(Path.Combine(AppContext.BaseDirectory, "..", "..", "..", "..", "cs_root"));
    static readonly string[] Names = { "1-small", "2-medium", "3-large", "4-enormous" };
    static string InPath(string name) => Path.Combine(Root, "level6", $"in_level-6_{name}.txt");
    static string OutPath(string name) => Path.Combine(Root, "Lösungen", "level6_cs", $"out_level-6_{name}.txt");

    static List<Pat> ParseInput(string path)
    {
        var lines = File.ReadAllLines(path).Where(l => l.Trim().Length > 0).ToList();
        int N = int.Parse(lines[0].Trim()); int i = 1; var res = new List<Pat>();
        for (int k = 0; k < N; k++)
        {
            var p = lines[i].Split(' ', StringSplitOptions.RemoveEmptyEntries).Select(int.Parse).ToArray();
            var pt = new Pat { r = p[0], count = p[3], rows = lines.Skip(i + 1).Take(p[1]).Select(s => s.TrimEnd()).ToArray() };
            res.Add(pt); i += 1 + p[1];
        }
        return res;
    }
    static byte OpCode(string t) => t switch { "-" => 0, "F" => 1, "B" => 2, "T" => 3, _ => throw new Exception("bad op " + t) };
    static readonly string[] OpStr = { "-", "F", "B", "T" };
    static List<List<byte[]>> ParseOutput(string path)
    {
        var text = File.ReadAllText(path).Replace("\r", "").Trim();
        var res = new List<List<byte[]>>();
        foreach (var blk in text.Split("\n\n"))
        {
            var prog = new List<byte[]>();
            foreach (var l in blk.Split('\n')) { var t = l.Split(' ', StringSplitOptions.RemoveEmptyEntries); if (t.Length == 0) continue; prog.Add(t.Select(OpCode).ToArray()); }
            res.Add(prog);
        }
        return res;
    }
    static string Format(List<List<byte[]>> progs)
    {
        var sb = new StringBuilder();
        for (int i = 0; i < progs.Count; i++)
        {
            if (i > 0) sb.Append('\n');
            foreach (var l in progs[i]) { sb.Append(string.Join(" ", l.Select(o => OpStr[o]))); sb.Append('\n'); }
        }
        return sb.ToString();
    }
    static void SaveAtomic(string path, string content)
    {
        var tmp = path + ".tmp";
        for (int attempt = 0; attempt < 50; attempt++)
        {
            try
            {
                File.WriteAllText(tmp, content, new UTF8Encoding(false));
                File.Move(tmp, path, true);
                return;
            }
            catch (Exception ex) { if (attempt == 49) Console.WriteLine("save failed " + path + ": " + ex.Message); Thread.Sleep(100); }
        }
    }

    static void Main(string[] args)
    {
        string mode = args.Length > 0 ? args[0] : "check";
        if (mode == "check")
        {
            foreach (var name in (args.Length > 1 ? args.Skip(1).ToArray() : Names))
            {
                var pats = ParseInput(InPath(name)); var progs = ParseOutput(OutPath(name));
                int tot = 0, bad = 0;
                for (int i = 0; i < pats.Count; i++) { int got = Sim.Simulate(pats[i].r, pats[i].rows, progs[i]); tot += progs[i].Count; if (got != pats[i].count) bad++; }
                Console.WriteLine($"{name}: patterns {pats.Count} programs {progs.Count} total {tot} bad {bad}");
            }
        }
        else if (mode == "mutate")
        {
            // write mutated programs and print C# counts, for cross-check with python
            string name = args[1]; string outp = args[2];
            var pats = ParseInput(InPath(name)); var progs = ParseOutput(OutPath(name));
            var rnd = new Random(42);
            foreach (var pr in progs) foreach (var l in pr) if (rnd.NextDouble() < 0.03) l[rnd.Next(6)] = (byte)rnd.Next(4);
            File.WriteAllText(outp, Format(progs));
            var sb = new StringBuilder();
            for (int i = 0; i < pats.Count; i++) sb.AppendLine(Sim.Simulate(pats[i].r, pats[i].rows, progs[i]).ToString());
            File.WriteAllText(outp + ".cs.txt", sb.ToString());
        }
        else if (mode == "opt")
        {
            // opt <names comma> <seconds> <threads> k=v...
            var names = args[1].Split(',');
            double secs = double.Parse(args[2], System.Globalization.CultureInfo.InvariantCulture); int threads = int.Parse(args[3]);
            Optimize(names, secs, threads, KV(args, 4));
        }
        else if (mode == "tune")
        {
            // tune <name> <step> <threads> k=v...
            string name = args[1]; int step = int.Parse(args[2]); int threads = int.Parse(args[3]); var kv = KV(args, 4);
            var pats = ParseInput(InPath(name)); var progs = ParseOutput(Path.Combine(Root, "Lösungen", "level6", $"out_level-6_{name}.txt"));
            long tminlen = kv.TryGetValue("minlen", out long tml) ? tml : 0;
            var idxs = Enumerable.Range(0, pats.Count).Where(i => i % step == 0 && progs[i].Count >= tminlen).ToArray();
            var res = new int[idxs.Length]; var sw = Stopwatch.StartNew();
            Parallel.For(0, idxs.Length, new ParallelOptions { MaxDegreeOfParallelism = threads }, k =>
            {
                int i = idxs[k];
                var s = new Searcher(pats[i]); s.SetW(kv);
                var r = s.Run(progs[i].Count * 2);
                res[k] = r == null ? -progs[i].Count * 2 : r.Count;
            });
            Console.WriteLine($"tune {name} {string.Join(" ", args.Skip(4))} sum {res.Sum(x => Math.Abs(x))} fails {res.Count(x => x < 0)} min-with-base {Enumerable.Range(0, idxs.Length).Sum(k => res[k] < 0 ? progs[idxs[k]].Count : Math.Min(res[k], progs[idxs[k]].Count))} improved {Enumerable.Range(0, idxs.Length).Count(k => res[k] > 0 && res[k] < progs[idxs[k]].Count)} base {idxs.Sum(i => progs[i].Count)} time {sw.Elapsed.TotalSeconds:F0}s");
        }
        else if (mode == "static")
        {
            foreach (var name in args[1].Split(','))
            {
                var pats = ParseInput(InPath(name)); var progs = ParseOutput(OutPath(name));
                int found = 0, better = 0, gain = 0;
                for (int i = 0; i < pats.Count; i++)
                {
                    var s = new Searcher(pats[i]);
                    var r = s.StaticSolve();
                    if (r == null) continue;
                    found++;
                    int got = Sim.Simulate(pats[i].r, pats[i].rows, r);
                    if (got != pats[i].count) { Console.WriteLine($"static mismatch {name} {i} got {got} want {pats[i].count}"); continue; }
                    if (r.Count < progs[i].Count) { better++; gain += progs[i].Count - r.Count; }
                }
                Console.WriteLine($"{name}: static found {found}/{pats.Count} better {better} gain {gain}");
            }
        }
        else if (mode == "cyc2")
        {
            // cyc2 <names> <threads>: period-2 cycle solver, saves improvements
            var names = args[1].Split(','); int threads = int.Parse(args[2]);
            foreach (var name in names)
            {
                var pats = ParseInput(InPath(name)); var progs = ParseOutput(OutPath(name));
                var other = Path.Combine(Root, "Lösungen", "level6", $"out_level-6_{name}.txt");
                try { var op = ParseOutput(other); for (int i = 0; i < op.Count && i < progs.Count; i++) if (op[i].Count < progs[i].Count && Sim.Simulate(pats[i].r, pats[i].rows, op[i]) == pats[i].count) progs[i] = op[i]; } catch { }
                int before = progs.Sum(p => p.Count); int found = 0, better = 0; long gain = 0; var locker = new object(); var sw = Stopwatch.StartNew();
                Parallel.For(0, pats.Count, new ParallelOptions { MaxDegreeOfParallelism = threads }, i =>
                {
                    var s = new Searcher(pats[i]);
                    int cur; lock (locker) cur = progs[i].Count;
                    var r = s.Cycle2Solve(cur);
                    lock (locker)
                    {
                        if (r != null) found++;
                        if (r != null && r.Count < progs[i].Count && Sim.Simulate(pats[i].r, pats[i].rows, r) == pats[i].count)
                        { better++; gain += progs[i].Count - r.Count; progs[i] = r; }
                    }
                });
                SaveAtomic(OutPath(name), Format(progs));
                Console.WriteLine($"{name}: cyc2 found {found} better {better} gain {gain} total {before} -> {progs.Sum(p => p.Count)} time {sw.Elapsed.TotalSeconds:F0}s");
            }
        }
        else if (mode == "chain")
        {
            // chain <names> <threads> [nodeLimit]
            var names = args[1].Split(','); int threads = int.Parse(args[2]); int lim = args.Length > 3 ? int.Parse(args[3]) : 3000;
            foreach (var name in names)
            {
                var pats = ParseInput(InPath(name)); var progs = ParseOutput(OutPath(name));
                var other = Path.Combine(Root, "Lösungen", "level6", $"out_level-6_{name}.txt");
                try { var op = ParseOutput(other); for (int i = 0; i < op.Count && i < progs.Count; i++) if (op[i].Count < progs[i].Count && Sim.Simulate(pats[i].r, pats[i].rows, op[i]) == pats[i].count) progs[i] = op[i]; } catch { }
                int before = progs.Sum(p => p.Count); int better = 0; long gain = 0; var locker = new object(); var sw = Stopwatch.StartNew(); int done = 0;
                var order = Enumerable.Range(0, pats.Count).OrderByDescending(i => pats[i].count).ToArray();
                Parallel.ForEach(order, new ParallelOptions { MaxDegreeOfParallelism = threads }, i =>
                {
                    if (pats[i].count < 2) return;
                    var s = new Searcher(pats[i]) { chainNodeLimit = lim };
                    List<byte[]> cur; lock (locker) cur = progs[i];
                    var r = s.ChainImprove(cur);
                    lock (locker)
                    {
                        done++;
                        if (r != null && r.Count < progs[i].Count && Sim.Simulate(pats[i].r, pats[i].rows, r) == pats[i].count)
                        { better++; gain += progs[i].Count - r.Count; progs[i] = r; MergeSave(name, pats, progs); }
                        if (done % 10 == 0) Console.WriteLine($"[{sw.Elapsed.TotalSeconds:F0}s] {done} better {better} gain {gain}");
                    }
                });
                Console.WriteLine($"{name}: chain better {better} gain {gain} total {before} -> {progs.Sum(p => p.Count)} time {sw.Elapsed.TotalSeconds:F0}s");
            }
        }
        else if (mode == "one")
        {
            string name = args[1]; int idx = int.Parse(args[2]);
            var pats = ParseInput(InPath(name)); var progs = ParseOutput(OutPath(name));
            var s = new Searcher(pats[idx]) { Debug = true }; s.SetW(KV(args, 3));
            var sw = Stopwatch.StartNew();
            var res = s.Run(progs[idx].Count + 200);
            Console.WriteLine($"cur {progs[idx].Count} new {(res == null ? -1 : res.Count)} time {sw.Elapsed.TotalSeconds:F2}s leaves {s.leaves} count {pats[idx].count} sim {(res == null ? -1 : Sim.Simulate(pats[idx].r, pats[idx].rows, res))}");
        }
    }

    // cross-process safe save: under a named mutex, adopt shorter verified programs from disk, then write
    static void MergeSave(string name, List<Pat> pats, List<List<byte[]>> progs)
    {
        using var mtx = new Mutex(false, "L6cs_" + name);
        try { mtx.WaitOne(); } catch (AbandonedMutexException) { }
        try
        {
            try
            {
                var disk = ParseOutput(OutPath(name));
                if (disk.Count == progs.Count)
                    for (int i = 0; i < disk.Count; i++)
                        if (disk[i].Count < progs[i].Count && Sim.Simulate(pats[i].r, pats[i].rows, disk[i]) == pats[i].count) progs[i] = disk[i];
            }
            catch (Exception ex) { Console.WriteLine("merge read failed: " + ex.Message); }
            SaveAtomic(OutPath(name), Format(progs));
            try
            {
                var bk = Path.Combine(Root, "agent_cs", "best", $"out_level-6_{name}.txt");
                Directory.CreateDirectory(Path.GetDirectoryName(bk)!);
                List<List<byte[]>> merged = progs.Select(x => x).ToList();
                if (File.Exists(bk))
                {
                    var old = ParseOutput(bk);
                    if (old.Count == merged.Count) for (int i = 0; i < old.Count; i++) if (old[i].Count < merged[i].Count && Sim.Simulate(pats[i].r, pats[i].rows, old[i]) == pats[i].count) merged[i] = old[i];
                }
                SaveAtomic(bk, Format(merged));
            }
            catch (Exception ex) { Console.WriteLine("backup failed: " + ex.Message); }
        }
        finally { mtx.ReleaseMutex(); }
    }
    static Dictionary<string, long> KV(string[] args, int from)
    {
        var d = new Dictionary<string, long>();
        for (int i = from; i < args.Length; i++) { var t = args[i].Split('='); d[t[0]] = long.Parse(t[1]); }
        return d;
    }
    static void Optimize(string[] names, double secs, int threads, Dictionary<string, long> kv)
    {
        var sw = Stopwatch.StartNew();
        var jobs = new List<(string name, int idx, int len)>();
        var allPats = new Dictionary<string, List<Pat>>(); var allProgs = new Dictionary<string, List<List<byte[]>>>();
        foreach (var name in names)
        {
            allPats[name] = ParseInput(InPath(name)); allProgs[name] = ParseOutput(OutPath(name));
            var other = Path.Combine(Root, "Lösungen", "level6", $"out_level-6_{name}.txt");
            int took = 0;
            try
            {
                var op = ParseOutput(other);
                if (op.Count == allProgs[name].Count)
                    for (int i = 0; i < op.Count; i++)
                        if (op[i].Count < allProgs[name][i].Count && Sim.Simulate(allPats[name][i].r, allPats[name][i].rows, op[i]) == allPats[name][i].count) { allProgs[name][i] = op[i]; took++; }
            }
            catch (Exception ex) { Console.WriteLine("merge failed " + ex.Message); }
            if (took > 0) SaveAtomic(OutPath(name), Format(allProgs[name]));
            Console.WriteLine($"{name}: start total {allProgs[name].Sum(p => p.Count)} (took {took} from level6)");
            for (int i = 0; i < allPats[name].Count; i++) jobs.Add((name, i, allProgs[name][i].Count));
        }
        jobs = jobs.OrderByDescending(j => j.len).ToList();
        if (kv.TryGetValue("minlen", out long minlen)) jobs = jobs.Where(j => j.len >= minlen).ToList();
        if (kv.TryGetValue("maxlen", out long maxlen)) jobs = jobs.Where(j => j.len <= maxlen).ToList();
        Console.WriteLine($"jobs {jobs.Count}");
        var locker = new object(); int done = 0; long gain = 0;
        Parallel.ForEach(jobs, new ParallelOptions { MaxDegreeOfParallelism = threads }, job =>
        {
            if (sw.Elapsed.TotalSeconds > secs) return;
            var pt = allPats[job.name][job.idx];
            int cur; lock (locker) cur = allProgs[job.name][job.idx].Count;
            var s = new Searcher(pt); s.SetW(kv); s.seed = s.seed * 1000003UL + (ulong)job.idx;
            List<byte[]>? res = null;
            if (kv.TryGetValue("suf", out long sufN) && sufN > 0)
            {
                List<byte[]> curProg; lock (locker) curProg = allProgs[job.name][job.idx];
                int L = curProg.Count;
                for (int k = 1; k <= sufN; k++)
                {
                    int t = (int)((long)L * k / (sufN + 1));
                    if (t <= 0 || t >= L - 1) continue;
                    var prefix = curProg.Take(t).ToList();
                    int bestTot = res?.Count ?? L;
                    var suf = s.RunFrom(prefix, bestTot - t - 1, () => sw.Elapsed.TotalSeconds > secs);
                    if (suf != null && t + suf.Count < bestTot) { prefix.AddRange(suf); res = prefix; }
                }
            }
            else res = s.Run(cur - 1, () => sw.Elapsed.TotalSeconds > secs);
            lock (locker)
            {
                done++;
                if (res != null && res.Count < allProgs[job.name][job.idx].Count)
                {
                    int got = Sim.Simulate(pt.r, pt.rows, res);
                    if (got == pt.count)
                    {
                        gain += allProgs[job.name][job.idx].Count - res.Count;
                        allProgs[job.name][job.idx] = res;
                        MergeSave(job.name, allPats[job.name], allProgs[job.name]);
                    }
                    else Console.WriteLine($"!! sim mismatch {job.name} {job.idx}: got {got} want {pt.count}");
                }
                if (done % 20 == 0) Console.WriteLine($"[{sw.Elapsed.TotalSeconds:F0}s] done {done}/{jobs.Count} gain {gain}");
            }
        });
        foreach (var name in names) Console.WriteLine($"{name}: total {allProgs[name].Sum(p => p.Count)}");
        Console.WriteLine($"finished gain {gain} in {sw.Elapsed.TotalSeconds:F0}s");
    }
}
