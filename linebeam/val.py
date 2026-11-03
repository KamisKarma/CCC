# usage: val.py <name> <results files...>  -> validates RES blocks, prints table vs current best
import sys
sys.path.insert(0,'/home/user/ccc/export_for_colleague/code/python')
from validate_level6_optimized import read_cases, read_programs, simulate
from pathlib import Path
n=sys.argv[1]
cs=read_cases(Path(f'/home/user/ccc/export_for_colleague/inputs/in_level-6_{n}.txt'))
best=read_programs(Path(f'/home/user/ccc/neu/out_level-6_{n}.txt'))
res={}
for fn in sys.argv[2:]:
    cur=None; prog=[]
    for line in open(fn):
        t=line.split()
        if not t: continue
        if t[0]=='RES': cur=int(t[1]); prog=[]
        elif t[0]=='END':
            if cur is not None:
                ok=simulate(cs[cur],prog)['valid']
                if not ok: print('INVALID',fn,cur,len(prog))
                elif cur not in res or len(prog)<len(res[cur]): res[cur]=prog
            cur=None
        elif cur is not None and len(t)==6: prog.append(tuple(t))
tot_gain=0
for i in sorted(res):
    g=len(best[i])-len(res[i]); tot_gain+=max(g,0)
    print(i,'cells',len(cs[i].pattern),'count',cs[i].count,'best',len(best[i]),'new',len(res[i]),'gain',g)
print('total gain',tot_gain)
