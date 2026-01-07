# 🏠 AI Property Price Predictor

An AI-powered property price prediction system using machine learning with 85.77% accuracy on validation data. The system combines 18 property features with RandomForest algorithm to deliver accurate price estimates.

---

##  Quick Stats

- **Model Accuracy**: 85.77% R² on unseen validation data
- **Features Used**: 18 property attributes
- **Training Samples**: 12,967
- **Validation Samples**: 3,242
- **Test Predictions**: 5,404

---

##  Features

- **Interactive Map Interface** - Streamlit web UI with folium maps for location selection
- **ML Price Prediction** - RandomForest model with 18 property features
- **Satellite Integration** - Optional Sentinel Hub imagery (NDVI, NDWI calculation)
- **Location Features** - Waterfront, view, condition, grade, and proximity metrics
- **Production Ready** - Serialized model in `model/price_model.pkl`

---

## 📁 Project Structure

```
cdc_project/
├── MAIN APPLICATION
│   ├── main.py                      # FastAPI backend server (REST API)
│   ├── app.py                       # Streamlit frontend (web UI)
│   ├── train_tabular.py             # Model training script
│   └── price_predictor_service.py   # Business logic
│
├── FEATURE & DATA MODULES
│   ├── feature_extractor.py         # Satellite feature extraction
│   ├── nearby_amenities.py          # POI searching
│   ├── sentinel_fetcher.py          # Sentinel Hub integration
│   ├── sentinel_config.py           # Configuration
│   └── openai_helper.py             # LLM integration
│
├── DATA FOLDER (data/)
│   ├── train.xlsx                   # Training set: 12,967 samples (80%)
│   ├── validation.xlsx              # Validation set: 3,242 samples (20%)
│   ├── test2.xlsx                   # Test set: 5,404 samples (holdout)
│   └── train(1).xlsx                # Original dataset: 16,209 samples
│
├── MODEL FOLDER (model/)
│   ├── price_model.pkl              # Trained RandomForest model (PRODUCTION)
│   ├── feature_names.txt            # Feature list for consistency
│   └── validation_results.csv       # Detailed validation predictions
│
├── OUTPUT
│   ├── predictions.csv              # Test set predictions
│   ├── requirements.txt             # Python dependencies
│   ├── pyproject.toml               # Project metadata
│   └── README.md                    # This file
│
└── CONFIG & DEPLOYMENT
    ├── .streamlit/                  # Streamlit configuration
    ├── .devcontainer/               # Docker dev container
    ├── runtime.txt                  # Python runtime version
    └── .gitattributes               # Git configuration
```

---

##  Model Performance

### Training Results (12,967 samples)
```
R² Score:  0.9565 
MAE:       $39,483.70
RMSE:      $75,498.32
```

### Validation Results (3,242 samples) - UNSEEN DATA 
```
R² Score:       0.8577  
MAE:            $73,640.01
RMSE:           $133,616.46
MAPE:           13.66%
Overfitting:    9.87% gap (No overfitting)
```

### Feature Importance (Top 10)
```
1. sqft_living          19.6%  ████████████████████
2. grade               16.9%  █████████████████
3. latitude            13.0%  █████████████
4. sqft_living15        9.3%  █████████
5. sqft_above           8.4%  ████████
6. bathrooms            6.9%  ███████
7. longitude            5.0%  █████
8. view                 3.7%  ████
9. yr_built             3.2%  ███
10. zipcode             3.0%  ███
```

---

##  Features Used in Model

The model uses **18 property features** for prediction:

| Category | Features |
|----------|----------|
| **Basic** | bedrooms, bathrooms, sqft_living, sqft_lot, floors |
| **Property Condition** | waterfront, view, condition, grade, sqft_above, sqft_basement |
| **Year Info** | yr_built, yr_renovated |
| **Location** | zipcode, lat, long |
| **Neighborhood** | sqft_living15, sqft_lot15 |

---

##  Installation & Setup

### Prerequisites
- Python 3.9+
- pip or conda
- (Optional) Sentinel Hub account for satellite features

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment (Optional)

For Sentinel Hub features, create `.env`:
```env
SENTINEL_CLIENT_ID=your_client_id
SENTINEL_CLIENT_SECRET=your_client_secret
```

---

##  Running the Application

### Option 1: Run Both Services Locally

**Terminal 1 - Start FastAPI Backend:**
```bash
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```
Backend available at: `http://127.0.0.1:8000`

**Terminal 2 - Start Streamlit Frontend:**
```bash
streamlit run app.py
```
Frontend available at: `http://localhost:8501`

### Option 2: Train Model

