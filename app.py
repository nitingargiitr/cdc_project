import streamlit as st
import folium
from streamlit_folium import folium_static
import pandas as pd
import numpy as np
import json
import os
from datetime import datetime
from price_predictor_service import predict_price, get_nearby_amenities
from fpdf import FPDF
import base64

# Initialize session state
if 'selected_lat' not in st.session_state:
    st.session_state.selected_lat = None
if 'selected_lon' not in st.session_state:
    st.session_state.selected_lon = None
if 'location_name' not in st.session_state:
    st.session_state.location_name = "Click on the map"
if 'location_features' not in st.session_state:
    st.session_state.location_features = None
if 'comparison_locations' not in st.session_state:
    st.session_state.comparison_locations = []
if 'budget_points_data' not in st.session_state:
    st.session_state.budget_points_data = None
if 'last_budget_params' not in st.session_state:
    st.session_state.last_budget_params = None
if 'budget_value' not in st.session_state:
    st.session_state.budget_value = 10000000.0
if 'budget_radius_km' not in st.session_state:
    st.session_state.budget_radius_km = 5
if 'budget_points' not in st.session_state:
    st.session_state.budget_points = 30
if 'last_clicked' not in st.session_state:
    st.session_state.last_clicked = None

# Constants
USD_INR_RATE = 90.0  # 1 USD = 90 INR

