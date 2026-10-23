import sys,re,time,subprocess,json
from pathlib import Path
b=Path(r'C:\Users\david\4aHbg\Diplomarbeit\ccc2026\levels\level6');s=b.parent.parent/'solutions';sys.path.insert(0,str(s))
from level6 import parse
cases={};inputs={};rank=[]
for k in (2,3,4):
 inputs[k]=next(b.glob(f'in_level-6_{k}-*.txt'));cases[k]=parse(inputs[k].read_text())
 for i,(r,p,c) in enumerate(cases[k]):
  q=b/'optimized_beam_round2'/str(k)/f'case_{i}.txt';score=len(q.read_text().splitlines());rank.append((score,k,i,len(p),c))
rank.sort(reverse=True);start=time.monotonic();gain=0;trials=0
for attempt in range(2):
 for score,k,i,m,c in rank[:100]:
  if time.monotonic()-start>270:break
  dst=b/'optimized_beam_round2'/str(k);q=dst/f'case_{i}.txt';before=len(q.read_text().splitlines())
  emit=6 if attempt==0 else 5;exe=s/f'level6_{"six" if emit==6 else "five"}beam_round2.exe'
  width=24 if emit==6 else 48;seed=(i+attempt*7)%19+1;mask=1 if emit==6 else 1<<(seed%6)
  out=subprocess.run([str(exe),str(inputs[k]),str(dst),str(width),str(i),str(i+1),str(mask),str(seed)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
  after=len(q.read_text().splitlines());trials+=1;gain+=before-after
  if after<before:print(f'IMPROVED data{k} case{i} {before}->{after} emit{emit} totalgain{gain}',flush=True)
  elif trials%10==0:print(f'PROGRESS trials{trials} gain{gain} elapsed{time.monotonic()-start:.1f}s',flush=True)
 if time.monotonic()-start>270:break
print(f'DONE trials{trials} gain{gain} elapsed{time.monotonic()-start:.1f}s',flush=True)
