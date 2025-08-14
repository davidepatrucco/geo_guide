# Architettura & Moduli
Versione: 1.0.0  
Data: 2025-08-14  
Stato: Draft

## Panoramica
Client (PWA React) ↔ API (FastAPI) ↔ Agents (LangGraph) ↔ MongoDB Atlas (+ CDN/Redis opz.).

## Moduli Backend
- api/routers: auth, poi, narration, contrib, config, health, log
- core/domain: POI, SourceDoc, NarrationStyle, Locale, UserProfile
- core/ports: POIRepository, DocStore, SearchClient, TTSClient, Cache
- adapters/data: mongo repos, redis cache
- adapters/integrations: wikipedia, overpass, places, tts
- agents: researcher, curator, narrator, graph
- infra: settings (env + app_config), middleware (headers, rate-limit), otel, logging

## Flusso LangGraph
researcher → curator → narrator (retry & policy).  
Cache: lookup `narrations_cache` prima di esecuzione; invalidazione su update `poi_docs`.

## API
OpenAPI `../openapi.yaml`.

## Deployment
Docker images firmate; Helm/Argo; Atlas backups; RPO ≤15m / RTO ≤1h.

## Sicurezza
OIDC PKCE; JWT scopes; CSP/HSTS; Secrets in Vault/SM.

## Osservabilità
OpenTelemetry, Prometheus, log JSON (no PII).

## Struttura Repo (riassunto)
```
geo-guide/
├─ specs/ (questi file)
├─ scripts/ (mongo scripts)
├─ backend/ (FastAPI + LangGraph)
└─ frontend/ (PWA React)
```
