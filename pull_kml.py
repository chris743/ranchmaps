import requests
import geopandas as gpd
import simplekml
from shapely.geometry import shape

# === CONFIGURATION ===
ARCGIS_API_KEY = "AAPTxy8BH1VEsoebNVZXo8HurH7_IUO_uR8ph4fbuquDhM-AuucCdY_vHbl28EKHT4eOGdE5dwDQdlrtefjCzaTI1BdEMNWlgpC4ya_q01gVuGh9Tt6Nt-4X8vXACmLJFovSsizgR1tFTvGdX3-EdyzuV29nBDnV_M_Qtw7tQpsOAeh1J_8MjYVHjw9TkDjafzd0IVHDeBgBgTYll9-XrI4EDN9IDV64Y73eK-H-sFIlGOg.AT1_dzP8qzYv"
FEATURE_LAYER_URL = "https://services2.arcgis.com/nlv1mN93wziUruyM/arcgis/rest/services/All_Cobblestone_Blocks/FeatureServer/0/query"
KML_OUTPUT_PATH = "blocks.xml"

# === QUERY THE ARCGIS ONLINE LAYER ===
params = {
    "where": "1=1",
    "outFields": "*",
    "f": "geojson",
    "returnGeometry": "true",
    "outSR": "4326",
    "token": ARCGIS_API_KEY
}

print("Making request to:", FEATURE_LAYER_URL)
print("Parameters:", params)

try:
    response = requests.get(FEATURE_LAYER_URL, params=params)
    print(f"Response status: {response.status_code}")
    print(f"Response headers: {dict(response.headers)}")
    print(f"Response content (first 500 chars): {response.text[:500]}")
    
    # Check if response is successful
    if response.status_code != 200:
        print(f"Error: HTTP {response.status_code}")
        print(f"Full response: {response.text}")
        exit(1)
    
    # Try to parse JSON
    try:
        data = response.json()
    except requests.exceptions.JSONDecodeError as e:
        print(f"JSON decode error: {e}")
        print(f"Response content type: {response.headers.get('content-type', 'unknown')}")
        print(f"Full response text: {response.text}")
        exit(1)
    
    # Check if we got features
    if "features" not in data:
        print("No 'features' key in response")
        print(f"Response keys: {list(data.keys()) if isinstance(data, dict) else 'Not a dict'}")
        print(f"Full response: {data}")
        exit(1)
    
    if not data["features"]:
        print("No features found in the response")
        exit(1)
    
    print(f"Found {len(data['features'])} features")
    
except requests.RequestException as e:
    print(f"Request error: {e}")
    exit(1)

# === CONVERT TO GeoDataFrame ===
try:
    gdf = gpd.GeoDataFrame.from_features(data["features"])
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    print(f"Created GeoDataFrame with {len(gdf)} rows")
    print(f"Columns: {list(gdf.columns)}")
    
except Exception as e:
    print(f"Error creating GeoDataFrame: {e}")
    exit(1)

# === CREATE KML ===
try:
    kml = simplekml.Kml()
    polygon_count = 0
    
    for idx, row in gdf.iterrows():
        geom = row.geometry
        if geom is None:
            continue
            
        if geom.geom_type == "Polygon":
            coords = list(geom.exterior.coords)
            p = kml.newpolygon(
                name=row.get("block_name", f"Block_{idx}"),
                description=(
                    f"Block ID: {row.get('blockID', 'Unknown')}<br>"
                    f"Block Name: {row.get('block_name', 'Unknown')}<br>"
                    f"Commodity: {row.get('commodity', 'Unknown')}<br>"
                    f"Variety: {row.get('variety', 'Unknown')}<br>"
                    f"Acres: {row.get('Acres', 'Unknown')}<br>"
                    f"Parent Ranch: {row.get('ranches', 'Unknown')} acres"
                    f"Row Spacing: {row.get('row_spacing', 'Unknown')}<br>"
                    f"Tree Spacing: {row.get('tree_spacing', 'Unknown')}<br>"
                    f"Tree Count: {row.get('tree_count', 'Unknown')}<br>"
                ),
                outerboundaryis=coords
            )
            p.style.polystyle.color = "7d00ff00"  # semi-transparent green
            p.style.linestyle.width = 2
            polygon_count += 1
            
        elif geom.geom_type == "MultiPolygon":
            for i, poly in enumerate(geom.geoms):
                coords = list(poly.exterior.coords)
                p = kml.newpolygon(
                    name=f"{row.get('block_name', f'Block_{idx}')}_{i}",
                    description=f"Ranch: {row.get('ranch_name', 'Unknown')}<br>Crop: {row.get('crop_type', 'Unknown')}",
                    outerboundaryis=coords
                )
                p.style.polystyle.color = "7d00ff00"
                p.style.linestyle.width = 2
                polygon_count += 1
    
    if polygon_count == 0:
        print("Warning: No polygons were added to KML")
    else:
        print(f"Added {polygon_count} polygons to KML")
    
    kml.save(KML_OUTPUT_PATH)
    print(f"KML saved to {KML_OUTPUT_PATH}")
    
except Exception as e:
    print(f"Error creating KML: {e}")
    exit(1)