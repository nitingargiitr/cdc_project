from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import joblib
import os
from fastapi.responses import Response
from backend.sentinel_fetcher import fetch_satellite_image
from backend.feature_extractor import extract_all_features, calculate_ndvi, calculate_ndwi, fetch_satellite_bands, get_road_density
from backend.nearby_amenities import get_nearby_amenities
import io
from PIL import Image
import numpy as np
import requests

app = FastAPI()

# Add CORS middleware to allow Streamlit frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(BASE_DIR, "model", "price_model.pkl")

# Load the model
try:
    model = joblib.load(MODEL_PATH)
except FileNotFoundError:
    print(f"Warning: Model not found at {MODEL_PATH}. Please train the model first.")
    model = None


@app.get("/predict")
def predict(bedrooms: int, bathrooms: float, sqft_living: int, lat: float = None, lon: float = None):
    """
    Predict property price based on bedrooms, bathrooms, sqft_living, and location features.
    If location is provided, extracts NDVI, NDWI, and road density features.
    """
    if model is None:
        return {"error": "Model not loaded. Please train the model first."}
    
    # Start with basic features
    features = [bedrooms, bathrooms, sqft_living]
    
    # Extract location-based features if coordinates provided
    location_features = {}
    if lat is not None and lon is not None:
        try:
            location_data = extract_all_features(lat, lon)
            ndvi = location_data.get("ndvi", 0.0)
            ndwi = location_data.get("ndwi", 0.0)
            road_density = location_data.get("road_density", 0.3)
            
            # Check if model expects 6 features (basic + location) or 3 (basic only)
            # Try with all features first
            try:
                price = model.predict([[bedrooms, bathrooms, sqft_living, ndvi, ndwi, road_density]])
                location_features = {
                    "ndvi": ndvi,
                    "ndwi": ndwi,
                    "road_density": road_density
                }
            except ValueError:
                # Model only expects 3 features (old model), use basic features only
                price = model.predict([[bedrooms, bathrooms, sqft_living]])
                location_features = {
                    "ndvi": ndvi,
                    "ndwi": ndwi,
                    "road_density": road_density,
                    "note": "Location features extracted but model not yet retrained to use them"
                }
        except Exception as e:
            # If feature extraction fails, fall back to basic prediction
            price = model.predict([[bedrooms, bathrooms, sqft_living]])
            location_features = {"error": str(e)}
    else:
        # No location provided, use basic features only
        price = model.predict([[bedrooms, bathrooms, sqft_living]])
    
    return {
        "predicted_price": float(price[0]),
        "location_features": location_features
    }


@app.get("/satellite")
def get_satellite(lat: float, lon: float):
    """
    Fetch satellite image for given coordinates.
    """
    try:
        image_array = fetch_satellite_image(lat, lon)
        
        # Ensure image is in correct format
        if len(image_array.shape) == 3 and image_array.shape[2] == 3:
            image = Image.fromarray(image_array, 'RGB')
        else:
            # Fallback: convert to RGB
            import numpy as np
            if len(image_array.shape) == 2:
                image_array = np.stack([image_array, image_array, image_array], axis=-1)
            image = Image.fromarray(image_array.astype(np.uint8), 'RGB')
        
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        buf.seek(0)
        return Response(content=buf.read(), media_type="image/png")
    except Exception as e:
        import traceback
        error_msg = f"Failed to fetch satellite image: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        # Return JSON error instead of image
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to fetch satellite image: {str(e)}"}
        )


@app.get("/ndvi")
def get_ndvi(lat: float, lon: float):
    """
    Calculate NDVI (greenery index) for given coordinates.
    Returns a value between -1 and 1, where higher values indicate more vegetation.
    """
    try:
        bands = fetch_satellite_bands(lat, lon)
        ndvi = calculate_ndvi(bands)
        return {"ndvi": ndvi, "interpretation": "Higher values indicate more vegetation/greenery"}
    except Exception as e:
        return {"error": f"Failed to calculate NDVI: {str(e)}"}


@app.get("/ndwi")
def get_ndwi(lat: float, lon: float):
    """
    Calculate NDWI (water index) for given coordinates.
    Returns a value between -1 and 1, where higher values indicate more water nearby.
    """
    try:
        bands = fetch_satellite_bands(lat, lon)
        ndwi = calculate_ndwi(bands)
        return {"ndwi": ndwi, "interpretation": "Higher values indicate more water bodies nearby"}
    except Exception as e:
        return {"error": f"Failed to calculate NDWI: {str(e)}"}


