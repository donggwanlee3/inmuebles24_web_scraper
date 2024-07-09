import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import boto3
from io import BytesIO
from io import StringIO
import os
import datetime
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'csv_data'))
unit_properties_path = os.path.join(base_dir, 'unit_properties.csv')
building_properties_path = os.path.join(base_dir, 'building_properties.csv')


def upload_csv_as_parquet_to_s3(csv_file, bucket_name, s3_key):
    # Read the CSV file into a Pandas DataFrame
    df = pd.read_csv(csv_file)
    
    # Convert DataFrame to Parquet format in memory
    parquet_buffer = BytesIO()
    df.to_parquet(parquet_buffer, index=False)
    parquet_buffer.seek(0)
    
    # Upload Parquet file to S3
    s3 = boto3.client('s3')
    s3.put_object(Bucket=bucket_name, Key=s3_key, Body=parquet_buffer.getvalue())
    
    print(f"Uploaded {csv_file} as Parquet to s3://{bucket_name}/{s3_key}")



def upload_geoparquet_to_s3(csv_file, bucket_name, s3_geo_key):
    # Read the CSV file into a Pandas DataFrame
    df = pd.read_csv(csv_file)

    # Check for the presence of 'latitude' and 'longitude' columns
    if 'latitude' in df.columns and 'longitude' in df.columns:
        # Separate rows with non-null latitude and longitude
        geo_df = df.dropna(subset=['latitude', 'longitude'])

        if not geo_df.empty:
            # Convert the DataFrame to a GeoDataFrame
            geometry = [Point(xy) for xy in zip(geo_df['longitude'], geo_df['latitude'])]
            gdf = gpd.GeoDataFrame(geo_df, geometry=geometry)

            # Set the coordinate reference system (CRS) if known, e.g., EPSG:4326
            gdf.set_crs(epsg=4326, inplace=True)

            # Convert GeoDataFrame to GeoParquet in memory
            geo_parquet_buffer = BytesIO()
            gdf.to_parquet(geo_parquet_buffer, index=False)
            geo_parquet_buffer.seek(0)

            # Upload GeoParquet to S3
            s3 = boto3.client('s3')
            s3.put_object(Bucket=bucket_name, Key=s3_geo_key, Body=geo_parquet_buffer.getvalue())
            print(f"Uploaded geospatial data from {csv_file} as GeoParquet to s3://{bucket_name}/{s3_geo_key}")
    else:
        print("The CSV file does not contain 'latitude' and 'longitude' columns.")

def upload_aws():
    bucket_name = 'blackprint-market-data'
    now = datetime.datetime.now()
    formatted_date = now.strftime("%Y_%m_%d_%H_%M_%S")
    # Upload unit_properties.csv as Parquet
    upload_csv_as_parquet_to_s3(unit_properties_path, bucket_name, f'{formatted_date}/units.parquet')
    # Convert and upload building_properties.csv as GeoParquet
    upload_geoparquet_to_s3(building_properties_path, bucket_name, f'{formatted_date}/buildings.parquet')

upload_aws()