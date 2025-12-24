import streamlit as st
import folium
from streamlit_folium import st_folium
import pandas as pd
import os
from fpdf import FPDF
from price_predictor_service import predict_price

# ---------------- SESSION STATE ----------------
st.session_state.setdefault("selected_lat", None)
st.session_state.setdefault("selected_lon", None)
st.session_state.setdefault("location_name", "Not selected")

# ---------------- HELPERS ----------------
def format_money(amount, currency="INR"):
    return f"$ {amount:,.0f}" if currency == "USD" else f"INR {amount:,.0f}"

def create_map(lat, lon):
    m = folium.Map(location=[lat, lon], zoom_start=12, tiles="cartodbpositron")
    folium.Marker([lat, lon], tooltip="Selected location").add_to(m)
    return m

def create_pdf(data, filename="property_analysis.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 10, "Property Analysis Report", ln=True, align="C")
    pdf.ln(5)
    pdf.set_font("Arial", size=12)
    for k, v in data.items():
        pdf.multi_cell(0, 8, f"{k}: {v}")
    pdf.output(filename)
    return filename

# ---------------- SIDEBAR ----------------
with st.sidebar:
    st.header("📍 Location Input")

    search_method = st.radio(
        "Choose input method",
        ["📌 Enter Coordinates", "🗺️ Click on Map"]
    )

    currency = st.radio("Currency", ["INR", "USD"])

    st.header("🏠 Property Details")
    bedrooms = st.number_input("Bedrooms", 1, 10, 3)
    bathrooms = st.number_input("Bathrooms", 1.0, 10.0, 2.0, 0.5)
    sqft = st.number_input("Living Area (sqft)", 300, 10000, 1500)

    # ---- Coordinate input ----
    if search_method == "📌 Enter Coordinates":
        lat_in = st.number_input("Latitude", value=28.6139, format="%.6f")
        lon_in = st.number_input("Longitude", value=77.2090, format="%.6f")

        if st.button("Use Coordinates", use_container_width=True):
            st.session_state.selected_lat = lat_in
            st.session_state.selected_lon = lon_in
            st.session_state.location_name = f"{lat_in:.4f}, {lon_in:.4f}"
            st.rerun()

# ---------------- MAIN ----------------
st.title("🏠 Property Price Predictor")

default_lat, default_lon = 28.6139, 77.2090
lat = st.session_state.selected_lat or default_lat
lon = st.session_state.selected_lon or default_lon

col1, col2 = st.columns([3, 1])

# ---------------- MAP CLICK ----------------
with col1:
    m = create_map(lat, lon)

    if search_method == "🗺️ Click on Map":
        map_data = st_folium(
            m,
            width=800,
            height=600,
            returned_objects=["last_clicked"],
            key="map"
        )

        if map_data and map_data.get("last_clicked"):
            click = map_data["last_clicked"]
            st.session_state.selected_lat = click["lat"]
            st.session_state.selected_lon = click["lng"]
            st.session_state.location_name = f"{click['lat']:.4f}, {click['lng']:.4f}"
            st.rerun()
    else:
        st_folium(m, width=800, height=600)

# ---------------- RESULT PANEL ----------------
with col2:
    st.subheader("📍 Selected Location")
    st.write(st.session_state.location_name)

    if st.session_state.selected_lat and st.session_state.selected_lon:
        pred = predict_price(
            bedrooms=bedrooms,
            bathrooms=bathrooms,
            sqft_living=sqft,
            lat=st.session_state.selected_lat,
            lon=st.session_state.selected_lon,
        )

        price = pred["predicted_price"]

        st.metric("Predicted Price", format_money(price, currency))
        st.metric("Price per SqFt", format_money(price / sqft, currency))

        export = {
            "Location": st.session_state.location_name,
            "Price": format_money(price, currency),
            "Price per SqFt": format_money(price / sqft, currency),
            "Bedrooms": bedrooms,
            "Bathrooms": bathrooms,
            "Area (sqft)": sqft,
        }

        csv = pd.DataFrame([export]).to_csv(index=False)
        st.download_button("📄 Download CSV", csv, "property.csv")

        pdf_path = create_pdf(export)
        with open(pdf_path, "rb") as f:
            st.download_button("📑 Download PDF", f, "property.pdf")
        os.remove(pdf_path)
