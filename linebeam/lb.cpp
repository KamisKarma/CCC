// LineBeam: beam search for CCC 2026 Level 6 with a double-line-aware potential.
// Usage: lb <input> <case_from> <case_to> <W> <maxlen_file|-> [k=v ...] > results
// Output lines: "RES <case> <len>" followed by the program lines, then "END".
#include <bits/stdc++.h>
using namespace std;
typedef unsigned long long u64;

static const int FD[6][2] = {{0,2},{1,1},{1,-1},{0,-2},{-1,-1},{-1,1}};
static const int RD[6][2] = {{-1,1},{0,2},{1,1},{1,-1},{0,-2},{-1,-1}};

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

map<string,double> KV;
double kv(const string& k, double d) { auto it = KV.find(k); return it == KV.end() ? d : it->second; }

template<int NW> struct Solver {
    struct BS { u64 w[NW]; };
    int r, Lr, nc, count;
    vector<BS> beam[6];          // [e][p]
    vector<BS> reach1[6];        // union of beams at p-1,p,p+1
    vector<int> chord[6];        // chord id within family, -1 if empty
    vector<BS> PK[3], HK[3];     // per family chord: pattern / halo cells
    BS P, H;
    double wP, wH, wL, wA, alpha, wL2; u64 seed; int W;

    static inline int pc(const BS& a) { int s = 0; for (int i = 0; i < NW; i++) s += __builtin_popcountll(a.w[i]); return s; }

    void init(const Pat& pt) {
        r = pt.r; Lr = 6 * r; count = pt.count;
        vector<pair<int,int>> per; int y = r, x = 0;
        for (int d = 0; d < 6; d++) for (int s = 0; s < r; s++) { per.push_back({y,x}); y += RD[d][0]; x += RD[d][1]; }
        set<pair<int,int>> perset(per.begin(), per.end());
        map<pair<int,int>,int> id;
        for (int yy = 1; yy < 2*r; yy++) { int lo = abs(r-yy), hi = 4*r-lo; for (int xx = lo+2; xx < hi; xx += 2) { int k = id.size(); id[{yy,xx}] = k; } }
        nc = id.size();
        auto setb = [&](BS& b, int i) { b.w[i>>6] |= 1ULL << (i&63); };
        memset(&P, 0, sizeof P); memset(&H, 0, sizeof H);
        for (auto& c : pt.P) setb(P, id[c]);
        for (auto& c : pt.P) for (int d = 0; d < 6; d++) { pair<int,int> q = {c.first+FD[d][0], c.second+FD[d][1]}; if (id.count(q) && !pt.P.count(q)) setb(H, id[q]); }
        // chord keys per family
        auto key = [&](int f, int yy, int xx) { return f==0 ? yy : (f==1 ? xx-yy : xx+yy); };
        map<int,int> kid[3];
        for (auto& [c, i] : id) for (int f = 0; f < 3; f++) { int k = key(f, c.first, c.second); if (!kid[f].count(k)) { int n = kid[f].size(); kid[f][k] = n; } }
        for (int f = 0; f < 3; f++) { PK[f].assign(kid[f].size(), BS{}); HK[f].assign(kid[f].size(), BS{}); }
        for (int f = 0; f < 3; f++) for (auto& [c, i] : id) { int k = kid[f][key(f,c.first,c.second)]; BS t{}; setb(t, i);
            for (int w = 0; w < NW; w++) { PK[f][k].w[w] |= t.w[w] & P.w[w]; HK[f][k].w[w] |= t.w[w] & H.w[w]; } }
        for (int e = 0; e < 6; e++) {
            beam[e].assign(Lr, BS{}); chord[e].assign(Lr, -1);
            for (int p = 0; p < Lr; p++) {
                int yy = per[p].first + FD[e][0], xx = per[p].second + FD[e][1]; int f = e % 3; int k = -1;
                while (id.count({yy,xx}) || perset.count({yy,xx})) {
                    auto it = id.find({yy,xx}); if (it != id.end()) { setb(beam[e][p], it->second); k = kid[f][key(f,yy,xx)]; }
                    yy += FD[e][0]; xx += FD[e][1];
                }
                chord[e][p] = k;
            }
            reach1[e].assign(Lr, BS{});
            for (int p = 0; p < Lr; p++) for (int d = -1; d <= 1; d++) { const BS& b = beam[e][(p+d+Lr)%Lr]; for (int w = 0; w < NW; w++) reach1[e][p].w[w] |= b.w[w]; }
        }
    }

    struct Node { BS m; uint8_t pos[6]; uint8_t on; uint8_t subs; int parent; uint16_t mv; };
    struct Cand { double s; int parent; uint16_t mv; };

    // apply move code to node -> child state; returns false never
    inline void apply(const Node& a, int mv, Node& c, BS& two, BS& three) {
        c = a; BS one{}; memset(&two, 0, sizeof two); memset(&three, 0, sizeof three);
        for (int e = 0; e < 6; e++) {
            int op = (mv >> (2*e)) & 3;
            if (op == 1) c.pos[e] = (c.pos[e] + 1) % Lr; else if (op == 2) c.pos[e] = (c.pos[e] + Lr - 1) % Lr; else if (op == 3) c.on ^= 1 << e;
            if (c.on >> e & 1) { const BS& b = beam[e][c.pos[e]]; for (int w = 0; w < NW; w++) { three.w[w] |= two.w[w] & b.w[w]; two.w[w] |= one.w[w] & b.w[w]; one.w[w] |= b.w[w]; } }
        }
    }

    // evaluate child (after matter update). returns score
    inline double score(const Node& c) {
        if (c.subs >= count) return 1e18;
        BS miss; for (int w = 0; w < NW; w++) miss.w[w] = P.w[w] & ~c.m.w[w];
        BS hm; for (int w = 0; w < NW; w++) hm.w[w] = H.w[w] & c.m.w[w];
        int made = pc(P) - pc(miss); int haloM = pc(hm);
        double s = c.subs * 1e9 + wP * made - wH * haloM;
        // line potential: for each family, best chord reachable by both emitters next tick
        double lp = 0;
        for (int f = 0; f < 3; f++) {
            int a = f, b = f + 3;
            int ca[3], na = 0, cb[3], nb = 0;
            auto cand = [&](int e, int* out, int& n) {
                if (c.on >> e & 1) { for (int d = -1; d <= 1; d++) { int k = chord[e][(c.pos[e]+d+Lr)%Lr]; if (k >= 0) out[n++] = k; } }
                else { int k = chord[e][c.pos[e]]; if (k >= 0) out[n++] = k; }
            };
            cand(a, ca, na); cand(b, cb, nb);
            double best = 0; bool any = false; BS R;
            for (int i = 0; i < na; i++) for (int j = 0; j < nb; j++) if (ca[i] == cb[j]) {
                if (!any) { any = true; memset(&R, 0, sizeof R);
                    for (int e = 0; e < 6; e++) if (e % 3 != f) { const BS& u = (c.on >> e & 1) ? reach1[e][c.pos[e]] : beam[e][c.pos[e]]; for (int w = 0; w < NW; w++) R.w[w] |= u.w[w]; } }
                int k = ca[i]; int g = 0, hb = 0;
                for (int w = 0; w < NW; w++) { g += __builtin_popcountll(PK[f][k].w[w] & miss.w[w]); hb += __builtin_popcountll(HK[f][k].w[w] & ~c.m.w[w] & ~R.w[w]); }
                double v = g - alpha * hb; if (v > best) best = v;
            }
            lp += best;
        }
        s += wL * lp;
        // attraction: missing cells under current beams
        int at = 0;
        for (int e = 0; e < 6; e++) if (c.on >> e & 1) { const BS& b = beam[e][c.pos[e]]; int t = 0; for (int w = 0; w < NW; w++) t += __builtin_popcountll(b.w[w] & miss.w[w]); at += min(t, 6); }
        s += wA * at;
        return s;
    }

    static inline u64 mix(u64 z) { z += 0x9E3779B97F4A7C15ULL; z = (z ^ (z >> 30)) * 0xBF58476D1CE4E5B9ULL; z = (z ^ (z >> 27)) * 0x94D049BB133111EBULL; return z ^ (z >> 31); }
    u64 hashNode(const Node& c) { u64 h = c.on * 1315423911ULL + c.subs; for (int e = 0; e < 6; e++) h = mix(h ^ c.pos[e]); for (int w = 0; w < NW; w++) h = mix(h ^ (c.m.w[w] & (P.w[w] | H.w[w]))); return h; }

    // returns program (list of move codes), or empty if not found within maxlen
    vector<uint16_t> solve(int maxlen) {
        vector<vector<Node>> layers; layers.push_back({});
        Node s0{}; for (int e = 0; e < 6; e++) s0.pos[e] = e * r; s0.on = 0; s0.subs = 0; s0.parent = -1; s0.mv = 0;
        layers[0].push_back(s0);
        vector<Cand> cands; u64 rng = seed * 0x9E3779B97F4A7C15ULL + 12345;
        for (int depth = 1; depth <= maxlen; depth++) {
            auto& cur = layers.back(); cands.clear();
            int found = -1, foundMv = 0;
            for (int pi = 0; pi < (int)cur.size() && found < 0; pi++) {
                const Node& a = cur[pi];
                for (int mv = 0; mv < 4096; mv++) {
                    Node c; BS two, three; apply(a, mv, c, two, three);
                    for (int w = 0; w < NW; w++) c.m.w[w] = (c.m.w[w] | two.w[w]) & ~three.w[w];
                    bool full = true, clean = true;
                    for (int w = 0; w < NW; w++) { if ((c.m.w[w] & P.w[w]) != P.w[w]) full = false; if (c.m.w[w] & H.w[w]) clean = false; }
                    if (full && clean) { c.subs++; for (int w = 0; w < NW; w++) c.m.w[w] &= ~P.w[w]; if (c.subs >= count) { found = pi; foundMv = mv; break; } }
                    rng = mix(rng); double noise = (rng >> 40) * (1.0 / (1 << 24)) * kv("noise", 0.5);
                    cands.push_back({score(c) + noise, pi, (uint16_t)mv});
                }
            }
            if (found >= 0) {
                vector<uint16_t> prog; prog.push_back(foundMv); int li = layers.size() - 1, idx = found;
                while (li > 0) { prog.push_back(layers[li][idx].mv); idx = layers[li][idx].parent; li--; }
                reverse(prog.begin(), prog.end()); return prog;
            }
            size_t keep = min(cands.size(), (size_t)W * 3);
            nth_element(cands.begin(), cands.begin() + keep - 1, cands.end(), [](const Cand& x, const Cand& y) { return x.s > y.s; });
            sort(cands.begin(), cands.begin() + keep, [](const Cand& x, const Cand& y) { return x.s > y.s; });
            vector<Node> nxt; unordered_set<u64> seen; nxt.reserve(W);
            for (size_t i = 0; i < keep && (int)nxt.size() < W; i++) {
                Node c; BS two, three; apply(cur[cands[i].parent], cands[i].mv, c, two, three);
                for (int w = 0; w < NW; w++) c.m.w[w] = (c.m.w[w] | two.w[w]) & ~three.w[w];
                bool full = true, clean = true;
                for (int w = 0; w < NW; w++) { if ((c.m.w[w] & P.w[w]) != P.w[w]) full = false; if (c.m.w[w] & H.w[w]) clean = false; }
                if (full && clean) { c.subs++; for (int w = 0; w < NW; w++) c.m.w[w] &= ~P.w[w]; }
                u64 h = hashNode(c); if (!seen.insert(h).second) continue;
                c.parent = cands[i].parent; c.mv = cands[i].mv; nxt.push_back(c);
            }
            layers.push_back(move(nxt));
        }
        return {};
    }
};

