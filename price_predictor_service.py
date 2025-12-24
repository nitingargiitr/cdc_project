"""
Direct Python service for price prediction, features extraction, and amenities.
Replaces HTTP calls for cloud-safe Streamlit deployment.
"""
import joblib
import numpy as np
import os
import random
from typing import Dict, List, Tuple, Optional
import streamlit as st
from feature_extractor import extract_all_features
from nearby_amenities import get_nearby_amenities as get_amenities_data

# Feature names in the exact order expected by the model
FEATURE_NAMES = [
    'bedrooms', 'bathrooms', 'sqft_living', 'sqft_lot', 'floors',
    'waterfront', 'view', 'condition', 'grade', 'sqft_above',
    'sqft_basement', 'yr_built', 'yr_renovated', 'zipcode', 'lat',
    'long', 'sqft_living15', 'sqft_lot15'
]

@st.cache_resource
def load_price_model():
    """Load the pre-trained price prediction model"""
    try:
        model_path = os.path.join(os.path.dirname(__file__), "model", "price_model.pkl")
        if os.path.exists(model_path):
            model = joblib.load(model_path)
            st.success("Successfully loaded price prediction model")
            return model
        else:
            st.warning("Price model file not found. Using fallback pricing.")
    except Exception as e:
        st.error(f"Error loading price model: {str(e)}")
    return None

@st.cache_data(ttl=3600, max_entries=128)
def get_features(lat: float, lon: float) -> Dict:
    """Return satellite features (NDVI, NDWI, road density) with caching."""
    try:
        features = extract_all_features(lat, lon)
        return {
            "ndvi": float(features.get("ndvi", 0.0)),
            "ndwi": float(features.get("ndwi", 0.0)),
            "road_density": float(features.get("road_density", 0.3)),
            "zipcode": int(str(int(lat*100)) + str(int(abs(lon)*100))[-4:]) % 100000,
            "condition": 3,  # Default condition (1-5)
            "grade": 7,      # Default grade (1-13)
            "view": 0,       # Default view (0-4)
            "waterfront": 0  # Default waterfront (0 or 1)
        }
    except Exception as e:
        st.warning(f"Could not fetch satellite features: {e}")
        return {
            "ndvi": 0.0,
            "ndwi": 0.0,
            "road_density": 0.3,
            "zipcode": 98001,
            "condition": 3,
            "grade": 7,
            "view": 0,
            "waterfront": 0
        }

