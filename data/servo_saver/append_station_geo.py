from supabase import create_client
import pandas as pd
import os
import requests
import zipfile
import io
import geopandas as gpd
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)


SUPABASE_URL     = os.environ.get("SUPABASE_URL", "fakekey")
SUPABASE_KEY     = os.environ.get("SUPABASE_KEY", "fakekey")


supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def select_supabase(table, columns="*", filters=None, batch_size=1000):
     all_rows = []
     start = 0

     while True:
         query = supabase.table(table).select(columns).range(start, start + batch_size - 1)

         if filters:
             for f in filters:
                 query = query.filter(*f)

         resp = query.execute()
         rows = resp.data or []

         if not rows:
             break

         all_rows.extend(rows)

         if len(rows) < batch_size:
             break

         start += batch_size

     return all_rows



def download_abs_meshblockdata():
    url = (
            "https://www.abs.gov.au/statistics/standards/australian-statistical-geography-standard-asgs-edition-3/jul2021-jun2026/access-and-downloads/digital-boundary-files/MB_2021_AUST_SHP_GDA2020.zip"
        )
    logging.info("Downloading Meshblock boundaries from ABS...")
    r = requests.get(url, timeout=120)
    r.raise_for_status()


    z = zipfile.ZipFile(io.BytesIO(r.content))
    # Find the .shp file inside the zip
    shp_file = [f for f in z.namelist() if f.endswith('.shp')][0]
    logging.info(f"Reading: {shp_file}")
    extract_dir = "meshblock_boundary"
    os.makedirs(extract_dir, exist_ok=True)
    z.extractall(extract_dir)

    meshblock = gpd.read_file(os.path.join(extract_dir, shp_file))
    return meshblock


def append_geographic_info(dfstation, meshblock):
    ## Convert stations to GeoDataFrame
    stations_gdf = gpd.GeoDataFrame(
        dfstation,
        geometry=gpd.points_from_xy(dfstation.longitude, dfstation.latitude),
        crs='EPSG:4326'
    ).to_crs(meshblock.crs)

    # Spatial join
    stations_geo = gpd.sjoin(stations_gdf, meshblock[['MB_CODE21', 'geometry','GCC_NAME21','SA4_CODE21','SA4_NAME21']],
                            how='left', predicate='within')
    return stations_geo


def update_geographic_info(stations_geo):

    records = (
        stations_geo[['id', 'MB_CODE21', 'GCC_NAME21', 'SA4_NAME21']]
        .dropna(subset=['MB_CODE21'])  # only update rows where join succeeded
        .to_dict(orient='records')
    )

    updated = 0
    errors  = 0

    for record in records:
        try:
            supabase.table("servo_stations").update({
                'mb_code21': record['MB_CODE21'],
                'gcc_name21':   record['GCC_NAME21'],
                'sa4_name21':     record['SA4_NAME21'],
            }).eq('id', record['id']).execute()
            updated += 1
        except Exception as e:
            logger.error(f"Failed to update station {record['id']}: {e}")
            errors += 1

    logger.info(f"Updated: {updated} stations, Errors: {errors}")

def append_station_geo():
    all_rows = select_supabase(
        "servo_stations",
        columns="id, latitude, longitude, mb_code21",
        filters=[("mb_code21", "is", "null")],
        batch_size=1000
    )
    dfstation = pd.DataFrame(all_rows)
    logger.info(f"Fetched {len(dfstation)} rows from supabase with mb_code21 is null")
    if len(dfstation) == 0:
        logger.info("No stations to update. Exiting.")
    else:
        meshblock = download_abs_meshblockdata()
        stations_geo = append_geographic_info(dfstation, meshblock)
        update_geographic_info(stations_geo)
        
if __name__ == "__main__":
    append_station_geo()