import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import boto3
from io import BytesIO
from io import StringIO
import os
import datetime
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'csv_data'))
unit_properties_path = os.path.join(base_dir, 'Unit_Properties.csv')
building_properties_path = os.path.join(base_dir, 'Building_Properties.csv')


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



def upload_geoparquet_to_s3(csv_file, bucket_name, s3_geo_key, s3_non_geo_key):
    # Read the CSV file into a Pandas DataFrame
    s3 = boto3.client('s3')
    df = pd.read_csv(csv_file)

    # Check for the presence of 'Latitude' and 'Longitude' columns
    has_geo_data = 'Latitude' in df.columns and 'Longitude' in df.columns

    if has_geo_data:
        # Separate rows with non-null latitude and longitude
        geo_df = df.dropna(subset=['Latitude', 'Longitude'])
        non_geo_df = df[df[['Latitude', 'Longitude']].isnull().any(axis=1)]

        # Handle non-geospatial data (rows with null lat/lon)
        if not non_geo_df.empty:
            non_geo_parquet_buffer = BytesIO()
            non_geo_df.to_parquet(non_geo_parquet_buffer, index=False)
            non_geo_parquet_buffer.seek(0)

            # Upload non-geospatial Parquet to S3
            s3 = boto3.client('s3')
            s3.put_object(Bucket=bucket_name, Key=s3_non_geo_key, Body=non_geo_parquet_buffer.getvalue())
            print(f"Uploaded non-geospatial data from {csv_file} as Parquet to s3://{bucket_name}/{s3_non_geo_key}")

        # Handle geospatial data (rows with valid lat/lon)
        if not geo_df.empty:
            # Convert the DataFrame to a GeoDataFrame
            geometry = [Point(xy) for xy in zip(geo_df['Longitude'], geo_df['Latitude'])]
            gdf = gpd.GeoDataFrame(geo_df, geometry=geometry)

            # Set the coordinate reference system (CRS) if known, e.g., EPSG:4326
            gdf.set_crs(epsg=4326, inplace=True)

            # Convert GeoDataFrame to GeoParquet in memory
            geo_parquet_buffer = BytesIO()
            gdf.to_parquet(geo_parquet_buffer, index=False)
            geo_parquet_buffer.seek(0)

            # Upload GeoParquet to S3
            s3.put_object(Bucket=bucket_name, Key=s3_geo_key, Body=geo_parquet_buffer.getvalue())
            print(f"Uploaded geospatial data from {csv_file} as GeoParquet to s3://{bucket_name}/{s3_geo_key}")

async def upload_aws():
    bucket_name = 'blackprint-market-data'
    now = datetime.datetime.now()
    formatted_date = now.strftime("%Y-%m-%d %H:%M:%S")
    # Upload unit_properties.csv as Parquet
    upload_geoparquet_to_s3(unit_properties_path, bucket_name, f'{formatted_date}/Units/Unit_Properties.parquet',f'{formatted_date}/Units/no_coord_Unit_Properties.parquet')
    # Convert and upload building_properties.csv as GeoParquet
    upload_geoparquet_to_s3(building_properties_path, bucket_name, f'{formatted_date}/Buildings/Building_Properties.parquet', f'{formatted_date}/Buildings/no_coord_Building_Properties.parquet')