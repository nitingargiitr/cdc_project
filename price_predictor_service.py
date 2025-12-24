"""
Direct Python service for price prediction, features extraction, and amenities.
Replaces HTTP calls for cloud-safe Streamlit deployment.
"""
import joblib
import numpy as np
import os
from typing import Dict, List
import streamlit as st
from feature_extractor import extract_all_features
from nearby_amenities import get_nearby_amenities as get_amenities_data


@st.cache_resource
def load_price_model():
    """Load the pre-trained price prediction model"""
    try:
        model_path = os.path.join(os.path.dirname(__file__), "model", "price_model.pkl")
        if os.path.exists(model_path):
            return joblib.load(model_path)
    except Exception as e:
        st.warning(f"Could not load model: {e}")
    return None


@st.cache_data(ttl=3600, max_entries=128)
def get_features(lat: float, lon: float) -> Dict:
    """Return satellite features (NDVI, NDWI, road density) with caching."""
    try:
        features = extract_all_features(lat, lon)
        return {
            "ndvi": features.get("ndvi", 0.0),
            "ndwi": features.get("ndwi", 0.0),
            "road_density": features.get("road_density", 0.3)
        }
    except Exception as e:
        st.warning(f"Could not fetch satellite features: {e}")
        return {
            "ndvi": 0.0,
            "ndwi": 0.0,
            "road_density": 0.3
        }


def predict_price(bedrooms: int, bathrooms: float, sqft_living: int, lat: float, lon: float) -> Dict:
    """Predict property price using all 18 features the model was trained with."""
    try:
        model = load_price_model()
        
        if model is None:
            return {
                "predicted_price": 500000,
                "explanation": "Using default estimate",
                "location_context": "Model not available",
                "features": {
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "sqft_living": sqft_living
                }
            }
        
        # Get satellite features
        sat_features = get_features(lat, lon)
        
        # Default values for other features
        default_features = {
            "sqft_lot": sqft_living * 2,
            "floors": 1.0,
            "waterfront": 0,
            "view": 0,
            "condition": 3,
            "grade": 7,
            "sqft_above": sqft_living * 0.8,
            "sqft_basement": sqft_living * 0.2,
            "yr_built": 2000,
            "yr_renovated": 0,
            "zipcode": 98001,
            "lat": lat,
            "long": lon,
            "sqft_living15": sqft_living,
            "sqft_lot15": sqft_living * 2
        }
        
        # Prepare features in the exact order the model expects
        X = np.array([[
            float(bedrooms),    # bedrooms
            float(bathrooms),   # bathrooms
            float(sqft_living), # sqft_living
            default_features["sqft_lot"],
            default_features["floors"],
            default_features["waterfront"],
            default_features["view"],
            default_features["condition"],
            default_features["grade"],
            default_features["sqft_above"],
            default_features["sqft_basement"],
            default_features["yr_built"],
            default_features["yr_renovated"],
            default_features["zipcode"],
            float(lat),        # lat
            float(lon),        # long
            default_features["sqft_living15"],
            default_features["sqft_lot15"]
        ]], dtype=np.float64)
        
        # Make prediction
        predicted_price = float(model.predict(X)[0])
        
        # Generate explanation
        reasons = []
        if bedrooms >= 3:
            reasons.append(f"{bedrooms} bedrooms add value")
        if bathrooms >= 2:
            reasons.append(f"{bathrooms} bathrooms increase desirability")
        if sqft_living > 1500:
            reasons.append(f"Large living area ({sqft_living} sqft)")
        elif sqft_living < 800:
            reasons.append("Compact living space")
            
        if sat_features.get('ndvi', 0) > 0.3:
            reasons.append("Good greenery in the area")
        if sat_features.get('road_density', 0) > 0.5:
            reasons.append("Well-connected location")
            
        explanation = "This price is based on " + ", ".join(reasons) if reasons else "Standard market pricing"
        
        location_context = "Prime location" if (sat_features.get('ndvi', 0) > 0.3 and 
                                             sat_features.get('road_density', 0) > 0.4) else "Standard location"
        
        return {
            "predicted_price": max(100000, predicted_price),
            "explanation": explanation,
            "location_context": location_context,
            "features": {
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "sqft_living": sqft_living,
                **sat_features,
                **{k: v for k, v in default_features.items() if k not in ['lat', 'long']}
            }
        }
    except Exception as e:
        st.error(f"Prediction error: {str(e)}")
        return {
            "predicted_price": 500000,
            "explanation": "Error in prediction",
            "location_context": "Error in prediction",
            "features": {}
        }


@st.cache_data(ttl=3600, max_entries=128)
def get_nearby_amenities(lat: float, lon: float, radius: int = 1000) -> Dict:
    """Return nearby amenities with caching to prevent redundant API calls."""
    try:
        return get_amenities_data(lat, lon, radius)
    except Exception as e:
        return {
            "total": 0,
            "by_category": {},
            "error": f"Could not fetch amenities: {str(e)}"
        }