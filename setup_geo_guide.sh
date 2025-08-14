#!/bin/bash
# setup_geo_guide.sh
# Crea struttura progetto + specs + deploy (serverless/container)

set -euo pipefail

BASE_DIR="geo-guide"
SPEC_DATE="$(date +%F)"   # es. 2025-08-14
SPEC_DIR="$BASE_DIR/specs"

# Cartelle principali
mkdir -p "$SPEC_DIR" "$BASE_DIR/scripts" \
  "$BASE_DIR/backend/src/{config,routes,controllers,models,services,utils,infra}" \
  "$BASE_DIR/backend/tests/integration" \
  "$BASE_DIR/frontend/public" "$BASE_DIR/frontend/src/{components,pages,styles}" \
  "$BASE_DIR/deploy" ".github/workflows"

# File placeholder root
: > "$BASE_DIR/README.md"
: > "$BASE_DIR/.env"
: > "$BASE_DIR/package.json"
: > "$BASE_DIR/requirements.txt"
: > "$BASE_DIR/docker-compose.yml"
: > "$BASE_DIR/openapi.yaml"

# Specs boilerplate
cat > "$SPEC_DIR/${SPEC_DATE}_tech-specs.md" <<'MD'
# Specifiche Tecniche — GeoGuide
(Versionate; aggiornare a ogni modifica rilevante)
MD
cat > "$SPEC_DIR/${SPEC_DATE}_datamodel.md" <<'MD'
# Data Model — MongoDB
Vedi anche scripts/create_collections_v3.js (Atlas-safe).
MD
cat > "$SPEC_DIR/${SPEC_DATE}_architecture.md" <<'MD'
# Architettura & Moduli
PWA React + FastAPI + LangGraph + MongoDB Atlas.
MD

# Copia OpenAPI in specs (o placeholder se vuoto)
if [[ -s "$BASE_DIR/openapi.yaml" ]]; then
  cp "$BASE_DIR/openapi.yaml" "$SPEC_DIR/${SPEC_DATE}_openapi_v1.0.0.yaml"
else
  cat > "$SPEC_DIR/${SPEC_DATE}_openapi_v1.0.0.yaml" <<'YAML'
openapi: 3.1.0
info: { title: GeoGuide API, version: "1.0.0" }
paths: {}
components: {}
YAML
fi

# Backend placeholders
: > "$BASE_DIR/backend/src/app.py"
: > "$BASE_DIR/backend/src/config/index.py"
: > "$BASE_DIR/backend/src/config/logger.py"
: > "$BASE_DIR/backend/src/routes/__init__.py"
: > "$BASE_DIR/backend/src/routes/auth.py"
: > "$BASE_DIR/backend/src/routes/pois.py"
: > "$BASE_DIR/backend/src/routes/narrations.py"
: > "$BASE_DIR/backend/src/routes/contrib.py"
: > "$BASE_DIR/backend/src/routes/usage.py"
: > "$BASE_DIR/backend/src/controllers/__init__.py"
: > "$BASE_DIR/backend/src/controllers/auth_controller.py"
: > "$BASE_DIR/backend/src/controllers/poi_controller.py"
: > "$BASE_DIR/backend/src/controllers/narration_controller.py"
: > "$BASE_DIR/backend/src/controllers/contrib_controller.py"
: > "$BASE_DIR/backend/src/controllers/usage_controller.py"
: > "$BASE_DIR/backend/src/models/__init__.py"
: > "$BASE_DIR/backend/src/models/poi.py"
: > "$BASE_DIR/backend/src/models/poi_doc.py"
: > "$BASE_DIR/backend/src/models/narration_cache.py"
: > "$BASE_DIR/backend/src/models/user_contrib.py"
: > "$BASE_DIR/backend/src/models/usage_log.py"
: > "$BASE_DIR/backend/src/models/user.py"
: > "$BASE_DIR/backend/src/models/app_config.py"
: > "$BASE_DIR/backend/src/services/__init__.py"
: > "$BASE_DIR/backend/src/services/llm_agent_service.py"
: > "$BASE_DIR/backend/src/services/geocoding_service.py"
: > "$BASE_DIR/backend/src/services/wiki_service.py"
: > "$BASE_DIR/backend/src/services/tts_service.py"
: > "$BASE_DIR/backend/src/infra/__init__.py"
: > "$BASE_DIR/backend/src/infra/db.py"
: > "$BASE_DIR/backend/src/utils/__init__.py"
: > "$BASE_DIR/backend/src/utils/error_handler.py"
: > "$BASE_DIR/backend/src/utils/validators.py"
: > "$BASE_DIR/backend/tests/integration/pois_test.py"
: > "$BASE_DIR/backend/tests/integration/narrations_test.py"

# Frontend placeholders
: > "$BASE_DIR/frontend/src/App.jsx"
: > "$BASE_DIR/frontend/src/components/MapView.jsx"
: > "$BASE_DIR/frontend/src/components/PoiDetails.jsx"
: > "$BASE_DIR/frontend/src/components/NarrationPlayer.jsx"
: > "$BASE_DIR/frontend/src/components/LoginForm.jsx"
: > "$BASE_DIR/frontend/src/pages/Home.jsx"
: > "$BASE_DIR/frontend/src/pages/Nearby.jsx"
: > "$BASE_DIR/frontend/src/pages/Contribute.jsx"
: > "$BASE_DIR/frontend/src/styles/main.css"

# Scripts Mongo
: > "$BASE_DIR/scripts/create_collections_v3.js"
: > "$BASE_DIR/scripts/seed.js"

# Deploy: README
cat > "$BASE_DIR/deploy/README.md" <<'MD'
# Deploy
Scegli una delle opzioni:
- AWS Lambda + API Gateway (Serverless Framework): `serverless.yml`
- Google Cloud Run (container serverless): `Dockerfile.backend`
MD

# Deploy: Serverless (AWS Lambda + API Gateway, FastAPI via Mangum)
cat > "$BASE_DIR/deploy/serverless.yml" <<'YML'
service: geoguide-api
frameworkVersion: "3"
provider:
  name: aws
  runtime: python3.11
  region: eu-central-1
  architecture: arm64
  memorySize: 1024
  timeout: 15
  environment:
    MONGO_URI: ${env:MONGO_URI}
    OPENAI_API_KEY: ${env:OPENAI_API_KEY}
functions:
  api:
    handler: backend/src/app.handler
    events:
      - httpApi: '*'
package:
  patterns:
    - backend/**/*
    - '!**/__pycache__/**'
plugins:
  - serverless-python-requirements
custom:
  pythonRequirements:
    slim: true
    layer: true
YML

# Deploy: Dockerfile per Cloud Run (container serverless)
cat > "$BASE_DIR/deploy/Dockerfile.backend" <<'DOCKER'
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir uvicorn[standard]
COPY backend /app/backend
ENV PORT=8080
CMD ["uvicorn","backend.src.app:app","--host","0.0.0.0","--port","8080"]
DOCKER

# GH Actions placeholders
cat > ".github/workflows/ci.yml" <<'YML'
name: CI
on: [push, pull_request]
jobs:
  backend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: backend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: '3.11' }
      - run: pip install -r requirements.txt || true
      - run: python -m pytest -q || true
  frontend:
    runs-on: ubuntu-latest
    defaults: { run: { working-directory: frontend } }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20' }
      - run: npm ci || true
      - run: npm run build || true
YML

echo "Struttura creata in '$BASE_DIR' con 'deploy/' e specs versionate ($SPEC_DATE)."