"""
Train a multimodal property price prediction model.
Combines tabular features (bedrooms, bathrooms, sqft_living) with 
location-based features (NDVI, NDWI, road_density).
"""
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import os
import sys
import numpy as np

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.feature_extractor import extract_all_features

def train_multimodal_model(sample_size=None):
    """
    Train a model that uses both tabular and location-based features.
    For locations in training data, extracts NDVI, NDWI, and road density.
    
    Args:
        sample_size: If provided, randomly sample this many rows for faster training.
                     Useful for large datasets. Set to None to use all data.
    """
    print("Loading training data...")
    df = pd.read_excel("data/train(1).xlsx")
    
    print(f"Training data shape: {df.shape}")
    print(f"Columns: {df.columns.tolist()}")
    
    # Sample data if requested (for faster training)
    if sample_size and sample_size < len(df):
        print(f"\n📊 Sampling {sample_size} rows for faster training...")
        df = df.sample(n=sample_size, random_state=42).reset_index(drop=True)
        print(f"Using {len(df)} rows for training")
    
    # Check if we have location data (lat/long columns)
    # Note: dataset uses 'long' not 'lon'
    has_location = 'lat' in df.columns and 'long' in df.columns
    
    if not has_location:
        print("⚠️  Warning: No lat/long columns found in training data.")
        print("Training basic model with tabular features only.")
        print("To use location features, add 'lat' and 'long' columns to your training data.")
        
        # Train basic model
        X = df[["bedrooms", "bathrooms", "sqft_living"]]
        y = df["price"]
        
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X, y)
        
        model_path = os.path.join("model", "price_model.pkl")
        joblib.dump(model, model_path)
        print(f"✅ Basic model saved to {model_path}")
        return
    
    # Extract location features for each row
    print("Extracting location-based features (this may take a while)...")
    features_list = []
    
    for idx, row in df.iterrows():
        if idx % 10 == 0:
            print(f"Processing row {idx+1}/{len(df)}...")
        
        lat = row['lat']
        lon = row['long']  # Dataset uses 'long' not 'lon'
        
        try:
            location_features = extract_all_features(lat, lon)
            features_list.append({
                'ndvi': location_features.get('ndvi', 0.0),
                'ndwi': location_features.get('ndwi', 0.0),
                'road_density': location_features.get('road_density', 0.3)
            })
        except Exception as e:
            print(f"Error extracting features for row {idx}: {e}")
            features_list.append({
                'ndvi': 0.0,
                'ndwi': 0.0,
                'road_density': 0.3
            })
    
    # Combine tabular and location features
    location_df = pd.DataFrame(features_list)
    
    X_tabular = df[["bedrooms", "bathrooms", "sqft_living"]]
    X_combined = pd.concat([X_tabular, location_df], axis=1)
    
    y = df["price"]
    
    print(f"Training multimodal model with {X_combined.shape[1]} features...")
    print(f"Feature names: {X_combined.columns.tolist()}")
    
    # Train model
    model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    model.fit(X_combined, y)
    
    # Evaluate
    train_score = model.score(X_combined, y)
    print(f"✅ Model trained! R² score: {train_score:.4f}")
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X_combined.columns,
        'importance': model.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\n📊 Feature Importance:")
    print(feature_importance.to_string(index=False))
    
    # Save model
    model_path = os.path.join("model", "price_model.pkl")
    joblib.dump(model, model_path)
    print(f"\n✅ Multimodal model saved to {model_path}")
    
    # Also save feature names for reference
    feature_names_path = os.path.join("model", "feature_names.txt")
    with open(feature_names_path, 'w') as f:
        f.write('\n'.join(X_combined.columns.tolist()))
    print(f"✅ Feature names saved to {feature_names_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Train multimodal property price prediction model")
    parser.add_argument(
        "--sample-size",
        type=int,
        default=None,
        help="Number of rows to sample for training (default: use all data). "
             "Recommended: 500-1000 for faster training with location features."
    )
    
    args = parser.parse_args()
    train_multimodal_model(sample_size=args.sample_size)

