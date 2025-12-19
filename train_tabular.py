import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib

df = pd.read_excel("data/train(1).xlsx")

X = df[["bedrooms", "bathrooms", "sqft_living"]]
y = df["price"]

model = RandomForestRegressor(n_estimators=100)
model.fit(X, y)

joblib.dump(model, "model/price_model.pkl")
print("Model saved")