def create_feature_dict(bedrooms: int, bathrooms: float, sqft_living: int, lat: float, lon: float, 
                      location_features: Dict) -> Dict[str, float]:
    """Create a dictionary of all features needed for prediction."""
    # Base features
    features = {
        'bedrooms': float(bedrooms),
        'bathrooms': float(bathrooms),
        'sqft_living': float(sqft_living),
        'lat': float(lat),
        'long': float(lon),
    }
    
    # Add satellite and location features
    features.update({
        'ndvi': float(location_features.get('ndvi', 0.0)),
        'ndwi': float(location_features.get('ndwi', 0.0)),
        'road_density': float(location_features.get('road_density', 0.3)),
        'zipcode': int(location_features.get('zipcode', 98001)),
        'condition': int(location_features.get('condition', 3)),
        'grade': int(location_features.get('grade', 7)),
        'view': int(location_features.get('view', 0)),
        'waterfront': int(location_features.get('waterfront', 0)),
    })
    
    # Calculate derived features
    features['sqft_lot'] = float(sqft_living * (2.0 + random.uniform(-0.1, 0.5)))  # 1.9x to 2.5x living area
    features['floors'] = float(1.0 + (bedrooms // 2) * 0.5)  # More bedrooms = more floors
    features['sqft_above'] = float(sqft_living * 0.8)  # 80% of living area is above ground
    features['sqft_basement'] = float(sqft_living * 0.2)  # 20% is basement
    features['yr_built'] = float(2000 + (random.randint(-10, 5)))  # Random year near 2000
    features['yr_renovated'] = float(0)  # Most properties not renovated
    features['sqft_living15'] = float(sqft_living * (0.9 + random.uniform(0, 0.2)))  # Nearby properties similar size
    features['sqft_lot15'] = float(features['sqft_lot'] * (0.9 + random.uniform(0, 0.2)))  # Nearby lots similar size
    
    return features

def predict_price(bedrooms: int, bathrooms: float, sqft_living: int, lat: float, lon: float) -> Dict:
    """
    Predict property price using the trained model with all required features.
    
    Args:
        bedrooms: Number of bedrooms
        bathrooms: Number of bathrooms (can be float for half-baths)
        sqft_living: Living area in square feet
        lat: Latitude of the property
        lon: Longitude of the property
        
    Returns:
        Dictionary containing predicted price, explanation, and features
    """
    try:
        # Get model and location features
        model = load_price_model()
        location_features = get_features(lat, lon)
        
        if model is None:
            # Fallback to a simple estimate if model isn't available
            return get_fallback_prediction(bedrooms, bathrooms, sqft_living, lat, lon, location_features)
        
        # Create complete feature dictionary
        features = create_feature_dict(bedrooms, bathrooms, sqft_living, lat, lon, location_features)
        
        # Prepare features in the exact order expected by the model
        X = np.array([[features[name] for name in FEATURE_NAMES]], dtype=np.float32)
        
        # Make prediction
        predicted_price = float(model.predict(X)[0])
        
        # Ensure price is reasonable (not negative or too low)
        predicted_price = max(100000, predicted_price)
        
        # Generate explanation based on key factors
        reasons = generate_explanation(features)
        location_context = get_location_context(features)
        
        # Prepare return value with all features and metadata
        return {
            "predicted_price": predicted_price,
            "explanation": "Price is based on " + ", ".join(reasons) if reasons else "Standard market pricing",
            "location_context": location_context,
            "features": {
                **features,
                "price_per_sqft": predicted_price / features['sqft_living'] if features['sqft_living'] > 0 else 0
            }
        }
    except Exception as e:
        st.error(f"Error in price prediction: {str(e)}")
        # Fall back to a simple estimate if prediction fails
        return get_fallback_prediction(bedrooms, bathrooms, sqft_living, lat, lon, {})

def generate_explanation(features: Dict[str, float]) -> List[str]:
    """Generate human-readable explanations for the price prediction."""
    reasons = []
    
    # Property size and rooms
    if features['sqft_living'] > 2000:
        reasons.append(f"spacious {int(features['sqft_living'])} sqft")
    elif features['sqft_living'] < 800:
        reasons.append("compact size")
    
    if features['bedrooms'] >= 4:
        reasons.append(f"{int(features['bedrooms'])} bedrooms")
    
    if features['bathrooms'] >= 2.5:
        reasons.append(f"{features['bathrooms']} bathrooms")
    
    # Location features
    if features.get('ndvi', 0) > 0.4:
        reasons.append("lush green surroundings")
    elif features.get('ndvi', 0) < 0.1:
        reasons.append("urban setting")
    
    if features.get('ndwi', 0) > 0.2:
        reasons.append("waterfront or near water")
    
    if features.get('road_density', 0) > 0.6:
        reasons.append("excellent connectivity")
    
    # Property condition
    if features.get('grade', 7) >= 9:
        reasons.append("high-end finishes")
    
    return reasons

def get_location_context(features: Dict[str, float]) -> str:
    """Generate a human-readable location context."""
    ndvi = features.get('ndvi', 0)
    ndwi = features.get('ndwi', 0)
    road_density = features.get('road_density', 0.3)
    
    if ndvi > 0.4 and ndwi > 0.2:
        return "Premium location with greenery and water access"
    elif ndvi > 0.3 or ndwi > 0.15:
        return "Desirable location with good features"
    elif road_density > 0.6:
        return "Urban area with excellent connectivity"
    return "Standard residential location"

def get_fallback_prediction(bedrooms: int, bathrooms: float, sqft_living: int, 
                          lat: float, lon: float, location_features: Dict) -> Dict:
    """Generate a fallback price prediction when the model is not available."""
    # Base price per sqft with location adjustment
    base_price_per_sqft = 300.0
    
    # Adjust for location (using lat/lon to create some variation)
    location_factor = 0.8 + ((lat % 0.1) + (lon % 0.1)) * 2.5
    
    # Adjust for property features
    bedroom_factor = 1.0 + (bedrooms - 2) * 0.1  # 10% per bedroom over 2
    bathroom_factor = 1.0 + (bathrooms - 1) * 0.15  # 15% per bathroom over 1
    
    # Calculate price
    predicted_price = int(sqft_living * base_price_per_sqft * location_factor * bedroom_factor * bathroom_factor)
    
    # Get location context
    location_context = get_location_context(location_features)
    
    # Generate explanation
    reasons = []
    if bedrooms >= 3:
        reasons.append(f"{bedrooms} bedrooms")
    if bathrooms >= 2:
        reasons.append(f"{bathrooms} bathrooms")
    if sqft_living > 1500:
        reasons.append(f"{sqft_living} sqft")
    
    return {
        "predicted_price": max(100000, predicted_price),
        "explanation": "Fallback estimate based on " + ", ".join(reasons) if reasons else "Standard market pricing",
        "location_context": location_context,
        "features": {
            'bedrooms': float(bedrooms),
            'bathrooms': float(bathrooms),
            'sqft_living': float(sqft_living),
            'sqft_lot': float(sqft_living * 2),
            'floors': 1.0 + (bedrooms // 2) * 0.5,
            'waterfront': 0.0,
            'view': 0.0,
            'condition': 3.0,
            'grade': 7.0,
            'sqft_above': float(sqft_living * 0.8),
            'sqft_basement': float(sqft_living * 0.2),
            'yr_built': 2000.0,
            'yr_renovated': 0.0,
            'zipcode': 98001.0,
            'lat': float(lat),
            'long': float(lon),
            'sqft_living15': float(sqft_living),
            'sqft_lot15': float(sqft_living * 2),
            'ndvi': location_features.get('ndvi', 0.0),
            'ndwi': location_features.get('ndwi', 0.0),
            'road_density': location_features.get('road_density', 0.3),
            'price_per_sqft': predicted_price / sqft_living if sqft_living > 0 else 0
        },
        "is_fallback": True
    }

@st.cache_data(ttl=3600, max_entries=128)
def get_nearby_amenities(lat: float, lon: float, radius: int = 1000) -> Dict:
    """
    Return nearby amenities with caching to prevent redundant API calls.
    Includes fallback to mock data if the API call fails.
    """
    try:
        result = get_amenities_data(lat, lon, radius)
        if not result.get('by_category') or not any(result['by_category'].values()):
            raise ValueError("No amenities found in API response")
        return result
    except Exception as e:
        st.warning(f"Using mock amenities data due to: {str(e)}")
        return generate_mock_amenities(lat, lon, radius)

def generate_mock_amenities(lat: float, lon: float, radius: int) -> Dict:
    """Generate mock amenities data for demonstration purposes."""
    import random
    
    # Common amenity categories and types
    categories = {
        "Education": ["Elementary School", "High School", "College", "Library", "Daycare"],
        "Healthcare": ["Hospital", "Clinic", "Pharmacy", "Dentist", "Urgent Care"],
        "Shopping": ["Supermarket", "Mall", "Convenience Store", "Department Store", "Pharmacy"],
        "Dining": ["Restaurant", "Cafe", "Fast Food", "Bakery", "Bar"],
        "Transportation": ["Bus Stop", "Subway Station", "Train Station", "Parking"],
        "Recreation": ["Park", "Gym", "Swimming Pool", "Sports Field", "Playground"],
        "Services": ["Bank", "ATM", "Post Office", "Laundry", "Car Wash"]
    }
    
    # Generate random amenities
    amenities = []
    for category, types in categories.items():
        # Randomly select 1-3 amenities per category
        for _ in range(random.randint(1, 3)):
            name = f"{random.choice(types)} {random.choice(['Central', 'Main', 'City', 'Local'])}"
            amenities.append({
                "name": name,
                "type": random.choice(types).lower(),
                "distance": random.randint(100, radius),
                "category": category
            })
    
    # Group by category
    by_category = {}
    for amenity in amenities:
        category = amenity.pop('category')
        if category not in by_category:
            by_category[category] = []
        by_category[category].append(amenity)
    
    return {
        "total": len(amenities),
        "by_category": by_category,
        "convenience_score": random.randint(60, 95),
        "convenience_rating": random.choice(["Good", "Very Good", "Excellent"]),
        "is_mock_data": True
    }