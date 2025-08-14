# Data Model — MongoDB
Versione: 1.0.0  
Data: 2025-08-14  
Stato: Draft

> Nota: `narrations_cache` è persistente con TTL **configurabile** (default 24h).

## Collections
1. `pois` — master POI
2. `poi_docs` — fonti normalizzate
3. `narrations_cache` — cache narrazioni
4. `user_contrib` — contributi + moderazione
5. `usage_logs` — eventi UX/telem.
6. `users` — profili OIDC
7. `app_config` — config e feature-flag

## Schemi (estratto)
### pois
- Campi: name{locale}, aliases[], location(Point [lon,lat]), geocell, osm{id,tags}, wikidata_qid, wikipedia{locale}, langs[], photos[], last_refresh_at, created_at, updated_at.
- Indici: 2dsphere(location), text(name.it,aliases), {wikidata_qid:1}(sparse), {geocell:1}.

### poi_docs
- Campi: poi_id(ObjectId), source(enum), url, lang, content_text, sections[], meta{}, embedding[], created_at.
- Indici: {poi_id:1,lang:1,source:1}, {url:1}(sparse).

### narrations_cache
- Campi: poi_id, style(enum), lang, text, audio_url?, sources[name,url][], confidence[0..1], created_at.
- Indici: {poi_id:1,lang:1,style:1}(unique), TTL {created_at:1} (config.).

### user_contrib
- Campi: poi_id, user_id(UUID bin4), lang, text(1..4000), status(enum), moderation{auto_flags[], reviewer_id, reviewed_at, notes}, created_at, updated_at.
- Indici: {poi_id:1,status:1,created_at:-1}, {user_id:1,created_at:-1}.

### usage_logs
- Eventi: app.open, auth.login, poi.nearby, poi.view, narration.request, narration.generated, audio.play, contrib.posted, contrib.moderated, error.
- Campi: event, ts, user_hash, session_id(UUID), request_id(UUID), poi_id?, latlon_q50m, app_ver, platform, network, outcome, error_code?, latency_ms?, size_bytes?, extra{}.
- Indici: TTL 24h su ts (config.), {event:1,ts:-1}, {user_hash:1,ts:-1}, {session_id:1}, {request_id:1}(sparse), {poi_id:1,ts:-1}.

### users
- Campi: sub(unique), display_name, locale, roles[], created_at, updated_at.

### app_config
- Campi: _id('v1'), version, flags{...}, limits{...}, llm{...}, updated_at.

## Script creazione
// create_collections_v3.js - Create-only (no collMod), safe for limited Atlas roles
// Run: mongosh --file create_collections_v3.js

const DB_NAME = "geo_guide";
const NARRATIONS_TTL_SECONDS = 60 * 60 * 24;   // TTL configurabile
const USAGELOGS_TTL_SECONDS  = 60 * 60 * 24;   // TTL configurabile

