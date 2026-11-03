#!/bin/bash
# Autopilot 2: rotating rounds of LineBeam (C++, double-line potential) and the C# beam, validate, merge, push.
D=/home/user/ccc/linebeam; REPO=/home/user/ccc; LOG=$D/auto2.log
S=/tmp/claude-0/-home-user/85cf224b-09ab-52fd-a512-c61e1800a6a7/scratchpad
export DOTNET_ROOT=$S/dotnet L6_ROOT=$S/root
END=$((SECONDS + ${1:-21600}))
CFGS=(
  "4-enormous|W=400 wLP=2 suf=2"
  "3-large|W=400 wLP=2 suf=2"
  "4-enormous|W=400 wLP=4 alpha=3 suf=3 full=0"
  "3-large|W=600 wLP=2 suf=3 full=0"
  "CS|4-enormous,3-large,2-medium|suf=3"
  "4-enormous|W=800 wLP=1 suf=1"
  "3-large|W=400 wLP=0 suf=2"
  "2-medium|W=600 wLP=2 suf=3 full=0"
  "4-enormous|W=400 wLP=2 alpha=1 suf=4 full=0"
  "3-large|W=800 wLP=4 alpha=2 suf=1"
)
total() { for n in 2-medium 3-large 4-enormous; do python3 -c "
import sys;sys.path.insert(0,'/home/user/ccc/export_for_colleague/code/python')
from validate_level6_optimized import read_programs;from pathlib import Path
print(sum(map(len,read_programs(Path('$REPO/neu/out_level-6_$n.txt')))))"; done | awk '{s+=$1} END{print s}'; }
best=$(total); echo "$(date +%T) start total=$best" >> $LOG
i=0
while [ $SECONDS -lt $END ]; do
  c=${CFGS[$((i % ${#CFGS[@]}))]}; seed=$((RANDOM * 32768 + RANDOM))
  echo "$(date +%T) round $i: $c seed=$seed" >> $LOG
  if [ "${c%%|*}" = CS ]; then
    rest=${c#CS|}; names=${rest%%|*}; extra=${rest#*|}
    for n in 2-medium 3-large 4-enormous; do cp $REPO/neu/out_level-6_$n.txt "$S/root/Lösungen/level6/"; done
    (cd $S && timeout 1000 $DOTNET_ROOT/dotnet app/L6.dll opt $names 900 4 W=400 wH=100 wC=2 wS=0 dbl=1 $extra seed=$seed) 2>&1 | grep -v '^\[' | tail -3 >> $LOG
    for n in 2-medium 3-large 4-enormous; do python3 $D/merge.py $n "full:$S/root/Lösungen/level6_cs/out_level-6_$n.txt" >> $LOG; done
  else
    n=${c%%|*}; extra=${c#*|}
    timeout 2400 $D/round.sh $n r$i $extra seed=$seed >> $LOG 2>&1
  fi
  tot=$(total)
  if [ -n "$tot" ] && [ "$tot" -lt "$best" ]; then
    (cd $REPO && git add neu && git commit -qm "Level 6: $tot Programmzeilen (Autopilot 2, alle geprüft, bad 0)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01S6CCRzBKAQUqojWucH5JhA" \
      && git pull -q --rebase origin main && git push -q origin main) >> $LOG 2>&1 \
      && { best=$tot; echo "$(date +%T) pushed $tot" >> $LOG; }
  fi
  i=$((i + 1))
done
echo "$(date +%T) done total=$best" >> $LOG
