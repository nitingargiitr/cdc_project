# 🏠 AI Property Price Predictor

An AI-powered web application that predicts property prices based on property features and location using machine learning and satellite imagery.

## Features

- 🗺️ Interactive map interface for selecting property locations
- 🤖 Machine learning model for price prediction
- 🛰️ Satellite imagery integration via Sentinel Hub
- 📊 Property feature inputs (bedrooms, bathrooms, square footage)
- 💰 Real-time price predictions

## Project Structure

```
property-price-map/
├── app/
│   └── app.py              # Streamlit frontend application
├── backend/
│   ├── main.py             # FastAPI backend server
│   ├── sentinel_config.py  # Sentinel Hub configuration
│   └── sentinel_fetcher.py # Satellite image fetching logic
├── model/
│   ├── train_tabular.py    # Model training script
│   └── price_model.pkl     # Trained model (generated)
├── data/
│   └── train(1).xlsx       # Training data
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variables template
└── README.md              # This file
```

## Setup Instructions

### 1. Prerequisites

- Python 3.8 or higher
- Sentinel Hub account (for satellite imagery - optional)

### 2. Install Dependencies

```bash
# Create and activate virtual environment (if not already done)
python -m venv venv
venv\Scripts\activate  # On Windows
# source venv/bin/activate  # On Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment Variables

```bash
# Copy the example environment file
copy .env.example .env  # On Windows
# cp .env.example .env  # On Linux/Mac

# Edit .env and add your Sentinel Hub credentials
# Get credentials from: https://www.sentinel-hub.com/
```

**Note:** If you don't have Sentinel Hub credentials, the satellite image feature won't work, but the price prediction will still function.

### 4. Train the Model

```bash
python model/train_tabular.py
```

This will generate `model/price_model.pkl` from the training data.

### 5. Run the Application

#### Start the Backend Server

```bash
uvicorn backend.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`

#### Start the Frontend (in a new terminal)

```bash
streamlit run app/app.py
```

The web interface will open in your browser at `http://localhost:8501`

## Usage

1. Open the Streamlit app in your browser
2. Use the sidebar to adjust property features:
   - Number of bedrooms
   - Number of bathrooms
   - Living area (square feet)
3. Click anywhere on the map to select a location
4. View the predicted property price

## API Endpoints

### `GET /predict`
Predict property price based on features and location.

**Parameters:**
- `bedrooms` (int): Number of bedrooms
- `bathrooms` (float): Number of bathrooms
- `sqft_living` (int): Living area in square feet
- `lat` (float, optional): Latitude
- `lon` (float, optional): Longitude

**Response:**
```json
{
  "predicted_price": 450000.0
}
```

### `GET /satellite`
Fetch satellite image for given coordinates.

**Parameters:**
- `lat` (float): Latitude
- `lon` (float): Longitude

**Response:** PNG image

## Current Limitations

- The model currently uses only basic features (bedrooms, bathrooms, sqft_living)
- Location data (lat/lon) is received but not yet integrated into the prediction model
- Satellite imagery features are not yet extracted and used for price prediction

## Future Enhancements

- [ ] Extract features from satellite images (green space, urban density, etc.)
- [ ] Integrate location-based features into the prediction model
- [ ] Add more property features (year built, lot size, etc.)
- [ ] Improve model accuracy with additional data
- [ ] Add historical price trends
- [ ] Display satellite images in the frontend

## Troubleshooting

### Backend Connection Error
If you see "Cannot connect to backend" error:
- Make sure the FastAPI server is running (`uvicorn backend.main:app --reload`)
- Check that the server is running on `http://127.0.0.1:8000`

### Model Not Found Error
- Run `python model/train_tabular.py` to generate the model file

### Sentinel Hub Errors
- Verify your credentials in the `.env` file
- Check your Sentinel Hub account quota
- Satellite features are optional - the app works without them

## License

This project is for educational purposes.


