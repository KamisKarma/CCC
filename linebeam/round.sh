#!/bin/bash
# round.sh <name> <tag> <args...>: run lb2 on all cases of <name> with 4 parallel workers, then merge
D=/home/user/ccc/linebeam; n=$1; tag=$2; shift 2
IN=/home/user/ccc/export_for_colleague/inputs/in_level-6_$n.txt; B=/home/user/ccc/neu/out_level-6_$n.txt
N=$(head -1 $IN | tr -d '\r'); mkdir -p $D/res
for w in 0 1 2 3; do
  cases=$(seq $w 4 $((N-1)) | paste -sd,)
  $D/lb2 $IN $B $cases "$@" > $D/res/$n.$tag.$w.txt &
done
wait
python3 $D/merge.py $n $D/res/$n.$tag.*.txt