# Custom CSS for better UI
st.markdown("""
    <style>
    .main {
        max-width: 1200px;
        padding: 2rem;
    }
    .stButton>button {
        background-color: #2563eb;
        color: white;
        border-radius: 0.5rem;
        padding: 0.5rem 1rem;
        border: none;
    }
    .stButton>button:hover {
        background-color: #1d4ed8;
    }
    .stTextInput>div>div>input {
        border-radius: 0.5rem;
        padding: 0.5rem;
    }
    .stNumberInput>div>div>input {
        border-radius: 0.5rem;
        padding: 0.5rem;
    }
    .stSlider>div>div>div>div>div>div {
        background-color: #2563eb !important;
    }
    .stRadio>div {
        flex-direction: row;
        gap: 1rem;
    }
    .stRadio>div>label {
        margin: 0;
    }
    .stTabs>div>div>div>div>div {
        gap: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# Helper functions
def format_money(amount, currency="INR"):
    """Format money based on currency"""
    if currency == "USD":
        return f"${amount:,.0f}"
    else:  # INR
        return f"INR {amount:,.0f}"

def money_value(amount, currency="INR"):
    """Convert amount to float based on currency"""
    if currency == "USD":
        return amount * USD_INR_RATE
    return amount

def get_price_color(price, budget):
    """Get color based on price relative to budget"""
    if budget == 0:
        return "blue"
    ratio = price / budget
    if ratio < 0.7:
        return "green"
    elif ratio < 1.0:
        return "orange"
    elif ratio < 1.3:
        return "red"
    else:
        return "darkred"

def create_map(lat, lon, zoom=12, budget_data=None):
    """Create a folium map centered at lat, lon"""
    m = folium.Map(location=[lat, lon], zoom_start=zoom, 
                  tiles="cartodbpositron", 
                  attr='© OpenStreetMap contributors')
    
    # Add main marker
    folium.Marker(
        [lat, lon],
        popup="Selected Location",
        icon=folium.Icon(color="blue", icon="home")
    ).add_to(m)
    
    # Add budget overlay if enabled
    if budget_data and 'points' in budget_data:
        for point in budget_data['points']:
            folium.CircleMarker(
                location=[point['lat'], point['lon']],
                radius=5,
                color=point.get('color', 'blue'),
                fill=True,
                fill_color=point.get('color', 'blue'),
                fill_opacity=0.7,
                popup=f"Price: {point.get('price_str', 'N/A')}"
            ).add_to(m)
    
    return m

def create_pdf(data, filename="property_analysis.pdf"):
    """Create a PDF report"""
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    
    # Title
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Property Analysis Report", ln=True, align='C')
    pdf.ln(10)
    
    # Property Details
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Property Details", ln=True)
    pdf.set_font("Arial", size=12)
    
    details = [
        ("Location", data.get('location', 'N/A')),
        ("Predicted Price", data.get('price', 'N/A')),
        ("Price per SqFt", data.get('price_per_sqft', 'N/A')),
        ("Bedrooms", data.get('bedrooms', 'N/A')),
        ("Bathrooms", data.get('bathrooms', 'N/A')),
        ("Living Area (sqft)", data.get('sqft_living', 'N/A')),
        ("Location Context", data.get('location_context', 'N/A'))
    ]
    
    for label, value in details:
        pdf.cell(100, 10, txt=f"{label}: {value}", ln=True)
    
    # Features
    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, txt="Location Features", ln=True)
    pdf.set_font("Arial", size=12)
    
    features = data.get('features', {})
    for feature, value in features.items():
        if isinstance(value, (int, float)):
            value = f"{value:.2f}"
        pdf.cell(100, 10, txt=f"{feature.replace('_', ' ').title()}: {value}", ln=True)
    
    # Save the PDF
    pdf.output(filename)
    return filename

# Sidebar
with st.sidebar:
    st.header("⚙️ Settings")
    
    # Currency Toggle
    currency = st.radio("Currency", ["INR", "USD"], index=0)
    
    # Budget Overlay
    st.header("💰 Budget Filter")
    enable_budget_overlay = st.checkbox("Enable Budget Overlay", value=False)
    
    if enable_budget_overlay:
        st.session_state.budget_value = st.number_input(
            f"Budget ({currency})",
            min_value=0.0,
            value=st.session_state.budget_value,
            step=100000.0 if currency == "INR" else 1000.0,
            key="budget_input"
        )
        st.session_state.budget_radius_km = st.slider(
            "Search radius (km)", 
            1, 20, 
            st.session_state.budget_radius_km, 
            1
        )
        st.session_state.budget_points = st.slider(
            "Number of points", 
            10, 100, 
            st.session_state.budget_points, 
            5
        )
        budget_inr = st.session_state.budget_value * (USD_INR_RATE if currency == "USD" else 1)
    else:
        budget_inr = 0.0
    
    # Property Details
    st.header("🏠 Property Details")
    bedrooms = st.number_input("Bedrooms", min_value=1, max_value=10, value=3, step=1)
    bathrooms = st.number_input("Bathrooms", min_value=1.0, max_value=10.0, value=2.0, step=0.5)
    sqft = st.number_input("Living Area (sqft)", min_value=300, max_value=10000, value=1500, step=50)

# Main app layout
st.title("🏠 Property Price Predictor")
st.markdown("""
    <div style="background-color: #f0f8ff; padding: 1rem; border-radius: 0.5rem; margin-bottom: 1rem;">
        <p style="margin: 0; color: #1e40af; font-size: 1rem;">
            Click anywhere on the map to select a location and get price predictions.
            Adjust property details in the sidebar to see how they affect the price.
        </p>
    </div>
""", unsafe_allow_html=True)

# Map display
col1, col2 = st.columns([3, 1])

with col1:
    # Create map centered on default location or user selection
    default_lat, default_lon = 28.6139, 77.2090  # Default to New Delhi
    lat = st.session_state.selected_lat or default_lat
    lon = st.session_state.selected_lon or default_lon
    
    # Budget overlay data
    budget_data = None
    if enable_budget_overlay and budget_inr > 0 and lat and lon:
        current_params = (lat, lon, st.session_state.budget_radius_km, 
                         st.session_state.budget_points, budget_inr)
        
        # Only regenerate points if parameters changed
        if (st.session_state.budget_points_data is None or 
            st.session_state.last_budget_params != current_params):
            
            import math
            import random
            
            points = []
            
            for _ in range(st.session_state.budget_points):
                radius_km = st.session_state.budget_radius_km * math.sqrt(random.random())
                angle = random.uniform(0, 2 * math.pi)
                
                lat_delta = (radius_km / 111.32) * math.cos(angle)
                lon_delta = (radius_km / (111.32 * math.cos(math.radians(lat)))) * math.sin(angle)
                
                point_lat = lat + lat_delta
                point_lon = lon + lon_delta
                
                # Generate price based on distance from center
                distance_factor = 1 - (radius_km / st.session_state.budget_radius_km) * 0.5
                price_inr = budget_inr * (0.5 + distance_factor)  # 50% to 150% of budget
                
                points.append({
                    'lat': point_lat,
                    'lon': point_lon,
                    'price': price_inr,
                    'price_str': format_money(price_inr, currency),
                    'color': get_price_color(price_inr, budget_inr)
                })
            
            st.session_state.budget_points_data = {
                'points': points,
                'radius_km': st.session_state.budget_radius_km
            }
            st.session_state.last_budget_params = current_params
        
        budget_data = st.session_state.budget_points_data
    
    # Create and display map
    m = create_map(lat, lon, budget_data=budget_data)
    folium_static(m, width=800, height=600)
    
    # Add JavaScript for map click handling
    st.components.v1.html("""
    <script>
    const doc = window.parent.document;
    const mapElement = doc.querySelector('.folium-map iframe');
    
    function handleMapClick(e) {
        const rect = this.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        
        const map = this.contentWindow.map;
        if (map) {
            const point = map.containerPointToLatLng([y, x]);
            const data = {
                lat: point.lat,
                lng: point.lng
            };
            
            // Update URL
            const url = new URL(window.parent.location);
            url.searchParams.set('lat', data.lat);
            url.searchParams.set('lng', data.lng);
            window.parent.history.pushState({}, '', url);
            
            // Store in session state
            const stJson = JSON.parse(window.parent.sessionStorage.getItem('_stcore:session-state') || '{}');
            stJson.last_clicked = data;
            window.parent.sessionStorage.setItem('_stcore:session-state', JSON.stringify(stJson));
            
            // Trigger Streamlit rerun
            const event = new CustomEvent('streamlit:rerun');
            window.parent.document.dispatchEvent(event);
        }
    }

    if (mapElement) {
        mapElement.addEventListener('load', function() {
            this.contentWindow.document.addEventListener('click', handleMapClick.bind(this));
        });
    }
    </script>
    """, height=0)

with col2:
    st.header("📍 Selected Location")
    st.write(st.session_state.location_name)
    
    if st.session_state.selected_lat is not None and st.session_state.selected_lon is not None:
        try:
            # Get prediction
            prediction = predict_price(
                bedrooms=bedrooms,
                bathrooms=bathrooms,
                sqft_living=sqft,
                lat=st.session_state.selected_lat,
                lon=st.session_state.selected_lon
            )
            
            # Display prediction
            st.metric(
                "Predicted Price", 
                format_money(prediction['predicted_price'], currency),
                delta=None,
                help=prediction.get('explanation', '')
            )
            
            st.metric(
                "Price per SqFt",
                format_money(prediction['predicted_price'] / sqft, currency),
                delta=None
            )
            
            # Location context
            st.markdown("### 🌍 Location Context")
            st.info(prediction.get('location_context', 'No location context available'))
            
            # Features
            st.markdown("### 📊 Location Features")
            features = prediction.get('features', {})
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("🌿 Greenery (NDVI)", f"{features.get('ndvi', 0):.2f}")
                st.metric("💧 Water Index (NDWI)", f"{features.get('ndwi', 0):.2f}")
            
            with col2:
                st.metric("🛣️ Road Density", f"{features.get('road_density', 0.3):.2f}")
            
            # Download buttons
            st.markdown("### 📥 Download")
            
            # Prepare data for export
            export_data = {
                "location": st.session_state.location_name,
                "price": format_money(prediction['predicted_price'], currency),
                "price_per_sqft": format_money(prediction['predicted_price'] / sqft, currency),
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
                "sqft_living": sqft,
                "location_context": prediction.get('location_context', ''),
                "features": features
            }
            
            # CSV Download
            csv = pd.DataFrame([export_data]).to_csv(index=False)
            st.download_button(
                label="📄 Download as CSV",
                data=csv,
                file_name="property_analysis.csv",
                mime="text/csv"
            )
            
            # PDF Download
            pdf_path = create_pdf(export_data)
            with open(pdf_path, "rb") as f:
                pdf_data = f.read()
            
            st.download_button(
                label="📑 Download as PDF",
                data=pdf_data,
                file_name="property_analysis.pdf",
                mime="application/pdf"
            )
            
            # Clean up
            try:
                os.remove(pdf_path)
            except:
                pass
                
        except Exception as e:
            st.error(f"Error getting prediction: {str(e)}")

# Add this to your sidebar section, right after the Property Details section
with st.sidebar:
    # ... (existing sidebar code) ...
    
    # Add this new section for coordinate input
    st.markdown("---")
    st.header("📍 Select Location")
    
    # Coordinate input fields
    col1, col2 = st.columns(2)
    with col1:
        lat_input = st.number_input("Latitude", 
                                  value=st.session_state.selected_lat if st.session_state.selected_lat else 28.6139,
                                  format="%.6f",
                                  step=0.000001)
    with col2:
        lon_input = st.number_input("Longitude",
                                  value=st.session_state.selected_lon if st.session_state.selected_lon else 77.2090,
                                  format="%.6f",
                                  step=0.000001)
    
    # Update location button
    if st.button("Update Location", key="update_location_btn"):
        st.session_state.selected_lat = lat_input
        st.session_state.selected_lon = lon_input
        st.session_state.location_name = f"Location ({lat_input:.4f}, {lon_input:.4f})"
        st.session_state.last_clicked = {'lat': lat_input, 'lng': lon_input}
        st.experimental_rerun()
    
    # Instructions for map click
    st.markdown("""
    <div style="margin-top: 1rem; padding: 1rem; background-color: #f0f8ff; border-radius: 0.5rem;">
        <p style="margin: 0; color: #1e40af; font-size: 0.9rem;">
            <b>Or</b> click anywhere on the map to select a location.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
# Handle URL parameters for sharing
query_params = st.experimental_get_query_params()
if 'lat' in query_params and 'lng' in query_params:
    try:
        lat = float(query_params['lat'][0])
        lon = float(query_params['lng'][0])
        st.session_state.selected_lat = lat
        st.session_state.selected_lon = lon
        st.session_state.location_name = f"Location ({lat:.4f}, {lon:.4f})"
        if 'last_clicked' not in st.session_state:
            st.session_state.last_clicked = {'lat': lat, 'lng': lon}
        st.experimental_rerun()
    except:
        pass

# Handle map click from session state
if 'last_clicked' in st.session_state and st.session_state.last_clicked:
    click_data = st.session_state.last_clicked
    if (st.session_state.selected_lat != click_data['lat'] or 
        st.session_state.selected_lon != click_data['lng']):
        st.session_state.selected_lat = click_data['lat']
        st.session_state.selected_lon = click_data['lng']
        st.session_state.location_name = f"Location ({click_data['lat']:.4f}, {click_data['lng']:.4f})"
        st.experimental_rerun()