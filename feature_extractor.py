"""
Feature extraction module for satellite imagery and location-based features.
Extracts NDVI (greenery), NDWI (water), and road density features.
"""
import numpy as np
from sentinelhub import (
    SentinelHubRequest,
    DataCollection,
    MimeType,
    CRS,
    BBox,
    bbox_to_dimensions
)
from .sentinel_config import get_sh_config
import requests
import time


def fetch_satellite_bands(lat, lon, size_pixels=256):
    """
    Fetch Sentinel-2 bands needed for NDVI and NDWI calculations.
    Returns: numpy array with bands [B02, B03, B04, B08, B11] (RGB, NIR, SWIR)
    """
    bbox = BBox(
        bbox=[lon - 0.002, lat - 0.002, lon + 0.002, lat + 0.002],
        crs=CRS.WGS84
    )

    resolution = 10  # meters per pixel
    width, height = bbox_to_dimensions(bbox, resolution=resolution)
    # Ensure reasonable size
    width = min(width, size_pixels)
    height = min(height, size_pixels)

    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: ["B02", "B03", "B04", "B08", "B11"],
            output: { bands: 5 }
        };
    }

    function evaluatePixel(sample) {
        return [sample.B02, sample.B03, sample.B04, sample.B08, sample.B11];
    }
    """

    request = SentinelHubRequest(
        evalscript=evalscript,
        input_data=[
            SentinelHubRequest.input_data(
                data_collection=DataCollection.SENTINEL2_L2A,
                time_interval=("2023-01-01", "2023-12-31"),
                mosaicking_order="mostRecent"
            )
        ],
        responses=[
            SentinelHubRequest.output_response("default", MimeType.TIFF)
        ],
        bbox=bbox,
        size=(width, height),
        config=get_sh_config()
    )

    bands = request.get_data()[0]
    return bands


def calculate_ndvi(bands):
    """
    Calculate NDVI (Normalized Difference Vegetation Index) from satellite bands.
    NDVI = (NIR - Red) / (NIR + Red)
    bands: array with shape (height, width, 5) where [B02, B03, B04, B08, B11]
    B08 is NIR, B04 is Red
    """
    if bands.shape[2] < 4:
        return 0.0
    
    # Normalize bands to 0-1 range (Sentinel-2 values are typically 0-10000)
    red = bands[:, :, 2].astype(np.float32) / 10000.0  # B04
    nir = bands[:, :, 3].astype(np.float32) / 10000.0  # B08
    
    # Avoid division by zero
    denominator = nir + red
    denominator = np.where(denominator == 0, 1e-10, denominator)
    
    ndvi = (nir - red) / denominator
    
    # Clip to valid range [-1, 1]
    ndvi = np.clip(ndvi, -1, 1)
    
    # Return mean NDVI value
    return float(np.nanmean(ndvi))


def calculate_ndwi(bands):
    """
    Calculate NDWI (Normalized Difference Water Index) from satellite bands.
    NDWI = (Green - NIR) / (Green + NIR)
    Alternative: NDWI = (Green - SWIR) / (Green + SWIR) - using SWIR for better water detection
    bands: array with shape (height, width, 5) where [B02, B03, B04, B08, B11]
    B03 is Green, B11 is SWIR
    """
    if bands.shape[2] < 5:
        return 0.0
    
    # Normalize bands to 0-1 range
    green = bands[:, :, 1].astype(np.float32) / 10000.0  # B03
    swir = bands[:, :, 4].astype(np.float32) / 10000.0   # B11
    
    # Avoid division by zero
    denominator = green + swir
    denominator = np.where(denominator == 0, 1e-10, denominator)
    
    ndwi = (green - swir) / denominator
    
    # Clip to valid range [-1, 1]
    ndwi = np.clip(ndwi, -1, 1)
    
    # Return mean NDWI value (higher = more water)
    return float(np.nanmean(ndwi))


def get_road_density(lat, lon, radius_meters=500):
    """
    Calculate road density using OpenStreetMap Overpass API.
    Returns a score from 0-1 indicating road density in the area.
    """
    try:
        # Calculate bounding box around the point
        # Approximate: 1 degree latitude ≈ 111 km
        # 1 degree longitude ≈ 111 km * cos(latitude)
        lat_offset = radius_meters / 111000
        lon_offset = radius_meters / (111000 * np.cos(np.radians(lat)))
        
        bbox = f"{lat - lat_offset},{lon - lon_offset},{lat + lat_offset},{lon + lon_offset}"
        
        # Overpass API query to get roads
        query = f"""
        [out:json][timeout:25];
        (
          way["highway"~"^(primary|secondary|tertiary|residential|unclassified|service|trunk|motorway)$"]({bbox});
        );
        out geom;
        """
        
        url = "https://overpass-api.de/api/interpreter"
        response = requests.post(url, data={"data": query}, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get("elements", [])
            
            # Calculate total road length
            total_length = 0.0
            for element in elements:
                if "geometry" in element:
                    geometry = element["geometry"]
                    if len(geometry) > 1:
                        # Calculate approximate length of road segment
                        for i in range(len(geometry) - 1):
                            lat1, lon1 = geometry[i]["lat"], geometry[i]["lon"]
                            lat2, lon2 = geometry[i+1]["lat"], geometry[i+1]["lon"]
                            # Haversine distance approximation
                            dlat = np.radians(lat2 - lat1)
                            dlon = np.radians(lon2 - lon1)
                            a = np.sin(dlat/2)**2 + np.cos(np.radians(lat1)) * np.cos(np.radians(lat2)) * np.sin(dlon/2)**2
                            c = 2 * np.arcsin(np.sqrt(a))
                            distance_km = 6371 * c
                            total_length += distance_km
            
            # Normalize: road density score (km/km²)
            # Area in km²
            area_km2 = (2 * lat_offset * 111) * (2 * lon_offset * 111 * np.cos(np.radians(lat)))
            if area_km2 > 0:
                density = total_length / area_km2
                # Normalize to 0-1 scale (assuming max reasonable density is ~20 km/km²)
                normalized_density = min(density / 20.0, 1.0)
                return float(normalized_density)
            else:
                return 0.0
        else:
            # If API fails, return a default value
            return 0.3  # Medium density assumption
    except Exception as e:
        print(f"Error fetching road density: {e}")
        return 0.3  # Default medium density


def extract_all_features(lat, lon):
    """
    Extract all visual and location-based features for a given location.
    Returns a dictionary with NDVI, NDWI, and road_density.
    """
    try:
        # Fetch satellite bands
        bands = fetch_satellite_bands(lat, lon)
        
        # Calculate indices
        ndvi = calculate_ndvi(bands)
        ndwi = calculate_ndwi(bands)
        
        # Get road density (this might take a moment)
        road_density = get_road_density(lat, lon)
        
        return {
            "ndvi": ndvi,
            "ndwi": ndwi,
            "road_density": road_density,
            "success": True
        }
    except Exception as e:
        print(f"Error extracting features: {e}")
        return {
            "ndvi": 0.0,
            "ndwi": 0.0,
            "road_density": 0.3,
            "success": False,
            "error": str(e)
        }

