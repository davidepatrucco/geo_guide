#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://127.0.0.1:8000/v1"
LAT="48.12627968879973"
LON="8.227031358650299"
RADIUS=50
LANG="it"
STYLE="guide"

echo "== Step 1: Config =="
curl -s "$BASE_URL/config" | jq .

echo "== Step 2: Nearby POI con enrichment =="
NEARBY=$(curl -s -X POST "$BASE_URL/poi/nearby?enrich=true&max_inserts=25" \
  -H 'content-type: application/json' \
  -d "{\"lat\":$LAT,\"lon\":$LON,\"radius_m\":$RADIUS,\"lang\":\"$LANG\"}")

echo "$NEARBY" | jq .

# Scegli un POI con wiki_content
POI_ID=$(echo "$NEARBY" | jq -r '.items[] | select(.wiki_content != null and .wiki_content != "") | .poi_id' | head -n 1)

if [[ -z "$POI_ID" ]]; then
  echo "❌ Nessun POI con wiki_content trovato, esco."
  exit 1
fi

echo "✅ POI selezionato per Step 3: $POI_ID"

# Mostra subito i poi_docs dal DB (via API se disponibile)
echo "== Verifica persist. poi_docs =="
curl -s "$BASE_URL/debug/poi_docs/$POI_ID" | jq .


echo "== Step 4: Narrazione =="
curl -s -X POST "$BASE_URL/narration?cache=false" \
  -H 'content-type: application/json' \
  -d "{\"poi_id\":\"$POI_ID\",\"lang\":\"$LANG\",\"style\":\"$STYLE\"}" \
  | jq .

echo "== Step 5 (opz): Documenti sorgente =="
curl -s "$BASE_URL/poi/$POI_ID/docs?lang=$LANG&limit=3" | jq .