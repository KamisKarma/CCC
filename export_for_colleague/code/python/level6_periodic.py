"""Constraint search for short repeating six-emitter production cycles."""
import sys,time,math
from pathlib import Path
sys.path.insert(0,r'C:\Users\david\.cache\ccc2026-optimizer-deps')
from ortools.sat.python import cp_model
from validate_level6_optimized import geometry,read_cases,read_programs,simulate,FIRE_DIRECTIONS

BASE=Path(__file__).resolve().parents[1]/'levels'/'level6'
NAMES=['example','small','medium','large','enormous']

def solve(case,length,incumbent,seconds):
    cells,beams=geometry(case.radius);n=6*case.radius
    targets=set(case.pattern);skirts=set()
    for r,c in targets:
        for dr,dc in FIRE_DIRECTIONS:
            k=(r+dr,c+dc)
            if k in cells and k not in targets:skirts.add(k)
    model=cp_model.CpModel()
    p=[[model.NewIntVar(0,n-1,f'p{d}_{t}') for t in range(length)] for d in range(6)]
    on=[[model.NewBoolVar(f'on{d}_{t}') for t in range(length)] for d in range(6)]
    q=[[model.NewIntVar(0,n,f'q{d}_{t}') for t in range(length)] for d in range(6)]
    linked=[(x,1,x) for x in range(n)]+[(x,0,n) for x in range(n)]
    transition=[]
    for x in range(n):
        for enabled in (0,1):
            transition.extend([(x,enabled,(x+move)%n,enabled) for move in (-1,0,1)])
            transition.append((x,enabled,x,1-enabled))
    for d in range(6):
        for t in range(length):
            model.AddAllowedAssignments([p[d][t],on[d][t],q[d][t]],linked)
            if length>1:
                nxt=(t+1)%length
                model.AddAllowedAssignments([p[d][t],on[d][t],p[d][nxt],on[d][nxt]],transition)
    phase_matter=[[] for _ in range(length)]
    for cell in targets|skirts:
        bit=cells[cell];previous=0
        for t in range(length):
            hits=[]
            for d in range(6):
                hit=model.NewBoolVar('h')
                model.AddElement(q[d][t],[int(bool(ray&bit)) for ray in beams[d]]+[0],hit)
                hits.append(hit)
            count=model.NewIntVar(0,6,'count');model.Add(count==sum(hits))
            if cell in targets:
                painted=model.NewBoolVar('painted')
                model.Add(count==2).OnlyEnforceIf(painted)
                model.Add(count!=2).OnlyEnforceIf(painted.Not())
                erased=model.NewBoolVar('erased')
                model.Add(count>=3).OnlyEnforceIf(erased)
                model.Add(count<=2).OnlyEnforceIf(erased.Not())
                matter=model.NewBoolVar('matter')
                model.Add(matter>=painted)
                model.Add(matter<=painted+previous)
                model.Add(matter<=1-erased)
                model.Add(matter>=previous-erased)
                phase_matter[t].append(matter);previous=matter
            else:model.AddAllowedAssignments([count],[(v,) for v in (0,1,3,4,5,6)])
        if cell in targets:model.Add(previous==1)
    for t in range(length-1):model.Add(sum(phase_matter[t])<len(targets))
    distances=[]
    for d in range(6):
        dist=model.NewIntVar(0,n//2,f'dist{d}')
        model.AddElement(p[d][0],[min((v-d*case.radius)%n,(d*case.radius-v)%n) for v in range(n)],dist)
        distances.append(dist)
    startup=model.NewIntVar(0,n//2,'startup')
    model.AddMaxEquality(startup,distances)
    model.Add(startup+1+(case.count-1)*length<len(incumbent))
    model.Minimize(startup)
    solver=cp_model.CpSolver();solver.parameters.max_time_in_seconds=seconds
    solver.parameters.num_search_workers=1;solver.parameters.random_seed=31
    status=solver.Solve(model)
    if status not in (cp_model.OPTIMAL,cp_model.FEASIBLE):return None
    positions=[[solver.Value(p[d][t]) for t in range(length)] for d in range(6)]
    active=[[solver.Value(on[d][t]) for t in range(length)] for d in range(6)]
    now=[d*case.radius for d in range(6)];program=[]
    while any(now[d]!=positions[d][0] for d in range(6)):
        row=[]
        for d in range(6):
            diff=(positions[d][0]-now[d])%n
            cmd='-' if diff==0 else ('F' if diff<=n//2 else 'B')
            row.append(cmd);now[d]=(now[d]+(1 if cmd=='F' else -1 if cmd=='B' else 0))%n
        program.append(tuple(row))
    program.append(tuple('T' if active[d][0] else '-' for d in range(6)))
    for i in range(case.count*length+length):
        a=i%length;b=(i+1)%length;row=[]
        for d in range(6):
            if active[d][a]!=active[d][b]:cmd='T'
            elif positions[d][a]==positions[d][b]:cmd='-'
            elif (positions[d][b]-positions[d][a])%n==1:cmd='F'
            else:cmd='B'
            row.append(cmd)
        program.append(tuple(row))
    result=simulate(case,program,record_ticks=True)
    if result['accepted']<case.count:return None
    program=program[:result['accepted_at'][case.count-1]]
    assert simulate(case,program)['valid']
    return program if len(program)<len(incumbent) else None

def main():
    start=time.monotonic();work=[]
    for fi,name in enumerate(NAMES[:4]):
        cases=read_cases(BASE/f'in_level-6_{fi}-{name}.txt')
        programs=read_programs(BASE/'optimized_final'/f'out_level-6_{fi}-{name}.txt')
        for i,(case,program) in enumerate(zip(cases,programs)):
            if case.count>=3 and len(case.pattern)<=40:
                work.append((case.count*(len(program)/case.count-1),fi,i,case,program))
    work.sort(reverse=True,key=lambda v:v[0]);saved=0
    for _,fi,i,case,program in work:
        if time.monotonic()-start>180:break
        before=len(program)
        for length in range(1,min(4,(len(program)-2)//case.count)+1):
            result=solve(case,length,program,0.4 if length==1 else 1.0)
            if result is not None:program=result
        if len(program)<before:
            saved+=before-len(program);out=BASE/'optimized_periodic'/str(fi);out.mkdir(parents=True,exist_ok=True)
            (out/f'case_{i}.txt').write_text('\n'.join(' '.join(row) for row in program)+'\n')
            print(f'{fi}/{i} {before}->{len(program)} total saved {saved}',flush=True)
    print(f'DONE saved={saved} seconds={time.monotonic()-start:.1f}',flush=True)

if __name__=='__main__':main()
