#!/usr/bin/env bash
# Explicit development-only capture from the same publisher endpoints as the verifier.
set -euo pipefail
work=$1
mkdir "$work" "$work/receipts"
receipts="$work/receipts"
get() {
    curl --fail --silent --show-error --retry 2 --connect-timeout 12 --max-time 90 \
        --max-filesize "$3" "$1" -o "$2"
}
node verification/g7-core-batch1/capture-valet-history.mjs "$work/valet"
cp "$work/valet/"G7-CA-*.json "$receipts/"
for pair in G7-CA-01:36100104 G7-CA-11:14100287; do
    mapping=${pair%:*}
    table=${pair#*:}
    get "https://www150.statcan.gc.ca/n1/tbl/csv/$table-eng.zip" "$work/$table.zip" 134217728
    python verification/g7-core-batch1/capture-statcan-history.py "$mapping" "$work/$table.zip" "$receipts/$mapping.json"
done
for country in DE FR IT; do
    get "https://data-api.ecb.europa.eu/service/data/IRS/M.$country.L.L40.CI.0000.EUR.N.Z?format=csvdata" "$work/$country.csv" 2000000
    python verification/g7-core-batch1/capture-ecb-yield-history.py "$country" "$receipts/G7-$country-23.json" --publisher-csv "$work/$country.csv"
done
get 'https://www.bankofengland.co.uk/boeapps/database/_iadb-fromshowcolumns.asp?csv.x=yes&Datefrom=01%2FJan%2F1963&Dateto=now&SeriesCodes=IUDMNPY&UsingCodes=Y&CSVF=CT' "$work/gb.csv" 2000000
python -m scripts.capture_boe_yield_history "$work/gb.csv" "$receipts/G7-GB-23.json"
get 'https://www.esri.cao.go.jp/jp/sna/data/data_list/sokuhou/files/2026/qe262_2/tables/gaku-jk2622.csv' "$work/gdp.csv" 8388608
python -m scripts.capture_japan_macro_history gdp "$work/gdp.csv" "$receipts/G7-JP-01.json"
get 'https://www.e-stat.go.jp/en/stat-search/file-download?fileKind=0&statInfId=000031831358' "$work/lfs.xlsx" 8388608
python -m scripts.capture_japan_macro_history unemployment "$work/lfs.xlsx" "$receipts/G7-JP-11.json"
root=https://www.mof.go.jp/english/policy/jgbs/reference/interest_rate
get "$root/historical/jgbcme_all.csv" "$work/jgb.csv" 4000000
get "$root/jgbcme.csv" "$work/jgb-current.csv" 4000000
python verification/g7-core-batch1/capture-mof-jgb-history.py "$work/jgb.csv" "$receipts/G7-JP-23.json" --current "$work/jgb-current.csv"
