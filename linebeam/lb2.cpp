// LineBeam2: C++ port of the C# beam search heuristic (pair distances, halo clearing, cell-sum)
// plus a clean double-line potential (wLP): reward states where an opposite pair can paint a chord
// next tick while the remaining emitters can cross that chord's halo cells.
// Usage: lb2 <input> <best_out_file> <cases: comma list or a-b> [k=v ...]
//   mode: suf=0 -> search from scratch; suf=K -> also re-search suffixes from K cut points of the best program
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long u64; typedef long long i64;

static const int FD[6][2] = {{0,2},{1,1},{1,-1},{0,-2},{-1,-1},{-1,1}};
static const int RD6[6][2] = {{-1,1},{0,2},{1,1},{1,-1},{0,-2},{-1,-1}};
static const int PE1[15] = {0,0,0,0,1,1,1,2,2,3,3,4,0,1,2}, PE2[15] = {1,2,4,5,2,3,5,3,4,4,5,5,3,4,5};

struct Pat { int r, count; set<pair<int,int>> P; };
vector<Pat> readInput(const string& path) {
    ifstream f(path); string line; vector<string> L;
    while (getline(f, line)) { if (!line.empty() && line.back()=='\r') line.pop_back(); L.push_back(line); }
    int n = stoi(L[0]); size_t cur = 1; vector<Pat> out;
    for (int i = 0; i < n; i++) {
        while (cur < L.size() && L[cur].find_first_not_of(" \t") == string::npos) cur++;
        istringstream h(L[cur]); int r, H, Wd, c; h >> r >> H >> Wd >> c; cur++;
        Pat p; p.r = r; p.count = c;
        for (int y = 0; y < H; y++, cur++) for (int x = 0; x < (int)L[cur].size(); x++) if (L[cur][x]=='M') p.P.insert({y,x});
        out.push_back(p);
    }
    return out;
}
vector<vector<uint16_t>> readOutput(const string& path) {
    ifstream f(path); string line; vector<vector<uint16_t>> progs; vector<uint16_t> cur;
    while (getline(f, line)) {
        istringstream s(line); vector<string> t; string x; while (s >> x) t.push_back(x);
        if (t.empty()) { if (!cur.empty()) { progs.push_back(cur); cur.clear(); } continue; }
        uint16_t mv = 0; for (int e = 0; e < 6; e++) { int o = t[e]=="F" ? 1 : t[e]=="B" ? 2 : t[e]=="T" ? 3 : 0; mv |= o << (2*e); }
        cur.push_back(mv);
    }
    if (!cur.empty()) progs.push_back(cur);
    return progs;
}

map<string,double> KV;
double kv(const string& k, double d) { auto it = KV.find(k); return it == KV.end() ? d : it->second; }
static inline u64 mix(u64 z) { z += 0x9E3779B97F4A7C15ULL; z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL; z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL; return z ^ (z >> 31); }

