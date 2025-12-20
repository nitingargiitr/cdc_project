import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import joblib
import os

print("=" * 70)
print("🚀 TRAINING PROPERTY PRICE PREDICTION MODEL WITH ALL FEATURES")
print("   (Optimized with Hyperparameter Tuning & Regularization)")
print("=" * 70)

# Load pre-split training and validation data
print("\n📥 Loading pre-split training data...")
df_train = pd.read_excel("data/train.xlsx")
print(f"Training data shape: {df_train.shape}")

print("📥 Loading pre-split validation data...")
df_validation = pd.read_excel("data/validation.xlsx")
print(f"Validation data shape: {df_validation.shape}")

# Define all features (exclude id and price)
feature_columns = [
    "bedrooms", "bathrooms", "sqft_living", "sqft_lot", "floors",
    "waterfront", "view", "condition", "grade", "sqft_above",
    "sqft_basement", "yr_built", "yr_renovated", "zipcode",
    "lat", "long", "sqft_living15", "sqft_lot15"
]

print(f"\n📊 Using {len(feature_columns)} features:")
print(f"   {', '.join(feature_columns)}")

# Prepare training features and target
print("\n🔧 Preparing training data...")
X_train = df_train[feature_columns].astype(np.float64)
y_train = df_train["price"].astype(np.float64)

# Remove any NaN values
X_train = X_train.dropna()
y_train = y_train[X_train.index]

# Prepare validation features and target
print("🔧 Preparing validation data...")
X_val = df_validation[feature_columns].astype(np.float64)
y_val = df_validation["price"].astype(np.float64)

X_val = X_val.dropna()
y_val = y_val[X_val.index]

print(f"Training set: {X_train.shape[0]} samples")
print(f"Validation set: {X_val.shape[0]} samples")

# Train model with optimized parameters
print("\n🤖 Training RandomForest model with optimized parameters...")
print("   (n_estimators=200, max_depth=20, min_samples_leaf=2)")

model = RandomForestRegressor(
    n_estimators=200,
    max_depth=20,
    min_samples_leaf=2,
    min_samples_split=5,
    max_features='sqrt',
    random_state=42,
    n_jobs=-1,
    verbose=1
)

model.fit(X_train, y_train)
print("✅ Model training completed!")

# Evaluate on training set
print("\n" + "=" * 70)
print("📈 TRAINING SET PERFORMANCE")
print("=" * 70)
y_train_pred = model.predict(X_train)
train_r2 = r2_score(y_train, y_train_pred)
train_mae = mean_absolute_error(y_train, y_train_pred)
train_rmse = np.sqrt(mean_squared_error(y_train, y_train_pred))

print(f"R² Score:        {train_r2:.6f}")
print(f"Mean Absolute Error (MAE):  ${train_mae:,.2f}")
print(f"Root Mean Squared Error (RMSE): ${train_rmse:,.2f}")

# Evaluate on validation set
print("\n" + "=" * 70)
print("🎯 VALIDATION SET PERFORMANCE")
print("=" * 70)
y_val_pred = model.predict(X_val)
val_r2 = r2_score(y_val, y_val_pred)
val_mae = mean_absolute_error(y_val, y_val_pred)
val_rmse = np.sqrt(mean_squared_error(y_val, y_val_pred))

print(f"R² Score:        {val_r2:.6f}")
print(f"Mean Absolute Error (MAE):  ${val_mae:,.2f}")
print(f"Root Mean Squared Error (RMSE): ${val_rmse:,.2f}")

# Check for overfitting
overfitting_indicator = train_r2 - val_r2
print(f"\nOverfitting Check (Train R² - Val R²): {overfitting_indicator:.6f}")
if overfitting_indicator > 0.1:
    print("⚠️  Warning: Possible overfitting detected!")
elif overfitting_indicator < 0:
    print("⚠️  Warning: Model performing worse on validation set!")
else:
    print("✅ Good generalization - no significant overfitting")

# Feature importance
print("\n" + "=" * 70)
print("🎯 FEATURE IMPORTANCE (Top 10)")
print("=" * 70)
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)

for idx, row in feature_importance.head(10).iterrows():
    print(f"{row['feature']:20s}: {row['importance']:.6f} {'█' * int(row['importance'] * 100)}")

# Save model
os.makedirs("model", exist_ok=True)
model_path = os.path.join("model", "price_model.pkl")
joblib.dump(model, model_path)
print(f"\n✅ Model saved to {model_path}")

# Save feature names
feature_names_path = os.path.join("model", "feature_names.txt")
with open(feature_names_path, 'w') as f:
    f.write('\n'.join(feature_columns))
print(f"✅ Feature names saved to {feature_names_path}")

# Save validation predictions for analysis
val_results = pd.DataFrame({
    'actual_price': y_val,
    'predicted_price': y_val_pred,
    'error': y_val - y_val_pred,
    'abs_error': abs(y_val - y_val_pred)
})
val_results_path = os.path.join("model", "validation_results.csv")
val_results.to_csv(val_results_path, index=False)
print(f"✅ Validation results saved to {val_results_path}")

print("\n" + "=" * 70)
print("✨ Training completed successfully!")
print(f"   Validation R²: {val_r2:.6f} | MAE: ${val_mae:,.0f}")
if val_r2 > 0.85:
    print("🎉 Excellent model performance!")
elif val_r2 > 0.80:
    print("✅ Good model performance!")
else:
    print("⚠️  Model needs improvement")
