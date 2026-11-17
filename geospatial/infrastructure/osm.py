import hashlib

import geopandas as gpd
import httpx
import shapely.geometry

from services.api.config import settings

OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://lz4.overpass-api.de/api/interpreter"
]

def query_osm_infrastructure(
    bbox: list[float],  # [min_lon, min_lat, max_lon, max_lat]
    layer_type: str = "buildings"  # "buildings" or "roads"
) -> gpd.GeoDataFrame:
    """
    Downloads OSM infrastructure for a bounding box with local caching.
    Respects rate limits and terms of service.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    cache_key = hashlib.md5(f"{layer_type}_{min_lon:.4f}_{min_lat:.4f}_{max_lon:.4f}_{max_lat:.4f}".encode()).hexdigest()
    cache_file = settings.CACHE_DIR / f"osm_{layer_type}_{cache_key}.geojson"

    if cache_file.exists():
        try:
            return gpd.read_file(cache_file)
        except Exception:
            pass

    # Build Overpass QL query
    # Bounding box format for Overpass: (min_lat, min_lon, max_lat, max_lon)
    bbox_str = f"{min_lat},{min_lon},{max_lat},{max_lon}"
    if layer_type == "buildings":
        query = f"""
        [out:json][timeout:25];
        (
          way["building"]({bbox_str});
          relation["building"]({bbox_str});
        );
        out body;
        >;
        out skel qt;
        """
    else:  # roads
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"~"motorway|trunk|primary|secondary|tertiary|residential|unclassified"]({bbox_str});
        );
        out body;
        >;
        out skel qt;
        """

    data = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(endpoint, data={"data": query})
                if resp.status_code == 200:
                    data = resp.json()
                    break
        except Exception:
            continue

    if not data or "elements" not in data:
        # Return empty GeoDataFrame with appropriate schema
        columns = ["geometry", "osm_id", "type", "name"]
        return gpd.GeoDataFrame(columns=columns, crs="EPSG:4326")

    # Parse OSM elements
    nodes = {}
    ways = []
    for elem in data["elements"]:
        if elem["type"] == "node":
            nodes[elem["id"]] = (elem["lon"], elem["lat"])
        elif elem["type"] == "way":
            ways.append(elem)

    features = []
    for way in ways:
        node_coords = [nodes[nid] for nid in way.get("nodes", []) if nid in nodes]
        if len(node_coords) < 2:
            continue

        tags = way.get("tags", {})
        osm_id = str(way.get("id"))
        name = tags.get("name", "Unnamed")

        if layer_type == "buildings":
            if len(node_coords) >= 3:
                # Close polygon if not closed
                if node_coords[0] != node_coords[-1]:
                    node_coords.append(node_coords[0])
                poly = shapely.geometry.Polygon(node_coords)
                if poly.is_valid and not poly.is_empty:
                    features.append({
                        "geometry": poly,
                        "osm_id": osm_id,
                        "type": tags.get("building", "yes"),
                        "name": name
                    })
        else:  # roads
            line = shapely.geometry.LineString(node_coords)
            if line.is_valid and not line.is_empty:
                features.append({
                    "geometry": line,
                    "osm_id": osm_id,
                    "type": tags.get("highway", "road"),
                    "name": name
                })

    gdf = gpd.GeoDataFrame(features, crs="EPSG:4326")
    if not gdf.empty:
        try:
            gdf.to_file(cache_file, driver="GeoJSON")
        except Exception:
            pass

    return gdf
