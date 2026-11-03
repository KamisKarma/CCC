// chain: exhaustive gap-1 / gap-2 submission-chain search (boards with pattern+halo <= 64 bits).
// After a submission, pattern+halo are empty, so the search state is only the emitter config.
// Usage: chain <input> <best_out> <cases> [cap=N] [from=all|first] [tl=seconds per case]
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long u64;
static const int FD[6][2] = {{0,2},{1,1},{1,-1},{0,-2},{-1,-1},{-1,1}};
static const int RD6[6][2] = {{-1,1},{0,2},{1,1},{1,-1},{0,-2},{-1,-1}};
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
map<string,double> KV; double kv(const string& k, double d) { auto it = KV.find(k); return it == KV.end() ? d : it->second; }

struct Cfg { uint8_t pos[6]; uint8_t on; };
static inline u64 key(const Cfg& c) { u64 k = c.on; for (int e = 0; e < 6; e++) k = k * 64 + c.pos[e]; return k; }

struct Chain {
    int r, n, count; u64 P = 0, H = 0; vector<u64> mask; // [e*n+p]
    void init(const Pat& pt) {
        r = pt.r; n = 6*r; count = pt.count;
        vector<pair<int,int>> per; int y = r, x = 0;
        for (int d = 0; d < 6; d++) for (int s = 0; s < r; s++) { per.push_back({y,x}); y += RD6[d][0]; x += RD6[d][1]; }
        set<pair<int,int>> perset(per.begin(), per.end()), interior;
        for (int yy = 1; yy < 2*r; yy++) { int lo = abs(r-yy), hi = 4*r-lo; for (int xx = lo+2; xx < hi; xx += 2) interior.insert({yy,xx}); }
        set<pair<int,int>> halo;
        for (auto& c : pt.P) for (int d = 0; d < 6; d++) { pair<int,int> q = {c.first+FD[d][0], c.second+FD[d][1]}; if (interior.count(q) && !pt.P.count(q)) halo.insert(q); }
        map<pair<int,int>,int> id; for (auto& c : pt.P) { int k = id.size(); id[c] = k; } int nP = id.size();
        for (auto& c : halo) { int k = id.size(); id[c] = k; }
        if (id.size() > 64) { fprintf(stderr, "too many bits\n"); exit(1); }
        for (int i = 0; i < (int)id.size(); i++) (i < nP ? P : H) |= 1ULL << i;
        mask.assign(6*n, 0);
        for (int e = 0; e < 6; e++) for (int p = 0; p < n; p++) {
            int yy = per[p].first + FD[e][0], xx = per[p].second + FD[e][1];
            while (interior.count({yy,xx}) || perset.count({yy,xx})) { auto it = id.find({yy,xx}); if (it != id.end()) mask[e*n+p] |= 1ULL << it->second; yy += FD[e][0]; xx += FD[e][1]; }
        }
    }
    inline void apply(const Cfg& a, int mv, Cfg& c) const {
        c = a; for (int e = 0; e < 6; e++) { int o = (mv >> (2*e)) & 3; if (o == 1) c.pos[e] = (c.pos[e]+1) % n; else if (o == 2) c.pos[e] = (c.pos[e]+n-1) % n; else if (o == 3) c.on ^= 1 << e; }
    }
    // simulate full program -> submission ticks and configs
    void sim(const vector<uint16_t>& prog, vector<int>& subT, vector<Cfg>& subC) const {
        Cfg c{}; for (int e = 0; e < 6; e++) c.pos[e] = e*r; u64 m = 0;
        for (int t = 0; t < (int)prog.size(); t++) {
            Cfg d; apply(c, prog[t], d); c = d; u64 one = 0, two = 0, three = 0;
            for (int e = 0; e < 6; e++) if (c.on >> e & 1) { u64 b = mask[e*n+c.pos[e]]; three |= two & b; two |= one & b; one |= b; }
            m = (m | two) & ~three;
            if ((m & P) == P && !(m & H)) { subT.push_back(t+1); subC.push_back(c); m &= ~P; }
        }
    }
    struct Edge { u64 to; Cfg c; uint16_t m1, m2; uint8_t gap; };
    // all gap-1 and gap-2 edges from config a (pattern+halo empty)
    vector<Edge> edges(const Cfg& a, int maxEdges) const {
        vector<Edge> out; unordered_set<u64> seen;
        // per-emitter options for step 1
        for (int m1 = 0; m1 < 4096; m1++) {
            Cfg c1; apply(a, m1, c1); u64 one = 0, two = 0, three = 0;
            for (int e = 0; e < 6; e++) if (c1.on >> e & 1) { u64 b = mask[e*n+c1.pos[e]]; three |= two & b; two |= one & b; one |= b; }
            u64 M1 = two & ~three;
            if ((M1 & P) == P && !(M1 & H)) { u64 k = key(c1); if (seen.insert(k*2).second) out.push_back({k, c1, (uint16_t)m1, 0, 1}); continue; }
            u64 need = P & ~M1, keep = P & M1, hm = M1 & H;
            // quick bound: step 2 needs every 'need' cell at exactly 2 beams
            // enumerate step 2 with recursion over emitters and three-pruning
            u64 b4[6][4]; Cfg c2opt[6][4];
            for (int e = 0; e < 6; e++) for (int o = 0; o < 4; o++) {
                int p = c1.pos[e]; bool on = c1.on >> e & 1; if (o == 1) p = (p+1) % n; else if (o == 2) p = (p+n-1) % n; else if (o == 3) on = !on;
                b4[e][o] = on ? mask[e*n+p] : 0; c2opt[e][o].pos[0] = p; c2opt[e][o].on = on;
            }
            u64 O[7], T[7], R[7]; O[0] = T[0] = R[0] = 0; int ops[6];
            function<void(int)> rec = [&](int e) {
                if (e == 6) {
                    u64 M2 = (M1 | T[6]) & ~R[6];
                    if ((M2 & P) == P && !(M2 & H)) {
                        Cfg c2; c2.on = 0; for (int q = 0; q < 6; q++) { c2.pos[q] = c2opt[q][ops[q]].pos[0]; if (c2opt[q][ops[q]].on) c2.on |= 1 << q; }
                        u64 k = key(c2); if (seen.insert(k*2+1).second && (int)out.size() < maxEdges) { int m2 = 0; for (int q = 0; q < 6; q++) m2 |= ops[q] << (2*q); out.push_back({k, c2, (uint16_t)m1, (uint16_t)m2, 2}); }
                    }
                    return;
                }
                for (int o = 0; o < 4; o++) {
                    u64 b = b4[e][o]; u64 r3 = R[e] | (T[e] & b);
                    if (r3 & keep) continue;            // would clear a made pattern cell
                    O[e+1] = O[e] | b; T[e+1] = T[e] | (O[e] & b); R[e+1] = r3; ops[e] = o;
                    // remaining emitters e+1..5 can add at most (5-e) beams; a need cell with 0 beams so far needs 2
                    if (e >= 4) { u64 zero = need & ~O[e+1]; if (e == 5 ? zero : 0) continue; if (e == 4 && zero) continue; }
                    rec(e+1);
                }
            };
            rec(0);
            (void)hm;
        }
        return out;
    }
};

