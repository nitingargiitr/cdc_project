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


# ✅ Load pre-trained model
@st.cache_resource
def load_price_model():
    """Load the pre-trained price prediction model"""
    try:
        model_path = os.path.join(os.path.dirname(__file__), "price_model.pkl")
        if os.path.exists(model_path):
            return joblib.load(model_path)
    except Exception as e:
        st.warning(f"Could not load model: {e}")
    return None


@st.cache_data(ttl=3600, max_entries=128)
def get_features(lat: float, lon: float) -> Dict:
    """Cached wrapper: return satellite features (NDVI, NDWI, road density).

    Caching reduces repeated SentinelHub/Overpass calls for the same location.
    """
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
    """
    Predict property price based on features.
    
    Args:
        bedrooms: Number of bedrooms
        bathrooms: Number of bathrooms
        sqft_living: Living area in square feet
        lat: Latitude
        lon: Longitude
        
    Returns:
        Dict with: predicted_price, explanation, location_context, features
    """
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
        
        # ✅ Prepare features for model prediction
        # The model expects: [bedrooms, bathrooms, sqft_living]
        X = np.array([[bedrooms, bathrooms, sqft_living]])
        predicted_price = float(model.predict(X)[0])
        
        # ✅ Generate explanation
        reasons = []
        
        # Property features
        if bedrooms >= 3:
            reasons.append(f"{bedrooms} bedrooms add value")
        if bathrooms >= 2:
            reasons.append(f"{bathrooms} bathrooms increase desirability")
        if sqft_living > 1500:
            reasons.append(f"Large living area ({sqft_living} sqft) adds premium")
        elif sqft_living < 800:
            reasons.append("Smaller property reduces price")
        
        # Location features
        ndvi = sat_features.get("ndvi", 0)
        ndwi = sat_features.get("ndwi", 0)
        road_density = sat_features.get("road_density", 0.3)
        
        if ndvi > 0.3:
            reasons.append("Green, park-like neighborhood increases value")
        if ndwi > 0.2:
            reasons.append("Water proximity adds premium")
        if road_density > 0.6:
            reasons.append("Excellent connectivity boosts price")
        
        explanation = " + ".join(reasons) if reasons else "Premium location"
        
        # Location context
        location_context = "Premium area" if predicted_price > 800000 else "Standard area"
        if ndvi > 0.3:
            location_context += " with excellent greenery"
        if road_density > 0.6:
            location_context += " and great connectivity"
        
        return {
            "predicted_price": predicted_price,
            "explanation": explanation,
            "location_context": location_context,
            "features": {
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "sqft_living": sqft_living,
                "ndvi": ndvi,
                "ndwi": ndwi,
                "road_density": road_density
            }
        }
    
    except Exception as e:
        return {
            "predicted_price": 500000,
            "explanation": f"Could not calculate: {str(e)}",
            "location_context": "Default estimate",
            "features": {
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "sqft_living": sqft_living,
                "ndvi": 0.0,
                "ndwi": 0.0,
                "road_density": 0.3
            }
        }


@st.cache_data(ttl=3600, max_entries=128)
def get_nearby_amenities(lat: float, lon: float, radius: int = 1000) -> Dict:
    """Cached wrapper: return nearby amenities using Overpass.

    Caching reduces Overpass requests for repeated lookups.
    """
    try:
        amenities = get_amenities_data(lat, lon, radius)
        return amenities
    except Exception as e:
        return {
            "total": 0,
            "by_category": {},
            "error": f"Could not fetch amenities: {str(e)}"
        }
