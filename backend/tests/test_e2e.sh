#!/usr/bin/env bash
set -euo pipefail

BASE_URL="http://127.0.0.1:8000/v1"
LAT="48.85905794455411"
LON="2.29476265310796"
RADIUS=50
LANG="it"
STYLE="guide"

echo "== Step 1: Config =="
curl -s "$BASE_URL/config" | jq .

echo
echo "== Step 2: Nearby POI con enrichment =="
NEARBY=$(curl -s -X POST "$BASE_URL/nearby?max_inserts=25" \
  -H 'content-type: application/json' \
  -d "{\"lat\":$LAT,\"lon\":$LON,\"radius_m\":$RADIUS,\"lang\":\"$LANG\",\"enrich\":true}")

echo "$NEARBY" | jq .

# Prende il primo POI_ID dai documenti Wikipedia con content_text valido
POI_ID=$(echo "$NEARBY" | jq -r '
  .docs[] | select(.source == "wikipedia" and (.content_text != null and .content_text != "")) | .poi_id
' | head -n 1)

if [[ -z "$POI_ID" || "$POI_ID" == "null" ]]; then
  echo "❌ Nessun POI con documenti Wikipedia trovati, esco."
  exit 1
fi

echo "✅ POI selezionato per Step 3: $POI_ID"
echo "📄 Dettagli POI:"
echo "$NEARBY" | jq --arg POI_ID "$POI_ID" '.pois[] | select(._id == $POI_ID)'

echo
echo "== Step 3: Narrazione (no cache) =="

# Mostra il POI completo
echo "📄 Dettagli POI selezionato:"
curl -s "$BASE_URL/poi/$POI_ID" | jq .

# Genera la narrazione
curl -s -X POST "$BASE_URL/narration?cache=false" \
  -H 'content-type: application/json' \
  -d "{\"poi_id\":\"$POI_ID\",\"lang\":\"$LANG\",\"style\":\"$STYLE\"}" \
  | jq .

echo
echo "== Step 4: Documenti sorgente (max 3) =="
curl -s "$BASE_URL/poi/$POI_ID/docs?lang=$LANG&limit=3" | jq .