@app.get("/road-density")
def get_road_density_endpoint(lat: float, lon: float):
    """
    Calculate road density for given coordinates using OpenStreetMap.
    Returns a normalized score between 0 and 1.
    """
    try:
        density = get_road_density(lat, lon)
        return {
            "road_density": density,
            "interpretation": "Higher values indicate more roads/urbanization in the area"
        }
    except Exception as e:
        return {"error": f"Failed to calculate road density: {str(e)}"}


@app.get("/features")
def get_all_features(lat: float, lon: float):
    """
    Extract all location-based features (NDVI, NDWI, road density) at once.
    """
    try:
        features = extract_all_features(lat, lon)
        return features
    except Exception as e:
        return {"error": f"Failed to extract features: {str(e)}"}


@app.get("/explain")
def explain_price(bedrooms: int, bathrooms: float, sqft_living: int, lat: float = None, lon: float = None, use_openai: bool = True):
    """
    Generate a human-readable explanation of why a property has a certain predicted price.
    Optionally uses OpenAI to enhance the explanation.
    """
    if model is None:
        return {"error": "Model not loaded. Please train the model first."}
    
    # Get prediction and features
    prediction_result = predict(bedrooms, bathrooms, sqft_living, lat, lon)
    predicted_price = prediction_result["predicted_price"]
    location_features = prediction_result.get("location_features", {})
    
    # Generate base explanation
    explanations = []
    
    # Property size explanations
    if sqft_living > 2500:
        explanations.append("large living space")
    elif sqft_living < 1000:
        explanations.append("compact living space")
    
    # Bedroom/bathroom explanations
    if bedrooms >= 4:
        explanations.append("multiple bedrooms")
    if bathrooms >= 3:
        explanations.append("multiple bathrooms")
    
    # Location-based explanations
    if isinstance(location_features, dict) and "ndvi" in location_features:
        ndvi = location_features.get("ndvi", 0)
        ndwi = location_features.get("ndwi", 0)
        road_density = location_features.get("road_density", 0.3)
        
        if ndvi > 0.3:
            explanations.append("green, vegetated area")
        elif ndvi < 0.1:
            explanations.append("urbanized area with limited greenery")
        
        if ndwi > 0.2:
            explanations.append("proximity to water bodies")
        
        if road_density > 0.6:
            explanations.append("high road density and good connectivity")
        elif road_density < 0.2:
            explanations.append("low traffic area")
    
    # Price tier explanation
    if predicted_price > 800000:
        price_tier = "premium"
    elif predicted_price > 500000:
        price_tier = "mid-to-high"
    elif predicted_price > 300000:
        price_tier = "mid-range"
    else:
        price_tier = "affordable"
    
    # Build base explanation text
    if explanations:
        base_explanation = f"This property is valued in the {price_tier} range (${predicted_price:,.0f}) because it features {', '.join(explanations)}."
    else:
        base_explanation = f"This property is valued at ${predicted_price:,.0f} based on its size and features."
    
    # Try to enhance with OpenAI
    explanation_text = base_explanation
    location_context = ""
    try:
        from backend.openai_helper import enhance_explanation, analyze_location_context
        if use_openai:
            features_dict = {
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "sqft_living": sqft_living,
                **location_features
            }
            explanation_text = enhance_explanation(predicted_price, features_dict, base_explanation)
            if lat is not None and lon is not None:
                location_context = analyze_location_context(lat, lon, location_features)
    except ImportError:
        pass  # OpenAI not available
    except Exception:
        pass  # OpenAI failed, use base explanation
    
    return {
        "predicted_price": predicted_price,
        "explanation": explanation_text,
        "location_context": location_context,
        "features": {
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "sqft_living": sqft_living,
            **location_features
        }
    }


@app.get("/nearby-amenities")
def nearby_amenities(lat: float, lon: float, radius: int = 1000):
    """
    Get nearby amenities (schools, hospitals, shops, etc.) for a location.
    User-friendly feature for normal users.
    """
    try:
        print(f"Fetching amenities for lat={lat}, lon={lon}, radius={radius}")
        amenities = get_nearby_amenities(lat, lon, radius)
        print(f"Amenities result: {amenities}")
        return amenities
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Amenities endpoint error: {error_msg}")
        print(traceback.format_exc())
        return {"error": f"Error: {error_msg}", "total": 0, "by_category": {}}