template<int NW> struct Solver {
    struct BS { u64 w[NW]; };
    int r, n, count, nP, nR;
    BS Pm, Hm;
    vector<BS> masks; vector<char> nz; vector<int> pe; vector<int> lineOf; vector<BS> lineMask[3]; int nLines[3];
    // weights
    i64 wP, wH, wS, wMin, wE, wC, nuMax, dblPen, wLP, alpha; bool useDbl; int W; u64 seed; int lockF = -1, lockFrom = 1, curDepth = 0, lockUntil = 1000;

    static inline int pc(const BS& a) { int s = 0; for (int i = 0; i < NW; i++) s += __builtin_popcountll(a.w[i]); return s; }
    int RDist(int a, int c) const { int d = abs(a - c); return min(d, n - d); }

    void init(const Pat& pt) {
        r = pt.r; n = 6 * r; count = pt.count;
        vector<pair<int,int>> per; int y = r, x = 0;
        for (int d = 0; d < 6; d++) for (int s = 0; s < r; s++) { per.push_back({y,x}); y += RD6[d][0]; x += RD6[d][1]; }
        set<pair<int,int>> perset(per.begin(), per.end());
        set<pair<int,int>> interior;
        for (int yy = 1; yy < 2*r; yy++) { int lo = abs(r-yy), hi = 4*r-lo; for (int xx = lo+2; xx < hi; xx += 2) interior.insert({yy,xx}); }
        set<pair<int,int>> halo;
        for (auto& c : pt.P) for (int d = 0; d < 6; d++) { pair<int,int> q = {c.first+FD[d][0], c.second+FD[d][1]}; if (interior.count(q) && !pt.P.count(q)) halo.insert(q); }
        map<pair<int,int>,int> id; for (auto& c : pt.P) { int k = id.size(); id[c] = k; } nP = id.size();
        for (auto& c : halo) { int k = id.size(); id[c] = k; } nR = id.size();
        memset(&Pm, 0, sizeof Pm); memset(&Hm, 0, sizeof Hm);
        for (int i = 0; i < nR; i++) { if (i < nP) Pm.w[i>>6] |= 1ULL << (i&63); else Hm.w[i>>6] |= 1ULL << (i&63); }
        masks.assign(6*n, BS{}); nz.assign(6*n, 0); pe.assign(6*nR, -1); lineOf.assign(6*n, -1);
        auto key = [&](int f, int yy, int xx) { return f==0 ? yy : (f==1 ? xx-yy : xx+yy); };
        map<int,int> kid[3];
        for (int e = 0; e < 6; e++) for (int p = 0; p < n; p++) {
            int yy = per[p].first + FD[e][0], xx = per[p].second + FD[e][1]; int f = e % 3; bool hitInterior = false; int k0 = INT_MIN;
            while (interior.count({yy,xx}) || perset.count({yy,xx})) {
                if (interior.count({yy,xx})) { hitInterior = true; k0 = key(f,yy,xx); auto it = id.find({yy,xx}); if (it != id.end()) { masks[e*n+p].w[it->second>>6] |= 1ULL << (it->second&63); nz[e*n+p] = 1; pe[e*nR+it->second] = p; } }
                yy += FD[e][0]; xx += FD[e][1];
            }
            if (hitInterior && nz[e*n+p]) { if (!kid[f].count(k0)) { int m = kid[f].size(); kid[f][k0] = m; } lineOf[e*n+p] = kid[f][k0]; }
        }
        for (int f = 0; f < 3; f++) { nLines[f] = kid[f].size(); lineMask[f].assign(nLines[f], BS{}); }
        for (int e = 0; e < 6; e++) for (int p = 0; p < n; p++) if (lineOf[e*n+p] >= 0) lineMask[e%3][lineOf[e*n+p]] = masks[e*n+p];
    }

    // ---- search state ----
    struct Node { BS m; uint8_t pos[6]; uint8_t on, subs; };
    // per parent
    BS M; int subs; int pOn; int pPos[6];
    int vPos[24]; bool vOn[24]; int vMask[24];
    BS ge1[7], ge2[7], ge3[7], tmp;
    i64 psum[7], pmin[7]; int ops[6];
    int pairTab[15*16];
    vector<uint8_t> dd; vector<int> unm; int curNu;
    int nhm; int hmList[16]; uint8_t axd[3*16*16];
    BS reachM[24]; int candN[3][16]; int candK[3][16][3];
    // heap
    vector<i64> hScore; vector<u64> hHash; vector<int> hPar; vector<uint16_t> hCombo; int hN, K;
    bool solFound; int solParent, solCombo; int curParent; u64 parentSeed;

    void heapPush(i64 s, u64 h, int par, uint16_t combo) {
        if (hN < K) {
            int i = hN++;
            while (i > 0) { int p = (i-1) >> 1; if (hScore[p] <= s) break; hScore[i] = hScore[p]; hHash[i] = hHash[p]; hPar[i] = hPar[p]; hCombo[i] = hCombo[p]; i = p; }
            hScore[i] = s; hHash[i] = h; hPar[i] = par; hCombo[i] = combo;
        } else {
            if (s <= hScore[0]) return;
            int i = 0;
            while (true) { int l = 2*i+1; if (l >= hN) break; int rr = l+1; int m = (rr < hN && hScore[rr] < hScore[l]) ? rr : l; if (hScore[m] >= s) break;
                hScore[i] = hScore[m]; hHash[i] = hHash[m]; hPar[i] = hPar[m]; hCombo[i] = hCombo[m]; i = m; }
            hScore[i] = s; hHash[i] = h; hPar[i] = par; hCombo[i] = combo;
        }
    }
    int combo() const { return ops[0] | ops[1] << 2 | ops[2] << 4 | ops[3] << 6 | ops[4] << 8 | ops[5] << 10; }

    void rec(int e) {
        if (e == 6) { leaf(); return; }
        for (int o = 0; o < 4; o++) {
            if (solFound) return;
            ops[e] = o; int vi = e*4+o; int mo = vMask[vi];
            if (lockF >= 0 && e == lockF + 3 && curDepth >= lockFrom) { int va = lockF*4 + ops[lockF]; if (!vOn[va] || !vOn[vi] || lineOf[lockF*n+vPos[va]] < 0 || lineOf[lockF*n+vPos[va]] != lineOf[e*n+vPos[vi]]) continue; }
            if (mo < 0) { ge1[e+1] = ge1[e]; ge2[e+1] = ge2[e]; ge3[e+1] = ge3[e]; }
            else { const BS& m = masks[mo]; for (int w = 0; w < NW; w++) { u64 a1 = ge1[e].w[w], a2 = ge2[e].w[w]; ge3[e+1].w[w] = ge3[e].w[w] | (a2 & m.w[w]); ge2[e+1].w[w] = a2 | (a1 & m.w[w]); ge1[e+1].w[w] = a1 | m.w[w]; } }
            i64 ps = psum[e], pm = pmin[e];
            for (int k = 0; k < 12; k++) if (PE2[k] == e) { int v = pairTab[k*16 + ops[PE1[k]]*4 + o]; ps += 2*v; if (v < pm) pm = v; }
            psum[e+1] = ps; pmin[e+1] = pm;
            rec(e+1);
        }
    }

    void leaf() {
        bool full = true, halo = false;
        for (int w = 0; w < NW; w++) { u64 nm = (M.w[w] | ge2[6].w[w]) & ~ge3[6].w[w]; tmp.w[w] = nm; if ((nm & Pm.w[w]) != Pm.w[w]) full = false; if (nm & Hm.w[w]) halo = true; }
        int ns = subs;
        if (full && !halo) { ns++; for (int w = 0; w < NW; w++) tmp.w[w] &= ~Pm.w[w]; if (ns == count) { solFound = true; solParent = curParent; solCombo = combo(); return; } }
        int madeP = 0, haloM = 0;
        for (int w = 0; w < NW; w++) { madeP += __builtin_popcountll(tmp.w[w] & Pm.w[w]); haloM += __builtin_popcountll(tmp.w[w] & Hm.w[w]); }
        i64 ec = 0;
        if (nhm > 0) {
            int c0 = (ops[0]*4+ops[3])*16, c1 = 256 + (ops[1]*4+ops[4])*16, c2 = 512 + (ops[2]*4+ops[5])*16; int best = 1000;
            for (int j = 0; j < nhm; j++) { int v = axd[c0+j]; int v1 = axd[c1+j]; if (v1 > v) v = v1; v1 = axd[c2+j]; if (v1 > v) v = v1; if (v < best) best = v; }
            ec = best;
        }
        i64 lp = 0;
        if (wC > 0 && curNu > 0 && curNu <= nuMax) {
            const uint8_t* d[6]; for (int e = 0; e < 6; e++) d[e] = &dd[(e*4+ops[e])*nP];
            i64 cs = 0;
            for (int k = 0; k < curNu; k++) {
                int d0 = d[0][k], d1 = d[1][k], d2 = d[2][k], d3 = d[3][k], d4 = d[4][k], d5 = d[5][k];
                int A = min(d0,d3), B = min(d1,d4), C = min(d2,d5);
                int mx = max(A, max(B, C)), mn = min(A, min(B, C)); int cc = A + B + C - mx - mn;
                if (useDbl) { int dm = min(max(d0,d3), min(max(d1,d4), max(d2,d5))) + (int)dblPen; if (dm < cc) cc = dm; }
                cs += cc;
            }
            lp -= wC * cs;
        }
        if (wLP > 0) {
            i64 tot = 0;
            for (int f = 0; f < 3; f++) {
                int ci = ops[f]*4 + ops[f+3]; int nc = candN[f][ci]; if (!nc) continue;
                BS R{}; for (int e = 0; e < 6; e++) if (e % 3 != f) { const BS& u = reachM[e*4+ops[e]]; for (int w = 0; w < NW; w++) R.w[w] |= u.w[w]; }
                i64 best = 0;
                for (int j = 0; j < nc; j++) {
                    const BS& L = lineMask[f][candK[f][ci][j]]; int g = 0, h = 0;
                    for (int w = 0; w < NW; w++) { g += __builtin_popcountll(L.w[w] & Pm.w[w] & ~tmp.w[w]); h += __builtin_popcountll(L.w[w] & Hm.w[w] & ~tmp.w[w] & ~R.w[w]); }
                    i64 v = g - alpha * h; if (v > best) best = v;
                }
                tot += best;
            }
            lp += wLP * tot;
        }
        i64 prim = ns * 1000000LL + wP * madeP - wH * haloM - wS * psum[6] / 2 - wMin * pmin[6] - wE * ec + lp;
        int cb = combo();
        i64 s = prim * 4096 + (i64)(mix(parentSeed + (u64)cb) >> 52);
        if (hN == K && s <= hScore[0]) return;
        u64 h = (u64)ns * 0x9E3779B97F4A7C15ULL; int onb = 0;
        for (int e = 0; e < 6; e++) { int vi = e*4+ops[e]; h = mix(h ^ (u64)vPos[vi] ^ ((u64)e << 20)); if (vOn[vi]) onb |= 1 << e; }
        h = mix(h ^ (u64)onb << 32);
        for (int w = 0; w < NW; w++) h = mix(h ^ tmp.w[w]);
        heapPush(s, h, curParent, (uint16_t)cb);
    }

    void step(Node& s, int cb) {
        for (int e = 0; e < 6; e++) { int o = (cb >> (2*e)) & 3; if (o == 1) s.pos[e] = (s.pos[e]+1) % n; else if (o == 2) s.pos[e] = (s.pos[e]+n-1) % n; else if (o == 3) s.on ^= 1 << e; }
        BS g1{}, g2{}, g3{};
        for (int e = 0; e < 6; e++) { if (!(s.on >> e & 1)) continue; const BS& m = masks[e*n+s.pos[e]]; for (int w = 0; w < NW; w++) { g3.w[w] |= g2.w[w] & m.w[w]; g2.w[w] |= g1.w[w] & m.w[w]; g1.w[w] |= m.w[w]; } }
        bool full = true, halo = false;
        for (int w = 0; w < NW; w++) { s.m.w[w] = (s.m.w[w] | g2.w[w]) & ~g3.w[w]; if ((s.m.w[w] & Pm.w[w]) != Pm.w[w]) full = false; if (s.m.w[w] & Hm.w[w]) halo = true; }
        if (full && !halo) { s.subs++; for (int w = 0; w < NW; w++) s.m.w[w] &= ~Pm.w[w]; }
    }
    Node start() { Node s{}; for (int e = 0; e < 6; e++) s.pos[e] = e * r; return s; }

    // beam search from state s0; returns moves (suffix) or empty
    int depthOff = 0;
    vector<uint16_t> run(const Node& s0, int maxDepth) {
        if (s0.subs >= count || maxDepth <= 0) return {};
        K = max(4*W, 64); hScore.assign(K,0); hHash.assign(K,0); hPar.assign(K,0); hCombo.assign(K,0);
        dd.assign(24*nP, 0); unm.assign(nP, 0);
        vector<Node> cur{s0}, nxt; vector<vector<int>> histPar; vector<vector<uint16_t>> histCombo;
        vector<int> order(K); unordered_set<u64> seen;
        for (int depth = 0; depth < maxDepth; depth++) {
            hN = 0; solFound = false; curDepth = depth + depthOff; int lockSave = lockF; if (curDepth >= lockUntil) lockF = -1;
            for (int i = 0; i < (int)cur.size() && !solFound; i++) {
                curParent = i; parentSeed = mix(seed * 1315423911ULL + (u64)depth * 2654435761ULL + (u64)i);
                const Node& a = cur[i]; M = a.m; subs = a.subs; pOn = a.on; for (int e = 0; e < 6; e++) pPos[e] = a.pos[e];
                for (int e = 0; e < 6; e++) { bool on = pOn >> e & 1; for (int o = 0; o < 4; o++) { int vi = e*4+o; int p = pPos[e]; bool on2 = on;
                    if (o == 1) p = (p+1) % n; else if (o == 2) p = (p+n-1) % n; else if (o == 3) on2 = !on;
                    vPos[vi] = p; vOn[vi] = on2; vMask[vi] = (on2 && nz[e*n+p]) ? e*n+p : -1; } }
                int nu = 0; for (int c = 0; c < nP; c++) if (!(M.w[c>>6] >> (c&63) & 1)) unm[nu++] = c; curNu = nu;
                if (nu == 0) memset(pairTab, 0, sizeof pairTab);
                else {
                    for (int vi = 0; vi < 24; vi++) { int e = vi >> 2; int off = vOn[vi] ? 0 : 1; int p = vPos[vi]; uint8_t* d = &dd[vi*nP];
                        for (int k = 0; k < nu; k++) { int t = pe[e*nR + unm[k]]; d[k] = (uint8_t)(t < 0 ? 250 : RDist(p, t) + off); } }
                    for (int k = 0; k < 12; k++) { int e1 = PE1[k], e2 = PE2[k];
                        for (int o1 = 0; o1 < 4; o1++) for (int o2 = 0; o2 < 4; o2++) { const uint8_t* a1 = &dd[(e1*4+o1)*nP]; const uint8_t* a2 = &dd[(e2*4+o2)*nP]; int best = 255;
                            for (int u = 0; u < nu; u++) { int v = a1[u]; int v2 = a2[u]; if (v2 > v) v = v2; if (v < best) { best = v; if (best == 0) break; } }
                            pairTab[k*16 + o1*4 + o2] = best; } }
                }
                nhm = 0; for (int c = nP; c < nR && nhm < 16; c++) if (M.w[c>>6] >> (c&63) & 1) hmList[nhm++] = c;
                for (int ax = 0; ax < 3 && nhm > 0; ax++) { int e1 = ax, e2 = ax+3;
                    for (int o1 = 0; o1 < 4; o1++) for (int o2 = 0; o2 < 4; o2++) { int v1i = e1*4+o1, v2i = e2*4+o2; int bo = ax*256 + (o1*4+o2)*16;
                        for (int j = 0; j < nhm; j++) { int c = hmList[j]; int t1 = pe[e1*nR+c], t2 = pe[e2*nR+c];
                            int d1 = t1 < 0 ? 200 : RDist(vPos[v1i], t1) + (vOn[v1i] ? 0 : 1); int d2 = t2 < 0 ? 200 : RDist(vPos[v2i], t2) + (vOn[v2i] ? 0 : 1);
                            axd[bo+j] = (uint8_t)min(d1, d2); } } }
                if (wLP > 0) {
                    for (int vi = 0; vi < 24; vi++) { int e = vi >> 2; BS& R = reachM[vi]; memset(&R, 0, sizeof R);
                        if (vOn[vi]) { for (int d = -1; d <= 1; d++) { const BS& m = masks[e*n + (vPos[vi]+d+n)%n]; for (int w = 0; w < NW; w++) R.w[w] |= m.w[w]; } }
                        else { const BS& m = masks[e*n + vPos[vi]]; for (int w = 0; w < NW; w++) R.w[w] |= m.w[w]; } }
                    for (int f = 0; f < 3; f++) for (int o1 = 0; o1 < 4; o1++) for (int o2 = 0; o2 < 4; o2++) {
                        int ci = o1*4+o2; int a = f*4+o1, b = (f+3)*4+o2; int la[3], na = 0, lb[3], nb = 0;
                        auto nextLines = [&](int vi, int e, int* out, int& cnt) { if (vOn[vi]) { for (int d = -1; d <= 1; d++) { int l = lineOf[e*n + (vPos[vi]+d+n)%n]; if (l >= 0) out[cnt++] = l; } } else { int l = lineOf[e*n + vPos[vi]]; if (l >= 0) out[cnt++] = l; } };
                        nextLines(a, f, la, na); nextLines(b, f+3, lb, nb); int c = 0;
                        for (int x = 0; x < na; x++) for (int y = 0; y < nb; y++) if (la[x] == lb[y] && c < 3) candK[f][ci][c++] = la[x];
                        candN[f][ci] = c; }
                }
                memset(&ge1[0], 0, sizeof(BS)); memset(&ge2[0], 0, sizeof(BS)); memset(&ge3[0], 0, sizeof(BS));
                psum[0] = 0; pmin[0] = 1000;
                rec(0);
            }
            lockF = lockSave;
            if (solFound) {
                vector<uint16_t> res; res.push_back((uint16_t)solCombo); int p = solParent;
                for (int d = (int)histPar.size() - 1; d >= 0; d--) { res.push_back(histCombo[d][p]); p = histPar[d][p]; }
                reverse(res.begin(), res.end()); return res;
            }
            if (hN == 0) return {};
            for (int i = 0; i < hN; i++) order[i] = i;
            sort(order.begin(), order.begin() + hN, [&](int x, int y) { return hScore[x] > hScore[y]; });
            seen.clear(); nxt.clear(); vector<int> hp; vector<uint16_t> hc;
            for (int j = 0; j < hN && (int)nxt.size() < W; j++) { int i = order[j]; if (!seen.insert(hHash[i]).second) continue;
                Node c = cur[hPar[i]]; step(c, hCombo[i]); nxt.push_back(c); hp.push_back(hPar[i]); hc.push_back(hCombo[i]); }
            histPar.push_back(hp); histCombo.push_back(hc); swap(cur, nxt);
        }
        return {};
    }
};