template<int NW> vector<uint16_t> run(const Pat& p, int W, int maxlen, u64 seed) {
    Solver<NW> s; s.init(p); s.W = W; s.seed = seed;
    s.wP = kv("wP", 10); s.wH = kv("wH", 60); s.wL = kv("wL", 6); s.wA = kv("wA", 1); s.alpha = kv("alpha", 2);
    return s.solve(maxlen);
}

int main(int argc, char** argv) {
    string in = argv[1]; int from = atoi(argv[2]), to = atoi(argv[3]); int W = atoi(argv[4]); string lens = argv[5];
    for (int i = 6; i < argc; i++) { string a = argv[i]; auto q = a.find('='); KV[a.substr(0,q)] = atof(a.substr(q+1).c_str()); }
    auto pats = readInput(in);
    vector<int> maxl(pats.size(), 200);
    if (lens != "-") { ifstream f(lens); int i, l; while (f >> i >> l) if (i < (int)maxl.size()) maxl[i] = l; }
    u64 seed = (u64)kv("seed", 1);
    static const char* OP[4] = {"-","F","B","T"};
    for (int ci = from; ci < to && ci < (int)pats.size(); ci++) {
        const Pat& p = pats[ci]; int cells = 3*p.r*(p.r-1)+1; int ml = maxl[ci] - 1;
        auto t0 = chrono::steady_clock::now();
        vector<uint16_t> prog;
        if (cells <= 64) prog = run<1>(p, W, ml, seed); else if (cells <= 128) prog = run<2>(p, W, ml, seed);
        else if (cells <= 256) prog = run<4>(p, W, ml, seed); else prog = run<7>(p, W, ml, seed);
        double dt = chrono::duration<double>(chrono::steady_clock::now() - t0).count();
        if (prog.empty()) { printf("NONE %d best %d (%.1fs)\n", ci, maxl[ci], dt); fflush(stdout); continue; }
        printf("RES %d %d was %d (%.1fs)\n", ci, (int)prog.size(), maxl[ci], dt);
        for (auto mv : prog) { for (int e = 0; e < 6; e++) printf("%s%s", OP[(mv >> (2*e)) & 3], e < 5 ? " " : "\n"); }
        printf("END\n"); fflush(stdout);
    }
}