int main(int argc, char** argv) {
    string in = argv[1], bestf = argv[2], cases = argv[3];
    for (int i = 4; i < argc; i++) { string a = argv[i]; auto q = a.find('='); KV[a.substr(0,q)] = atof(a.substr(q+1).c_str()); }
    auto pats = readInput(in); auto best = readOutput(bestf);
    vector<int> list; { stringstream ss(cases); string tok; while (getline(ss, tok, ',')) { auto d = tok.find('-'); if (d == string::npos) list.push_back(stoi(tok)); else for (int i = stoi(tok.substr(0,d)); i <= stoi(tok.substr(d+1)); i++) list.push_back(i); } }
    int cap = kv("cap", 40), maxE = kv("maxe", 2000); double tl = kv("tl", 120);
    static const char* OP[4] = {"-","F","B","T"};
    for (int ci : list) {
        const Pat& pt = pats[ci]; if (pt.count < 2) continue;
        Chain ch; ch.init(pt); vector<int> subT; vector<Cfg> subC; ch.sim(best[ci], subT, subC);
        int L = best[ci].size(); if ((int)subT.size() != pt.count) { printf("BADSIM %d\n", ci); continue; }
        auto t0 = chrono::steady_clock::now();
        unordered_map<u64, vector<Chain::Edge>> cache; long expansions = 0;
        int bestTotal = L; vector<uint16_t> bestProg;
        int jmax = kv("from", 0) > 0 ? 1 : pt.count - 1;
        for (int j = 1; j <= jmax; j++) {
            int base = subT[j-1], need = pt.count - j, budget = bestTotal - base - 1;
            if (need <= 0 || budget < need) continue;
            // layered by cost: layer[t] = states (cfg, k, parent idx, edge)
            struct St { Cfg c; int k; int par; uint16_t m1, m2; uint8_t gap; int t; };
            vector<St> all; vector<vector<int>> layer(budget + 3);
            all.push_back({subC[j-1], 0, -1, 0, 0, 0, 0}); layer[0].push_back(0);
            unordered_map<u64, int> bestK; // key*32+k -> visited
            int goal = -1; bool timeout = false;
            for (int t = 0; t <= budget && goal < 0 && !timeout; t++) {
                auto& Lt = layer[t];
                sort(Lt.begin(), Lt.end(), [&](int a, int b) { return all[a].k > all[b].k; });
                if ((int)Lt.size() > cap) Lt.resize(cap);
                for (int si : Lt) {
                    St s = all[si];
                    if (t + (need - s.k) > budget) continue;
                    u64 k0 = key(s.c);
                    auto it = cache.find(k0);
                    if (it == cache.end()) { it = cache.emplace(k0, ch.edges(s.c, maxE)).first; expansions++; }
                    for (auto& ed : it->second) {
                        int nt = t + ed.gap, nk = s.k + 1; if (nt > budget) continue;
                        u64 vk = ed.to * 32 + nk; auto v = bestK.find(vk); if (v != bestK.end() && v->second <= nt) continue; bestK[vk] = nt;
                        all.push_back({ed.c, nk, si, ed.m1, ed.m2, ed.gap, nt});
                        if (nk == need) { if (goal < 0 || nt < all[goal].t) goal = all.size() - 1; }
                        else layer[nt].push_back(all.size() - 1);
                    }
                    if (chrono::duration<double>(chrono::steady_clock::now() - t0).count() > tl) { timeout = true; break; }
                }
                // goal found at cost <= t+2; make sure no cheaper goal remains in later processing: costs are >= t+1, accept
            }
            if (goal >= 0 && base + all[goal].t < bestTotal) {
                vector<uint16_t> tail; for (int g = goal; all[g].par >= 0; g = all[g].par) { if (all[g].gap == 2) { tail.push_back(all[g].m2); } tail.push_back(all[g].m1); }
                reverse(tail.begin(), tail.end());
                vector<uint16_t> np(best[ci].begin(), best[ci].begin() + base); np.insert(np.end(), tail.begin(), tail.end());
                bestTotal = np.size(); bestProg = np;
            }
            if (timeout) break;
        }
        double dt = chrono::duration<double>(chrono::steady_clock::now() - t0).count();
        if (!bestProg.empty()) {
            printf("RES %d %d was %d (%.1fs, %ld exp)\n", ci, (int)bestProg.size(), L, dt, expansions);
            for (auto mv : bestProg) for (int e = 0; e < 6; e++) printf("%s%s", OP[(mv >> (2*e)) & 3], e < 5 ? " " : "\n");
            printf("END\n");
        } else printf("NONE %d best %d (%.1fs, %ld exp)\n", ci, L, dt, expansions);
        fflush(stdout);
    }
}
