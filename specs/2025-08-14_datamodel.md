# Data Model — MongoDB
Versione: 1.1.0  
Data: 2025-08-14  
Stato: Draft

> Nota: `narrations_cache` è persistente con TTL **configurabile** (default 24h).

## Collections
1. `searched_pois` — cache ricerche per coordinate
2. `pois` — master POI
3. `poi_docs` — fonti normalizzate
4. `narrations_cache` — cache narrazioni
5. `user_contrib` — contributi + moderazione
6. `usage_logs` — eventi UX/telem.
7. `users` — profili OIDC
8. `app_config` — config e feature-flag

---

## Schemi (estratto)

### searched_pois
- **Scopo**: evitare ricerche ripetute per stesse coordinate in un periodo breve.
- Campi:
  - `lat_round` (double)
  - `lon_round` (double)
  - `last_search_at` (date)
- Indici:
  - `{lat_round:1, lon_round:1}` (unique)
  - `{last_search_at:1}`

---

### pois
- **Scopo**: POI univoco per (lat_round, lon_round, name).
- Campi:
  - `poi_id` (string, univoco)
  - `lat_round` (double)
  - `lon_round` (double)
  - `name`{locale}
  - `aliases`[]
  - `location`(Point [lon,lat])
  - `geocell`
  - `osm`{id,tags}
  - `wikidata_qid`
  - `wikipedia`{locale}
  - `langs`[]
  - `photos`[]
  - `last_seen_at` (date)
  - `is_active` (bool)
  - `created_at`, `updated_at`
- Indici:
  - `{lat_round:1, lon_round:1, name:1}` (unique)
  - `2dsphere(location)`
  - `{wikidata_qid:1}`(sparse)
  - `{geocell:1}`

---

### poi_docs
- Campi: `poi_id`(ObjectId), `source`(enum), `url`, `lang`, `content_text`, `sections`[], `meta`{}, `embedding`[], `created_at`.
- Indici: `{poi_id:1,lang:1,source:1}`, `{url:1}`(sparse).

---

### narrations_cache
- Campi: `poi_id`, `style`(enum), `lang`, `text`, `audio_url?`, `sources`[name,url][], `confidence`[0..1], `created_at`.
- Indici: `{poi_id:1,lang:1,style:1}`(unique), TTL `{created_at:1}` (config.).

---

### user_contrib
- Campi: `poi_id`, `user_id`(UUID bin4), `lang`, `text`(1..4000), `status`(enum), `moderation`{auto_flags[], reviewer_id, reviewed_at, notes}, `created_at`, `updated_at`.
- Indici: `{poi_id:1,status:1,created_at:-1}`, `{user_id:1,created_at:-1}`.

---

### usage_logs
- Eventi: `app.open`, `auth.login`, `poi.nearby`, `poi.view`, `narration.request`, `narration.generated`, `audio.play`, `contrib.posted`, `contrib.moderated`, `error`.
- Campi: `event`, `ts`, `user_hash`, `session_id`(UUID), `request_id`(UUID), `poi_id?`, `latlon_q50m`, `app_ver`, `platform`, `network`, `outcome`, `error_code?`, `latency_ms?`, `size_bytes?`, `extra`{}.
- Indici: TTL 24h su ts (config.), `{event:1,ts:-1}`, `{user_hash:1,ts:-1}`, `{session_id:1}`, `{request_id:1}`(sparse), `{poi_id:1,ts:-1}`.

---

### users
- Campi: `sub`(unique), `display_name`, `locale`, `roles`[], `created_at`, `updated_at`.

---

### app_config
- Campi: `_id`('v1'), `version`, `flags`{...}, `limits`{...}, `llm`{...}, `updated_at`.