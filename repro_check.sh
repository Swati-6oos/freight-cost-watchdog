#!/usr/bin/env bash
# Three untouched runs from scratch; outputs must be byte-identical.
set -e
cd "$(dirname "$0")"
for i in 1 2 3; do
  python3 run.py > /dev/null
  cp outputs/output.csv outputs/run_$i.csv
done
sha256sum outputs/run_1.csv outputs/run_2.csv outputs/run_3.csv
diff outputs/run_1.csv outputs/run_2.csv && diff outputs/run_2.csv outputs/run_3.csv \
  && echo "REPRODUCIBLE: 3 runs byte-identical" | tee outputs/repro_check.txt
rm outputs/run_*.csv
