# usage: merge.py <name> <result files...>: validate RES blocks, merge shorter valid programs into neu/out file
import sys
sys.path.insert(0,'/home/user/ccc/export_for_colleague/code/python')
from validate_level6_optimized import read_cases, read_programs, simulate
from pathlib import Path
n=sys.argv[1]
cs=read_cases(Path(f'/home/user/ccc/export_for_colleague/inputs/in_level-6_{n}.txt'))
outp=Path(f'/home/user/ccc/neu/out_level-6_{n}.txt')
best=read_programs(outp)
assert len(best)==len(cs) and all(simulate(c,p)['valid'] for c,p in zip(cs,best))
gain=0
for fn in sys.argv[2:]:
    if fn.startswith('full:'):
        try: other=read_programs(Path(fn[5:]))
        except Exception: continue
        if len(other)==len(best):
            for i,(c,p) in enumerate(zip(cs,other)):
                if len(p)<len(best[i]) and simulate(c,p)['valid']: gain+=len(best[i])-len(p); best[i]=p
        continue
    cur=None; prog=[]
    try: lines=open(fn).read().split('\n')
    except FileNotFoundError: continue
    for line in lines:
        t=line.split()
        if not t: continue
        if t[0]=='RES': cur=int(t[1]); prog=[]
        elif t[0]=='END':
            if cur is not None and len(prog)<len(best[cur]) and simulate(cs[cur],prog)['valid']:
                gain+=len(best[cur])-len(prog); best[cur]=prog
            cur=None
        elif cur is not None and len(t)==6: prog.append(tuple(t))
if gain:
    assert all(simulate(c,p)['valid'] for c,p in zip(cs,best))
    tmp=outp.with_suffix('.tmp'); tmp.write_text('\n\n'.join('\n'.join(' '.join(l) for l in p) for p in best)+'\n'); tmp.replace(outp)
print(n,'gain',gain,'total',sum(len(p) for p in best))