template<int NW> void work(const Pat& p, int ci, const vector<uint16_t>& best, int sufK) {
    Solver<NW> s; s.init(p);
    s.wP = kv("wP", 8); s.wH = kv("wH", 100); s.wS = kv("wS", 0); s.wMin = kv("wMin", 2); s.wE = kv("wE", 3); s.wC = kv("wC", 2); s.nuMax = kv("nuMax", 24);
    s.dblPen = kv("dbl", 1); s.useDbl = s.dblPen >= 0; s.wLP = kv("wLP", 0); s.alpha = kv("alpha", 2); s.W = kv("W", 200); s.seed = (u64)kv("seed", 1); s.lockF = kv("lock", -1); s.lockFrom = kv("lockFrom", 1); s.lockUntil = kv("lockUntil", 1000);
    static const char* OP[4] = {"-","F","B","T"};
    int origLen = kv("raw", 0) > 0 ? 999 : (int)best.size(); int bestLen = origLen; vector<uint16_t> bestProg = best; string how;
    auto t0 = chrono::steady_clock::now();
    if (kv("full", 1) > 0) { auto pr = s.run(s.start(), bestLen - 1); if (!pr.empty() && (int)pr.size() < bestLen) { bestLen = pr.size(); bestProg = pr; how = "full"; } }
    if (kv("sweep", 0) > 0) {
        int Lmin = kv("swmin", 2), Lmax = kv("swmax", p.r + 1); int Wsave = s.W; s.W = kv("swW", s.W);
        for (int mask = 1; mask < 8; mask++) for (int dirs = 0; dirs < 8; dirs++) {
            if (kv("swall", 1) > 0 && mask != 7) continue;
            if (mask == 7 && kv("swsame", 1) > 0 && dirs != 0 && dirs != 7) continue;
            bool skip = false; for (int f = 0; f < 3; f++) if (!(mask >> f & 1) && (dirs >> f & 1)) skip = true; if (skip) continue;
            for (int L = Lmin; L <= Lmax; L++) {
                vector<uint16_t> pre; auto st = s.start();
                uint16_t t = 0; for (int f = 0; f < 3; f++) if (mask >> f & 1) { t |= 3 << (2*f); t |= 3 << (2*(f+3)); }
                pre.push_back(t); s.step(st, t);
                for (int i = 1; i < L; i++) {
                    uint16_t mv = 0;
                    for (int f = 0; f < 3; f++) if (mask >> f & 1) {
                        int d = (dirs >> f & 1) ? 1 : -1; int e1 = f, e2 = f + 3; int l1 = s.lineOf[e1*s.n + st.pos[e1]]; if (l1 < 0) continue; int tgt = l1 + d;
                        int o1 = -1, o2 = -1;
                        for (int o = 1; o <= 2; o++) { int p1 = o == 1 ? (st.pos[e1]+1) % s.n : (st.pos[e1]+s.n-1) % s.n; if (s.lineOf[e1*s.n+p1] == tgt) o1 = o;
                                                       int p2 = o == 1 ? (st.pos[e2]+1) % s.n : (st.pos[e2]+s.n-1) % s.n; if (s.lineOf[e2*s.n+p2] == tgt) o2 = o; }
                        if (o1 > 0 && o2 > 0) mv |= (o1 << (2*e1)) | (o2 << (2*e2));
                    }
                    pre.push_back(mv); s.step(st, mv);
                }
                if (st.subs >= s.count) continue;
                auto suf = s.run(st, bestLen - (int)pre.size() - 1);
                if (!suf.empty() && (int)(pre.size() + suf.size()) < bestLen) { pre.insert(pre.end(), suf.begin(), suf.end()); bestProg = pre; bestLen = pre.size(); how += " sweep" + to_string(mask) + "/" + to_string(dirs) + "/" + to_string(L); }
            }
        }
        s.W = Wsave;
    }
    for (int k = 1; k <= sufK; k++) {
        int cut = (int)((i64)bestLen * k / (sufK + 1)); if (cut <= 0 || cut >= bestLen - 1) continue;
        auto st = s.start(); for (int i = 0; i < cut; i++) s.step(st, bestProg[i]);
        auto suf = s.run(st, bestLen - cut - 1);
        if (!suf.empty() && cut + (int)suf.size() < bestLen) { vector<uint16_t> np(bestProg.begin(), bestProg.begin() + cut); np.insert(np.end(), suf.begin(), suf.end()); bestProg = np; bestLen = np.size(); how += " suf" + to_string(k); }
    }
    double dt = chrono::duration<double>(chrono::steady_clock::now() - t0).count();
    if (bestLen < origLen) {
        printf("RES %d %d was %d (%.1fs)%s\n", ci, bestLen, (int)best.size(), dt, how.c_str());
        for (auto mv : bestProg) for (int e = 0; e < 6; e++) printf("%s%s", OP[(mv >> (2*e)) & 3], e < 5 ? " " : "\n");
        printf("END\n");
    } else printf("NONE %d best %d (%.1fs)\n", ci, (int)best.size(), dt);
    fflush(stdout);
}

