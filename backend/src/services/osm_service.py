# services/osm_service.py
import logging
import aiohttp
import ssl
import certifi

OSM_OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Forza certificati certifi
ssl_context = ssl.create_default_context(cafile=certifi.where())

async def fetch_osm_pois(lat: float, lon: float, radius_m: int):
    logging.info(f"[OSM] Fetching POIs for lat={lat}, lon={lon}, radius={radius_m}m")
    query = f"""
    [out:json];
    (
      node
        (around:{radius_m},{lat},{lon})
        ["name"];
    );
    out body;
    """
    logging.debug(f"[OSM] Overpass query:\n{query.strip()}")

    async with aiohttp.ClientSession() as session:
        async with session.post(OSM_OVERPASS_URL, data={"data": query}, ssl=ssl_context) as resp:
            if resp.status != 200:
                logging.error(f"[OSM] Failed with status {resp.status}")
                return []
            data = await resp.json()

    pois = []
    for el in data.get("elements", []):
        name = el.get("tags", {}).get("name")
        if not name:
            logging.debug(f"[OSM] Skipping element {el.get('id')} (no name)")
            continue
        lat_poi, lon_poi = el["lat"], el["lon"]
        lang_guess = None
        pois.append({
            "provider": "osm",
            "provider_id": str(el.get("id")),  # ID OSM
            "name": name,
            "lat": lat_poi,
            "lon": lon_poi,
            "lang": lang_guess
        })
        logging.debug(f"[OSM] Found POI: '{name}' ({lat_poi},{lon_poi}) → provider_id={el.get('id')}")

    logging.info(f"[OSM] Total POIs fetched: {len(pois)}")
    return pois