```bash
python train_tabular.py
```
This will:
- Load `data/train.xlsx` and `data/validation.xlsx`
- Train RandomForest model on 18 features
- Evaluate on validation set
- Save model to `model/price_model.pkl`
- Display performance metrics

---


### /predict - Price Prediction
```http
GET /predict?bedrooms=4&bathrooms=2.5&sqft_living=1810&sqft_lot=9240&...
```

**Parameters (all required):**
- bedrooms (float)
- bathrooms (float)  
- sqft_living (int)
- sqft_lot (int)
- floors (float)
- waterfront (0 or 1)
- view (0-4)
- condition (1-5)
- grade (1-13)
- sqft_above (int)
- sqft_basement (int)
- yr_built (int)
- yr_renovated (int)
- zipcode (int)
- lat (float)
- long (float)
- sqft_living15 (int)
- sqft_lot15 (int)

**Response:**
```json
{
  "predicted_price": 475000.50,
  "status": "success",
  "features_used": 18
}
```

### /satellite - Satellite Image
```http
GET /satellite?lat=47.5&lon=-122.3
```

### /ndvi - Greenery Index
```http
GET /ndvi?lat=47.5&lon=-122.3
```

---

##  Making Predictions

### Via Python
```python
import requests

api_url = "http://127.0.0.1:8000/predict"
params = {
    "bedrooms": 4,
    "bathrooms": 2.5,
    "sqft_living": 1810,
    "sqft_lot": 9240,
    "floors": 2,
    "waterfront": 0,
    "view": 0,
    "condition": 3,
    "grade": 7,
    "sqft_above": 1810,
    "sqft_basement": 0,
    "yr_built": 1961,
    "yr_renovated": 0,
    "zipcode": 98055,
    "lat": 47.4362,
    "long": -122.187,
    "sqft_living15": 1660,
    "sqft_lot15": 9240
}

response = requests.get(api_url, params=params)
print(f"Predicted Price: ${response.json()['predicted_price']:,.0f}")
```

### Via Streamlit UI
1. Open http://localhost:8501
2. Select location on map or enter coordinates
3. Adjust property parameters
4. Get instant price prediction

---

## 📊 Data & Training Details

### Dataset
- **Total Samples**: 16,209 properties
- **Split**: 80% training (12,967), 20% validation (3,242)
- **Test Set**: 5,404 hold-out samples
- **Features**: 18 property attributes
- **Target**: Price (continuous variable)

### Model Architecture
- **Algorithm**: Random Forest Regressor
- **Estimators**: 200 trees
- **Max Depth**: 20
- **Min Samples Leaf**: 2
- **Max Features**: sqrt
- **Random State**: 42
- **Jobs**: -1 (parallel processing)

### Validation Metrics
- **R² Score**: 0.8577 (excellent generalization)
- **MAE**: $73,640 (average prediction error)
- **RMSE**: $133,616 (penalizes larger errors)
- **MAPE**: 13.66% (mean absolute percentage error)
- **Overfitting Gap**: 9.87% (excellent - less than 10%)

---

## ⚙️ Configuration

### Environment Variables
```env
# Sentinel Hub (optional)
SENTINEL_CLIENT_ID=your_id
SENTINEL_CLIENT_SECRET=your_secret
```

### Python Version
- Minimum: 3.9
- Tested: 3.11

---

## 📝 Files Reference

| File | Purpose | Size |
|------|---------|------|
| `main.py` | FastAPI REST API server | 11 KB |
| `app.py` | Streamlit web interface | 32 KB |
| `train_tabular.py` | Model training pipeline | 5 KB |
| `price_predictor_service.py` | Business logic layer | 6 KB |
| `feature_extractor.py` | Satellite/location feature extraction | 7 KB |
| `model/price_model.pkl` | Production ML model (BINARY) | 66 MB |
| `data/train.xlsx` | Training dataset (12,967 rows) | 1.3 MB |
| `data/validation.xlsx` | Validation dataset (3,242 rows) | 332 KB |
| `24116063_final.csv` | Test set predictions (5,404 rows) | 159 KB |

---

## 🎓 Model Development Notes

The model was developed using:
- **Scikit-learn** for ML algorithms
- **Pandas** for data processing
- **NumPy** for numerical operations
- **Sentinel Hub** for satellite data
- **FastAPI** for REST API
- **Streamlit** for web UI

---

##  Model Retraining

To retrain the model with new data:

1. Update data files in `data/` folder
2. Run the training script:
```bash
python train_tabular.py
```
3. New model will be saved to `model/price_model.pkl`
4. Restart FastAPI backend to use new model

---

**Last Updated**: January 2025  
**Model Status**: Production Ready  
**Accuracy**: 85.77% R² 
**Features**: 18 | **Training Samples**: 12,967 | **Validation Samples**: 3,242