(function () {
  const dbh = db.getSiblingDB(DB_NAME);
  const existing = new Set(dbh.getCollectionNames());

  function createIfMissing(name, validator) {
    if (!existing.has(name)) {
      dbh.createCollection(name, validator ? { validator } : {});
      print(`+ created: ${name}`);
      return true;
    } else {
      print(`= exists: ${name} (validator NOT updated; needs collMod privilege)`);
      return false;
    }
  }

  // pois
  createIfMissing("pois", {
    $jsonSchema: {
      bsonType: "object",
      required: ["name", "location", "langs", "last_refresh_at"],
      properties: {
        name: { bsonType: "object", additionalProperties: { bsonType: "string", minLength: 1 } },
        aliases: { bsonType: "array", items: { bsonType: "string" } },
        location: {
          bsonType: "object",
          required: ["type", "coordinates"],
          properties: {
            type: { enum: ["Point"] },
            coordinates: {
              bsonType: "array",
              items: [{ bsonType: "double" }, { bsonType: "double" }],
              minItems: 2, maxItems: 2
            }
          }
        },
        geocell: { bsonType: "string" },
        osm: { bsonType: "object", properties: { id: { bsonType: "string" }, tags: { bsonType: "object" } } },
        wikidata_qid: { bsonType: "string", pattern: "^Q[0-9]+$" },
        wikipedia: { bsonType: "object", additionalProperties: { bsonType: "string" } },
        langs: { bsonType: "array", items: { bsonType: "string", pattern: "^[a-z]{2}(-[A-Z]{2})?$" }, minItems: 1 },
        photos: { bsonType: "array", items: { bsonType: "string" } },
        last_refresh_at: { bsonType: "date" },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  });
  dbh.pois.createIndex({ location: "2dsphere" });
  dbh.pois.createIndex({ "name.it": "text", aliases: "text" });
  dbh.pois.createIndex({ wikidata_qid: 1 }, { sparse: true });
  dbh.pois.createIndex({ geocell: 1 });

  // poi_docs
  createIfMissing("poi_docs", {
    $jsonSchema: {
      bsonType: "object",
      required: ["poi_id", "source", "lang", "content_text", "created_at"],
      properties: {
        poi_id: { bsonType: "objectId" },
        source: { enum: ["wikipedia", "osm", "places", "user"] },
        url: { bsonType: "string" },
        lang: { bsonType: "string", pattern: "^[a-z]{2}(-[A-Z]{2})?$" },
        content_text: { bsonType: "string", minLength: 1 },
        sections: { bsonType: "array", items: { bsonType: "string" } },
        meta: { bsonType: "object" },
        embedding: { bsonType: "array", items: { bsonType: "double" } },
        created_at: { bsonType: "date" }
      }
    }
  });
  dbh.poi_docs.createIndex({ poi_id: 1, lang: 1, source: 1 });
  dbh.poi_docs.createIndex({ url: 1 }, { sparse: true });

  // narrations_cache
  createIfMissing("narrations_cache", {
    $jsonSchema: {
      bsonType: "object",
      required: ["poi_id", "style", "lang", "text", "sources", "confidence", "created_at"],
      properties: {
        poi_id: { bsonType: "objectId" },
        style: { enum: ["guide", "quick", "kids", "anecdotes"] },
        lang: { bsonType: "string", pattern: "^[a-z]{2}(-[A-Z]{2})?$" },
        text: { bsonType: "string", minLength: 1 },
        audio_url: { bsonType: "string" },
        sources: {
          bsonType: "array",
          minItems: 1,
          items: {
            bsonType: "object",
            required: ["name", "url"],
            properties: { name: { bsonType: "string" }, url: { bsonType: "string" } }
          }
        },
        confidence: { bsonType: "double", minimum: 0, maximum: 1 },
        created_at: { bsonType: "date" }
      }
    }
  });
  dbh.narrations_cache.createIndex({ poi_id: 1, lang: 1, style: 1 }, { unique: true });
  dbh.narrations_cache.createIndex({ created_at: 1 }, { expireAfterSeconds: NARRATIONS_TTL_SECONDS });

  // user_contrib
  createIfMissing("user_contrib", {
    $jsonSchema: {
      bsonType: "object",
      required: ["poi_id", "text", "lang", "status", "created_at"],
      properties: {
        poi_id: { bsonType: "objectId" },
        user_id: { bsonType: "binData" },
        lang: { bsonType: "string", pattern: "^[a-z]{2}(-[A-Z]{2})?$" },
        text: { bsonType: "string", minLength: 1, maxLength: 4000 },
        status: { enum: ["pending", "approved", "rejected"] },
        moderation: {
          bsonType: "object",
          properties: {
            auto_flags: { bsonType: "array", items: { bsonType: "string" } },
            reviewer_id: { bsonType: "binData" },
            reviewed_at: { bsonType: "date" },
            notes: { bsonType: "string" }
          }
        },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  });
  dbh.user_contrib.createIndex({ poi_id: 1, status: 1, created_at: -1 });
  dbh.user_contrib.createIndex({ user_id: 1, created_at: -1 });

  // usage_logs
  createIfMissing("usage_logs", {
    $jsonSchema: {
      bsonType: "object",
      required: ["event", "ts"],
      properties: {
        event: {
          enum: [
            "app.open","auth.login","poi.nearby","poi.view",
            "narration.request","narration.generated","audio.play",
            "contrib.posted","contrib.moderated","error"
          ]
        },
        ts: { bsonType: "date" },
        user_hash: { bsonType: "string" },
        session_id: { bsonType: "binData" },
        request_id: { bsonType: "binData" },
        poi_id: { bsonType: ["objectId","null"] },
        latlon_q50m: { bsonType: "string" },
        app_ver: { bsonType: "string" },
        platform: { enum: ["ios","android","web"] },
        network: { enum: ["wifi","cellular","offline","unknown"] },
        outcome: { enum: ["ok","fail","cancel","timeout"] },
        error_code: { bsonType: "string" },
        latency_ms: { bsonType: "int" },
        size_bytes: { bsonType: "int" },
        extra: { bsonType: "object" }
      }
    }
  });
  dbh.usage_logs.createIndex({ ts: 1 }, { expireAfterSeconds: USAGELOGS_TTL_SECONDS });
  dbh.usage_logs.createIndex({ event: 1, ts: -1 });
  dbh.usage_logs.createIndex({ user_hash: 1, ts: -1 });
  dbh.usage_logs.createIndex({ session_id: 1 });
  dbh.usage_logs.createIndex({ request_id: 1 }, { sparse: true });
  dbh.usage_logs.createIndex({ poi_id: 1, ts: -1 });

  // users
  createIfMissing("users", {
    $jsonSchema: {
      bsonType: "object",
      required: ["sub", "created_at"],
      properties: {
        sub: { bsonType: "string" },
        display_name: { bsonType: "string" },
        locale: { bsonType: "string", pattern: "^[a-z]{2}(-[A-Z]{2})?$" },
        roles: { bsonType: "array", items: { enum: ["user","moderator","admin"] } },
        created_at: { bsonType: "date" },
        updated_at: { bsonType: "date" }
      }
    }
  });
  dbh.users.createIndex({ sub: 1 }, { unique: true });

  // app_config
  createIfMissing("app_config", {
    $jsonSchema: {
      bsonType: "object",
      required: ["_id", "version", "flags", "limits", "updated_at"],
      properties: {
        _id: { bsonType: "string" },
        version: { bsonType: "int" },
        flags: { bsonType: "object" },
        limits: { bsonType: "object" },
        llm: { bsonType: "object" },
        updated_at: { bsonType: "date" }
      }
    }
  });

  print("[setup] Done. NOTE: If a collection existed, its validator was not changed due to missing collMod privilege.");
})();
