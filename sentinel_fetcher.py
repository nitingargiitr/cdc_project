from sentinelhub import (
    SentinelHubRequest,
    DataCollection,
    MimeType,
    CRS,
    BBox,
    bbox_to_dimensions
)
from .sentinel_config import get_sh_config

def fetch_satellite_image(lat, lon, size=512):
    """
    Fetch satellite image with proper scaling for display.
    Returns RGB image array scaled to 0-255.
    """
    bbox = BBox(
        bbox=[lon - 0.002, lat - 0.002, lon + 0.002, lat + 0.002],
        crs=CRS.WGS84
    )

    resolution = 10  # meters per pixel
    width, height = bbox_to_dimensions(bbox, resolution=resolution)
    # Ensure reasonable size
    width = min(width, size)
    height = min(height, size)

    # Improved evalscript with proper scaling for RGB display
    evalscript = """
    //VERSION=3
    function setup() {
        return {
            input: [{
                bands: ["B04", "B03", "B02"]
            }],
            output: { 
                bands: 3,
                sampleType: "UINT8"
            }
        };
    }

    function evaluatePixel(sample) {
        // Scale Sentinel-2 reflectance values (0-1) to 0-255 for RGB display
        // Apply gamma correction and contrast enhancement for better visualization
        var gain = 2.5;
        var gamma = 1.8;
        
        var R = Math.pow(Math.min(sample.B04 * gain, 1), 1/gamma) * 255;
        var G = Math.pow(Math.min(sample.B03 * gain, 1), 1/gamma) * 255;
        var B = Math.pow(Math.min(sample.B02 * gain, 1), 1/gamma) * 255;
        
        return [R, G, B];
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

    image = request.get_data()[0]
    
    # Ensure image is in correct format (uint8, 0-255)
    import numpy as np
    if image.dtype != np.uint8:
        # Clip and convert to uint8
        image = np.clip(image, 0, 255).astype(np.uint8)
    
    # If image is grayscale or has wrong shape, convert to RGB
    if len(image.shape) == 2:
        image = np.stack([image, image, image], axis=-1)
    elif image.shape[2] == 1:
        image = np.repeat(image, 3, axis=2)
    
    return image
