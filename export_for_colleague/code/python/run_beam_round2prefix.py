import sys,time,subprocess
from pathlib import Path
b=Path(r'C:\Users\david\4aHbg\Diplomarbeit\ccc2026\levels\level6');s=b.parent.parent/'solutions';sys.path.insert(0,str(s))
from level6 import parse
rank=[];inputs={}
for k in (2,3,4):
 inputs[k]=next(b.glob(f'in_level-6_{k}-*.txt'))
 for i,(r,p,c) in enumerate(parse(inputs[k].read_text())):
  q=b/'optimized_beam_round2'/str(k)/f'case_{i}.txt';score=len(q.read_text().splitlines());rank.append((score,k,i,len(p),c))
rank.sort(reverse=True);start=time.monotonic();gain=0
# Highcounts benefit from partialcycle export, largecount1-2 cases from fullcompletion.
for trial,(score,k,i,m,c) in enumerate(rank[:20]):
 if time.monotonic()-start>130:break
 dst=b/'optimized_beam_round2'/str(k);q=dst/f'case_{i}.txt';before=len(q.read_text().splitlines());seed=(i+7)%19+1;pref=b/'round2_prefixes'/str(k)
 out=subprocess.run([str(s/'level6_sixbeam_round2p.exe'),str(inputs[k]),str(dst),'12',str(i),str(i+1),'1',str(seed),str(pref)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
 after=len(q.read_text().splitlines());gain+=before-after
 print(f'TRIAL {trial} data{k} case{i} {before}->{after} gain{gain} elapsed{time.monotonic()-start:.1f}s',flush=True)
print(f'DONE gain{gain} elapsed{time.monotonic()-start:.1f}s',flush=True)
