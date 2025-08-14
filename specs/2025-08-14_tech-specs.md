# Specifiche Tecniche — GeoGuide
Versione: 1.0.0  
Data: 2025-08-14  
Stato: Draft

## 1. Scopo
PWA React + FastAPI + LangGraph + MongoDB. Guida geolocalizzata multilingua con narrazioni e TTS.

## 2. Requisiti Funzionali (FR)
- FR1 Nearby POI (raggio 50–150 m, default 120).
- FR2 Narrazione {poi,lang,style} con ≥2 fonti, cache 24h (TTL **configurabile**).
- FR3 TTS opzionale; fallback testo.
- FR4 Contributi utente con moderazione.
- FR5 Multilingua (UI+contenuti), separatori numerici invariati.
- FR6 Event logging pseudonimo (session/request).
- FR7 Offline minimo (schede + audio recenti).

## 3. Requisiti Non Funzionali (NFR)
- SLO p95: 400 ms (hit), 1.5 s (miss); uptime 99.9%.
- Sicurezza: OWASP ASVS L2, OIDC PKCE, headers CSP/HSTS, rate-limit.
- Privacy: no PII nei log; location coarse.
- Scalabilità: API stateless, possibilità di sharding.
- Accessibilità: WCAG 2.1 AA.

## 4. API
- OpenAPI: `../openapi.yaml` (v1.0.0).  
- Endpoint chiave: /auth/*, /poi/nearby, /narration (POST/GET), /contrib/*, /config, /log, /health, /metrics.

## 5. Sicurezza
- JWT (scopes: poi:read, narration:write, contrib:write, log:write).
- CSP strict, HSTS, Referrer-Policy, Permissions-Policy.
- Secret mgmt: Vault/Secret Manager.

## 6. Telemetria
- OpenTelemetry (spans: researcher→curator→narrator).
- Log JSON strutturati; raw 24h → aggregati anonimi 13 mesi.

## 7. Caching
- `narrations_cache` su Mongo (TTL **configurabile**, default 24h).
- CDN per audio/immagini; Redis (opz.) per hot keys.

## 8. Test
- Unit ≥85%, Contract su OpenAPI, E2E “arrivo in piazza”, ZAP baseline.

## 9. Change Log
- 1.0.0 (2025-08-14) prima versione.