int main(int argc, char** argv) {
    string in = argv[1], bestf = argv[2], cases = argv[3];
    for (int i = 4; i < argc; i++) { string a = argv[i]; auto q = a.find('='); KV[a.substr(0,q)] = atof(a.substr(q+1).c_str()); }
    auto pats = readInput(in); auto best = readOutput(bestf);
    vector<int> list;
    { stringstream ss(cases); string tok; while (getline(ss, tok, ',')) { auto d = tok.find('-'); if (d == string::npos) list.push_back(stoi(tok)); else for (int i = stoi(tok.substr(0,d)); i <= stoi(tok.substr(d+1)); i++) list.push_back(i); } }
    int sufK = kv("suf", 0);
    for (int ci : list) {
        if (ci >= (int)pats.size()) continue;
        const Pat& p = pats[ci];
        // count bits needed: pattern + halo
        set<pair<int,int>> halo; int r = p.r;
        for (auto& c : p.P) for (int d = 0; d < 6; d++) { pair<int,int> q = {c.first+FD[d][0], c.second+FD[d][1]}; int yy = q.first; if (yy < 1 || yy >= 2*r) continue; int lo = abs(r-yy), hi = 4*r-lo; if (q.second < lo+2 || q.second >= hi || ((q.second - lo) & 1)) continue; if (!p.P.count(q)) halo.insert(q); }
        int bits = p.P.size() + halo.size(); int nw = (bits + 63) / 64;
        switch (nw) { case 1: work<1>(p, ci, best[ci], sufK); break; case 2: work<2>(p, ci, best[ci], sufK); break; case 3: work<3>(p, ci, best[ci], sufK); break;
            case 4: work<4>(p, ci, best[ci], sufK); break; case 5: work<5>(p, ci, best[ci], sufK); break; case 6: work<6>(p, ci, best[ci], sufK); break; default: work<7>(p, ci, best[ci], sufK); }
    }
}
