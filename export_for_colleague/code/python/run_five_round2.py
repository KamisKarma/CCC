import sys,time,subprocess
from pathlib import Path
b=Path(r'C:\Users\david\4aHbg\Diplomarbeit\ccc2026\levels\level6');s=b.parent.parent/'solutions';sys.path.insert(0,str(s))
from level6 import parse
inp=next(b.glob('in_level-6_2-*.txt'));cases=parse(inp.read_text());dst=b/'optimized_beam_round2'/'2';rank=[]
for i,(r,p,c) in enumerate(cases):
 if len(p)<=30 and i!=50:
  rank.append((len((dst/f'case_{i}.txt').read_text().splitlines()),i))
rank.sort(reverse=True);start=time.monotonic();gain=0
for old,i in rank[:35]:
 if time.monotonic()-start>85:break
 q=dst/f'case_{i}.txt';before=len(q.read_text().splitlines());seed=(i%11)+3;mask=1<<(2+i%4)
 out=subprocess.run([str(s/'level6_fivebeam_round2.exe'),str(inp),str(dst),'24',str(i),str(i+1),str(mask),str(seed)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 after=len(q.read_text().splitlines());gain+=before-after
 if after<before:print(f'IMPROVE medium{i} {before}->{after} gain{gain}',flush=True)
print(f'DONE FIVE gain{gain} elapsed{time.monotonic()-start:.1f}s',flush=True)
