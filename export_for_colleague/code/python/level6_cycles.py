"""Shortest programs over the union of observed machine-state transitions.

All transition records preserve six emitter positions, their activation state,
target matter, and skirting matter. Other matter never affects future beams or
pattern detection, so it is safely ignored. BFS over (physical state, pickups)
can repeat efficient cycles and combine routes without changing machine rules.
"""
from collections import deque
from pathlib import Path
import argparse
from validate_level6_optimized import read_cases, read_programs, geometry, FIRE_DIRECTIONS, simulate

BASE = Path(__file__).resolve().parents[1] / 'levels' / 'level6'
NAMES = ['example','small','medium','large','enormous']
DIRECTORIES = ['optimized_beam','optimized_beam_v2','optimized_multibeam',
               'optimized_fivebeam','optimized_sixbeam','optimized_parallel',
               'optimized_augmented','optimized_compact','optimized_cycles',
               'optimized_sixwide','optimized_sixrefine','optimized_augmented_round2',
               'optimized_compact_round2','optimized_beam_round2','optimized_periodic']

def canonical(positions,on,radius):
    positions=list(positions);swaps=0;n=radius*6
    for d,axis in enumerate((3,5,1)):
        reflected=(axis*radius-positions[d+3])%n
        if (positions[d],(on>>d)&1)>(reflected,(on>>(d+3))&1):
            positions[d+3]=(axis*radius-positions[d])%n
            positions[d]=reflected
            a=(on>>d)&1;b=(on>>(d+3))&1
            if a!=b: on ^= (1<<d)|(1<<(d+3))
            swaps |= 1<<d
    return tuple(positions),on,swaps

def transform_action(line,swaps):
    result=list(line);reverse={'F':'B','B':'F','T':'T','-':'-'}
    for d in range(3):
        if swaps>>d&1:
            result[d]=reverse[line[d+3]]
            result[d+3]=reverse[line[d]]
    return tuple(result)

def shortest(case, programs):
    cells, beams = geometry(case.radius)
    pattern = sum(cells[c] for c in case.pattern)
    forbidden = 0
    for r,c in case.pattern:
        for dr,dc in FIRE_DIRECTIONS:
            if (r+dr,c+dc) not in case.pattern:
                forbidden |= cells.get((r+dr,c+dc),0)
    relevant = pattern | forbidden
    initial = (*[i*case.radius for i in range(6)],0,0)
    node_ids = {initial:0}
    edges = [[]]
    unique_edges = set()
    n = 6*case.radius
    for program in programs:
        pos = list(initial[:6]); on = 0; matter = 0; previous = 0;previous_swaps=0
        for line in program:
            for d,cmd in enumerate(line):
                if cmd=='F': pos[d]=(pos[d]+1)%n
                elif cmd=='B': pos[d]=(pos[d]-1)%n
                elif cmd=='T': on ^= 1<<d
            one = two = three = 0
            for d in range(6):
                if on>>d&1:
                    ray=beams[d][pos[d]]
                    three |= two&ray;two |= one&ray;one |= ray
            matter = ((matter|two)&~three)&relevant
            pickup = int((matter&pattern)==pattern and not matter&forbidden)
            if pickup: matter &= ~pattern
            canon_pos,canon_on,swaps=canonical(pos,on,case.radius)
            state = (*canon_pos,canon_on,matter)
            target = node_ids.get(state)
            if target is None:
                target = len(edges);node_ids[state]=target;edges.append([])
            key = previous,target,pickup
            if key not in unique_edges:
                unique_edges.add(key);edges[previous].append((target,pickup,transform_action(line,previous_swaps),previous_swaps^swaps))
            previous = target;previous_swaps=swaps
    queue = deque([(0,0)])
    parent = {(0,0):None}
    while queue:
        node,count=queue.popleft()
        for dest,delta,line,frame_change in edges[node]:
            state = dest,count+delta
            if state in parent: continue
            parent[state]=((node,count),line,frame_change)
            if state[1]==case.count:
                path=[]
                while parent[state] is not None:
                    state,line,frame_change=parent[state];path.append((line,frame_change))
                result=[];frame=0
                for line,frame_change in reversed(path):
                    result.append(transform_action(line,frame));frame^=frame_change
                assert simulate(case,result)['valid']
                return result
            queue.append(state)
    return min(programs,key=len)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--base-dir',type=Path,default=BASE)
    args=parser.parse_args();base=args.base_dir
    total_before=total_after=improved=0
    for fi,name in enumerate(NAMES):
        cases=read_cases(base/f'in_level-6_{fi}-{name}.txt')
        alternatives=[[] for _ in cases]
        for fn in [f'out_level-6_{fi}-{name}.txt',f'candidate-route-{fi}.txt']:
            p=base/fn
            if p.exists():
                for a,prog in zip(alternatives,read_programs(p)): a.append(prog)
        for directory in DIRECTORIES:
            for sub in [name,str(fi)]:
                for path in (base/directory/sub).glob('case_*.txt'):
                    i=int(path.stem[5:]);programs=read_programs(path)
                    if programs and simulate(cases[i],programs[0])['valid']:
                        alternatives[i].append(programs[0])
        for path in (base/'round2_prefixes'/str(fi)).glob('case_*.txt'):
            i=int(path.stem.split('_')[1]);programs=read_programs(path)
            if programs:alternatives[i].append(programs[0])
        outdir=base/'optimized_cycles'/str(fi);outdir.mkdir(parents=True,exist_ok=True)
        before=after=0
        for i,(case,programs) in enumerate(zip(cases,alternatives)):
            best=shortest(case,programs)
            old=min(len(p) for p in programs if simulate(case,p)['valid']);before+=old;after+=len(best)
            if len(best)<old:
                improved+=1
                print(f'{name} case{i}: {old}->{len(best)}',flush=True)
            (outdir/f'case_{i}.txt').write_text('\n'.join(' '.join(row) for row in best)+'\n',encoding='utf-8')
        print(f'{name}: {before}->{after} saved={before-after}',flush=True)
        total_before+=before;total_after+=after
    print(f'TOTAL {total_before}->{total_after}; saved {total_before-total_after}; improved {improved}',flush=True)

if __name__=='__main__': main()
