from pathlib import Path
import sys,shutil,subprocess
b=Path(r'C:\Users\david\4aHbg\Diplomarbeit\ccc2026\levels\level6')
sys.path.insert(0,str(b.parent.parent/'solutions'))
from level6 import parse
exe=b.parent.parent/'solutions'/'level6_sixbeam.exe'
for k in range(3):
 dst=b/'optimized_sixrefine'/str(k);dst.mkdir(parents=True,exist_ok=True)
 for p in (b/'optimized_sixbeam'/str(k)).glob('case_*.txt'):
  candidates=[p]+[q for q in (b/'optimized_fivebeam'/str(k)/p.name,b/'optimized_multibeam'/str(k)/p.name) if q.exists()]
  shortest=min(candidates,key=lambda q:len(q.read_text().splitlines()));shutil.copy2(shortest,dst/p.name)
for k in range(2):
 inp=next(b.glob(f'in_level-6_{k}-*.txt'))
 subprocess.run([str(exe),str(inp),str(b/'optimized_sixrefine'/str(k)),'160','0','1000','1','1'],check=True)
inp=next(b.glob('in_level-6_2-*.txt'));cases=parse(inp.read_text());dst=b/'optimized_sixrefine'/'2'
ranked=sorted(range(len(cases)),key=lambda i:len((dst/f'case_{i}.txt').read_text().splitlines()),reverse=True)[:35]
for i in ranked:
 subprocess.run([str(exe),str(inp),str(dst),'64',str(i),str(i+1),'1','1'],check=True)
