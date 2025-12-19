import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
import joblib

df = pd.read_excel("data/train(1).xlsx")

# ✅ Ensure consistent float64 dtype for all features
X = df[["bedrooms", "bathrooms", "sqft_living"]].astype(np.float64)
y = df["price"].astype(np.float64)

# Remove any NaN values
X = X.dropna()
y = y[X.index]

print(f"Training data shape: {X.shape}")
print(f"X dtype: {X.dtypes}")
print(f"y dtype: {y.dtype}")

model = RandomForestRegressor(n_estimators=100, random_state=42)
model.fit(X, y)

# Save model in root directory
joblib.dump(model, "price_model.pkl")
print("✅ Model saved to price_model.pkl")
