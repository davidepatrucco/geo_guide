#!/usr/bin/env bash
# Deploy diretto su STAGING (Serverless). La CI parte comunque su push main.
set -euo pipefail
export STAGE=staging
: "${MONGO_URI:?set MONGO_URI (staging)}"
: "${OPENAI_API_KEY:?set OPENAI_API_KEY (staging)}"
npx serverless deploy --config "$(dirname "$0")/serverless.yml" --stage "$STAGE"