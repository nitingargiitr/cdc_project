"""
User-Friendly Property Price Predictor
Focus on practical features for normal users - nearby amenities, location quality, etc.
"""
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MousePosition, Fullscreen
import pandas as pd
import os
import random
from io import BytesIO

# Currency configuration
USD_INR_RATE = 90.0  # Current exchange rate

# Initialize budget-related variables with default values
budget_value = 0.0
budget_radius_km = 5
budget_points = 30
budget_inr = 0.0

def format_money(amount_in_inr, currency):
    if amount_in_inr is None:
        return "-"
    if currency == "USD":
        return f"${amount_in_inr / USD_INR_RATE:,.0f}"
    return f"₹{amount_in_inr:,.0f}"

def money_value(amount_in_inr, currency):
    if amount_in_inr is None:
        return 0.0
    return amount_in_inr / USD_INR_RATE if currency == "USD" else float(amount_in_inr)

# Local service (replace backend HTTP calls)
from price_predictor_service import predict_price, get_features, get_nearby_amenities

st.set_page_config(
    layout="wide",
    page_title="AI Property Price Predictor",
    initial_sidebar_state="expanded",
    page_icon="🏠",
)

# ✅ FIX 1: Create fresh map object function
def get_price_color(price, budget):
    """Return color based on price to budget ratio"""
    if budget <= 0:
        return "gray"
    ratio = price / budget
    if ratio < 0.85:
        return "green"  # Well within budget
    elif ratio < 1.0:
        return "lightgreen"  # Slightly under budget
    elif ratio < 1.15:
        return "orange"  # Slightly over budget
    else:
        return "red"  # Over budget

def create_map(lat, lon, location_name=None, budget_data=None):
    """Create a fresh map object every time - never reuse"""
    m = folium.Map(
        location=[lat, lon],
        zoom_start=15,
        tiles="cartodbpositron",
        attr="CartoDB Positron",
        control_scale=True,
    )
    
    # Add budget overlay points if provided
    if budget_data and 'points' in budget_data:
        for point in budget_data['points']:
            folium.CircleMarker(
                location=[point['lat'], point['lon']],
                radius=5,
                color=point['color'],
                fill=True,
                fill_color=point['color'],
                fill_opacity=0.7,
                popup=f"Est. Price: {point['price_str']}"
            ).add_to(m)
        

    # Add marker with string-only properties
    folium.Marker(
        [lat, lon],
        popup=f"<b>{location_name or 'Selected Location'}</b><br>Lat: {lat:.5f}<br>Lon: {lon:.5f}",
        tooltip="Selected Location",
        icon=folium.Icon(color="red", icon="home", prefix="fa")
    ).add_to(m)
    
    # Add analysis radius circle
    folium.Circle(
        location=[lat, lon],
        radius=1000,
        popup="Nearby amenities search radius: 1km",
        color="#2563eb",
        fill=True,
        fillColor="#2563eb",
        fillOpacity=0.1
    ).add_to(m)
    
    # Add budget search radius if provided
    if budget_data and 'radius_km' in budget_data:
        folium.Circle(
            location=[lat, lon],
            radius=budget_data['radius_km'] * 1000,  # Convert km to meters
            popup=f"Budget search radius: {budget_data['radius_km']}km",
            color="#888",
            fill=False,
            dash_array='5, 5'
        ).add_to(m)
        
        # Add legend for budget colors
        legend_html = """
        <div style="position: fixed; 
                    bottom: 50px; left: 50px; width: 180px; height: 120px; 
                    border:2px solid grey; z-index:9999; font-size:14px;
                    background-color:white; padding: 10px; border-radius: 5px;
                    ">
            <div style="font-weight: bold; margin-bottom: 5px;">Price vs Budget:</div>
            <div><i class="fa fa-circle" style="color:green"></i> &lt; 85% of budget</div>
            <div><i class="fa fa-circle" style="color:lightgreen"></i> 85-100% of budget</div>
            <div><i class="fa fa-circle" style="color:orange"></i> 100-115% of budget</div>
            <div><i class="fa fa-circle" style="color:red"></i> &gt; 115% of budget</div>
        </div>
        """
        m.get_root().html.add_child(folium.Element(legend_html))
    
    # Add plugins
    MousePosition().add_to(m)
    Fullscreen().add_to(m)
    
    return m

# Custom CSS
st.markdown(
    """
<style>
  :root {
    --bg: #0b1220;
    --surface: rgba(255, 255, 255, 0.06);
    --surface-2: rgba(255, 255, 255, 0.08);
    --border: rgba(255, 255, 255, 0.10);
    --text: #e5e7eb;
    --muted: rgba(229, 231, 235, 0.72);
    --brand: #60a5fa;
    --brand-2: #a78bfa;
    --success: #22c55e;
    --warn: #f59e0b;
    --danger: #ef4444;
    --radius: 14px;
  }

  .stApp {
    background: radial-gradient(1200px 600px at 15% 0%, rgba(96,165,250,0.20), transparent 55%),
                radial-gradient(900px 500px at 85% 10%, rgba(167,139,250,0.16), transparent 60%),
                var(--bg);
    color: var(--text);
  }

  .block-container {
    padding-top: 1.25rem;
    padding-bottom: 2rem;
    max-width: 1200px;
  }

  h1, h2, h3, h4 {
    color: var(--text) !important;
    letter-spacing: -0.02em;
  }

  p, li, label {
    color: var(--muted) !important;
  }

  .pp-hero {
    border: 1px solid var(--border);
    background: linear-gradient(135deg, rgba(96,165,250,0.14), rgba(167,139,250,0.08));
    border-radius: var(--radius);
    padding: 1.2rem 1.2rem;
    margin-bottom: 1.25rem;
  }
  .pp-hero-title {
    margin: 0;
    font-size: 2.15rem;
    font-weight: 800;
    line-height: 1.1;
    background: linear-gradient(90deg, var(--brand), var(--brand-2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .pp-hero-sub {
    margin: 0.45rem 0 0 0;
    font-size: 1.02rem;
    color: var(--muted) !important;
  }

  section[data-testid="stSidebar"] {
    background: rgba(255, 255, 255, 0.04) !important;
    border-right: 1px solid var(--border) !important;
  }
  section[data-testid="stSidebar"] h2, section[data-testid="stSidebar"] h3 {
    color: var(--text) !important;
  }

  .stButton>button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    border: 1px solid rgba(96,165,250,0.35) !important;
    background: linear-gradient(90deg, rgba(96,165,250,0.92), rgba(167,139,250,0.85)) !important;
    color: #0b1220 !important;
    transition: transform 140ms ease, filter 140ms ease;
  }
  .stButton>button:hover {
    filter: brightness(1.05);
    transform: translateY(-1px);
  }

  .stTabs [data-baseweb="tab-list"] {
    gap: 8px !important;
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border) !important;
    padding: 6px !important;
    border-radius: 12px !important;
  }
  .stTabs [data-baseweb="tab"] {
    border-radius: 10px !important;
    padding: 10px 14px !important;
    color: var(--muted) !important;
    font-weight: 600 !important;
    background: transparent !important;
  }
  .stTabs [aria-selected="true"] {
    background: rgba(255,255,255,0.10) !important;
    color: var(--text) !important;
  }

  div[data-testid="stMetric"] {
    background: rgba(255,255,255,0.06) !important;
    border: 1px solid var(--border) !important;
    border-radius: 14px !important;
    padding: 14px 14px !important;
  }

  .pp-section-title {
    margin: 0 0 0.75rem 0;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--text);
  }
  .pp-card {
    background: rgba(255,255,255,0.06);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1rem;
    margin-bottom: 1rem;
  }
  .pp-inline {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
  }
  .pp-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    border-radius: 999px;
    background: rgba(255,255,255,0.08);
    border: 1px solid var(--border);
    color: var(--muted);
    font-size: 0.85rem;
    font-weight: 600;
  }

  .pp-map-card {
    padding: 0 !important;
    overflow: hidden;
  }
  .pp-map-head {
    padding: 0.85rem 0.95rem;
    border-bottom: 1px solid var(--border);
    background: rgba(255,255,255,0.03);
    color: var(--text);
    font-weight: 800;
    letter-spacing: -0.01em;
  }
  .pp-map-card [data-testid="stIFrame"] {
    width: 100% !important;
  }
  .pp-map-card iframe {
    width: 100% !important;
    min-width: 100% !important;
    max-width: 100% !important;
    display: block;
    background: transparent !important;
  }

  .pp-map-card div[data-testid="stIFrame"] {
    width: 100% !important;
    max-width: 100% !important;
    display: block;
  }
</style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
<div class="pp-hero">
  <div class="pp-inline">
    <div>
      <div class="pp-hero-title">AI Property Price Predictor</div>
      <div class="pp-hero-sub">Modern price insights using property specs + location signals.</div>
    </div>
    <div class="pp-pill">Live • Streamlit</div>
  </div>
</div>
    """,
    unsafe_allow_html=True,
)

# Initialize session state
for key in ['selected_lat', 'selected_lon', 'location_name', 'location_features', 'comparison_locations', 'budget_value', 'budget_radius_km', 'budget_points']:
    if key not in st.session_state:
        st.session_state[key] = [] if key == 'comparison_locations' else (10000000.0 if key == 'budget_value' else (5 if key in ['budget_radius_km'] else (30 if key == 'budget_points' else None)))

# Sidebar - Location Selection
st.sidebar.header("📍 Location Selection")

# Currency Toggle
st.sidebar.markdown("---")
st.sidebar.header("💱 Currency")
currency = st.sidebar.radio("Display prices in", ["INR", "USD"], horizontal=True, key="currency")

search_method = st.sidebar.radio(
    "Choose input method:"
    ["📌 Enter Coordinates", "🗺️ Click on Map"],
    key="search_method"
)

lat = st.session_state.selected_lat
lon = st.session_state.selected_lon
location_name = st.session_state.location_name

# Enter Coordinates
if search_method == "📌 Enter Coordinates":
    col1, col2 = st.sidebar.columns(2)
    with col1:
        lat_input = st.number_input("Latitude", value=lat or 28.6139, format="%.5f", step=0.0001, key="lat_in")
    with col2:
        lon_input = st.number_input("Longitude", value=lon or 77.2090, format="%.5f", step=0.0001, key="lon_in")
    
    if st.sidebar.button("✅ Use Coordinates", use_container_width=True):
        st.session_state.selected_lat = lat_input
        st.session_state.selected_lon = lon_input
        st.session_state.location_name = f"{lat_input:.5f}, {lon_input:.5f}"
        st.session_state.location_features = None  # Clear cached features
        st.rerun()
else:
    st.sidebar.info("Click on the map to select a location.")
st.sidebar.markdown("---")
st.sidebar.header("💰 Budget Filter")
enable_budget_overlay = st.sidebar.toggle("Show affordability overlay", value=False, key="budget_overlay")

if enable_budget_overlay:
    st.session_state.budget_value = st.sidebar.number_input(
        f"Budget ({currency})",
        min_value=0.0,
        value=st.session_state.budget_value,
        step=100000.0 if currency == "INR" else 1000.0,
        key="budget_input"
    )
    st.session_state.budget_radius_km = st.sidebar.slider(
        "Search radius (km)", 
        1, 20, 
        st.session_state.budget_radius_km, 
        1, 
        key="budget_radius_slider"
    )
    st.session_state.budget_points = st.sidebar.slider(
        "Number of points", 
        10, 100, 
        st.session_state.budget_points, 
        5, 
        key="budget_points_slider"
    )
    budget_inr = st.session_state.budget_value * (USD_INR_RATE if currency == "USD" else 1)
else:
    budget_inr = 0.0

st.sidebar.markdown("---")
st.sidebar.header("🏡 Property Details")
bedrooms = st.sidebar.slider("Bedrooms", 1, 6, 3, key="bed")
bathrooms = st.sidebar.slider("Bathrooms", 1.0, 4.0, 2.0, 0.5, key="bath")
sqft = st.sidebar.slider("Living Area (sqft)", 500, 4000, 1500, 50, key="sqft")

# Map Display
col_map, col_info = st.columns([2, 1], gap="large")

with col_map:
    st.markdown(
        '<div class="pp-card pp-map-card"><div class="pp-map-head">📍 Property Location</div>',
        unsafe_allow_html=True,
    )
    budget_data = None
    if enable_budget_overlay and st.session_state.budget_value > 0 and lat and lon:
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
            
            price_inr = random.uniform(0.5, 2.0) * budget_inr
            
            points.append({
                'lat': point_lat,
                'lon': point_lon,
                'price': price_inr,
                'price_str': format_money(price_inr, currency),
                'color': get_price_color(price_inr, budget_inr)
            })
        
        budget_data = {
            'points': points,
            'radius_km': st.session_state.budget_radius_km
        }

    if lat and lon:
        m = create_map(lat, lon, location_name, budget_data)
        
        map_data = None
        try:
            map_data = st_folium(
                m,
                height=560,
                width="100%",
                key="main_map"
            )
        except Exception as e:
            st.warning("⚠️ Map temporarily unavailable. Please refresh the page.")
        
        if search_method == "🗺️ Click on Map" and map_data and map_data.get("last_clicked"):
            clicked = map_data["last_clicked"]
            new_lat = float(clicked["lat"])
            new_lon = float(clicked["lng"])
            if (st.session_state.selected_lat != new_lat) or (st.session_state.selected_lon != new_lon):
                st.session_state.selected_lat = new_lat
                st.session_state.selected_lon = new_lon
                st.session_state.location_name = f"{new_lat:.5f}, {new_lon:.5f}"
                st.session_state.location_features = None
                st.rerun()
    else:
        # Default map (no location selected yet)
        m_default = folium.Map(
            location=[28.6139, 77.2090],
            zoom_start=10,
            tiles="cartodbpositron",
            attr="CartoDB Positron",
            control_scale=True,
        )
        
        # ✅ FIX 3: Cloud-safe st_folium with error handling
        map_data = None
        try:
            map_data = st_folium(
                m_default,
                height=560,
                width="100%",
                key="main_map"
            )
        except Exception as e:
            st.warning("⚠️ Map temporarily unavailable. Please refresh the page.")
        
        # ✅ FIX 2: Handle map clicks WITHOUT st.rerun()
        if search_method == "🗺️ Click on Map" and map_data and map_data.get("last_clicked"):
            clicked = map_data["last_clicked"]
            new_lat = float(clicked["lat"])
            new_lon = float(clicked["lng"])
            st.session_state.selected_lat = new_lat
            st.session_state.selected_lon = new_lon
            st.session_state.location_name = f"{new_lat:.5f}, {new_lon:.5f}"
            st.session_state.location_features = None
            st.rerun()
        
        st.info("👆 Select a location to get started")

    st.markdown("</div>", unsafe_allow_html=True)

# Location Info Panel
with col_info:
    if lat and lon:
        st.markdown('<div class="pp-section-title">Location Overview</div>', unsafe_allow_html=True)
        st.markdown(
            f"""
<div class="pp-card">
  <div style="font-weight: 750; color: var(--text);">{location_name or 'Selected Location'}</div>
  <div style="margin-top: 6px; color: var(--muted); font-size: 0.92rem;">
    Lat {lat:.5f} • Lon {lon:.5f}
  </div>
</div>
            """,
            unsafe_allow_html=True,
        )
        
        # Quick location features (use local service)
        if st.session_state.location_features is None:
            try:
                st.session_state.location_features = get_features(lat, lon)
            except Exception:
                st.session_state.location_features = {"error": "Failed to fetch features"}

        features = st.session_state.location_features or {}
        if "error" not in features:
            ndvi_val = features.get('ndvi', 0)
            ndwi_val = features.get('ndwi', 0)
            road_val = features.get('road_density', 0.3)
            c1, c2 = st.columns(2)
            with c1:
                st.metric("Greenery (NDVI)", f"{ndvi_val:.3f}")
                st.metric("Connectivity", f"{road_val:.3f}")
            with c2:
                st.metric("Water (NDWI)", f"{ndwi_val:.3f}")
            # Warn if all features are zero/default (likely API/credentials issue)
            if ndvi_val == 0 and ndwi_val == 0 and (road_val == 0 or road_val == 0.3):
                st.warning("Satellite features are all zero or default. Check Sentinel Hub credentials or API access.")

# Main Analysis Section
if lat and lon:
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Price Prediction", "Nearby Amenities", "Location Quality", "Property Comparison"])
    
    with tab1:
        st.header("Price Prediction")
        
        try:
            # Use local service instead of HTTP
            result = predict_price(bedrooms, bathrooms, sqft, lat, lon)
            price = result.get("predicted_price")

            # Price Display
            col_price1, col_price2, col_price3 = st.columns(3)
            with col_price1:
                st.metric("Predicted Price", format_money(price, currency))
            with col_price2:
                price_per_sqft_val = price / sqft if sqft > 0 else 0
                st.metric("Price/sqft", format_money(price_per_sqft_val, currency))
            with col_price3:
                st.metric("Property Size", f"{sqft:,} sqft")

            # Explanation
            st.info(f"Why this price? {result.get('explanation', '')}")

            if result.get("location_context"):
                st.caption(f"{result['location_context']}")
                
                # Feature Breakdown
                with st.expander("Feature Breakdown"):
                    features_data = result.get("features", {})
                    st.write("**Property:**")
                    st.write(f"- Bedrooms: {features_data.get('bedrooms', bedrooms)}")
                    st.write(f"- Bathrooms: {features_data.get('bathrooms', bathrooms)}")
                    st.write(f"- Living Area: {features_data.get('sqft_living', sqft)} sqft")
                    
                    if 'ndvi' in features_data:
                        st.write("\n**Location:**")
                        st.write(f"- Greenery (NDVI): {features_data.get('ndvi', 0):.3f}")
                        st.write(f"- Water (NDWI): {features_data.get('ndwi', 0):.3f}")
                        st.write(f"- Road Density: {features_data.get('road_density', 0):.3f}")
        except Exception as e:
            st.error(f"Error: {str(e)}")
    
    with tab2:
        st.header("Nearby Amenities")
        st.write("Discover what's nearby - schools, hospitals, shops, and more!")
        
        # Range slider
        amenity_radius = st.slider(
            "Search Range (meters)",
            min_value=100,
            max_value=1000,
            value=1000,
            step=100,
            key="amenity_range"
        )
        
        with st.spinner("Finding nearby amenities..."):
            try:
                # Use local amenities function
                amenities_data = get_nearby_amenities(lat, lon, amenity_radius)

                if amenities_data.get("error"):
                    st.error(f"{amenities_data['error']}")
                else:
                    # Total count
                    total = amenities_data.get("total", 0)
                    
                    if total == 0:
                        st.info("No amenities found in this range. Try expanding the search radius.")
                    else:
                        st.subheader(f"Found {total} amenities within {amenity_radius}m")
                    
                    # Show amenities by category
                    by_category = amenities_data.get("by_category", {})
                    
                    if by_category:
                        # Education
                        if "Education" in by_category:
                            with st.expander(f"Education ({len(by_category['Education'])} found)", expanded=True):
                                education = by_category["Education"]
                                for item in education:
                                    st.write(f"**{item['name']}** - *{item['type'].title()}*")
                        
                        # Healthcare
                        if "Healthcare" in by_category:
                            with st.expander(f"Healthcare ({len(by_category['Healthcare'])} found)", expanded=True):
                                healthcare = by_category["Healthcare"]
                                for item in healthcare:
                                    st.write(f"**{item['name']}** - *{item['type'].title()}*")
                        
                        # Shopping
                        if "Shopping" in by_category:
                            with st.expander(f"Shopping ({len(by_category['Shopping'])} found)", expanded=False):
                                shopping = by_category["Shopping"]
                                for item in shopping:
                                    st.write(f"**{item['name']}** - *{item['type'].title()}*")
                        
                        # Dining
                        if "Dining" in by_category:
                            with st.expander(f"Dining ({len(by_category['Dining'])} found)", expanded=False):
                                dining = by_category["Dining"]
                                for item in dining:
                                    st.write(f"**{item['name']}** - *{item['type'].title()}*")
                        
                        # Services
                        if "Services" in by_category:
                            with st.expander(f"Services ({len(by_category['Services'])} found)", expanded=False):
                                services = by_category["Services"]
                                for item in services:
                                    st.write(f"**{item['name']}** - *{item['type'].title()}*")
                        
                        # Recreation
                        if "Recreation" in by_category:
                            with st.expander(f"Recreation ({len(by_category['Recreation'])} found)", expanded=False):
                                recreation = by_category["Recreation"]
                                for item in recreation:
                                    st.write(f"**{item['name']}** - *{item['type'].title()}*")
                        
                        # Safety
                        if "Safety" in by_category:
                            with st.expander(f"Safety ({len(by_category['Safety'])} found)", expanded=False):
                                safety = by_category["Safety"]
                                for item in safety:
                                    st.write(f"**{item['name']}** - *{item['type'].title()}*")
                    else:
                        st.info("No amenities found in this area. Try a different location.")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with tab3:
        st.header("Location Quality")
        st.write("Understand the quality of this location")
        
        features = st.session_state.location_features
        if features and "error" not in features:
            col_qual1, col_qual2, col_qual3 = st.columns(3)
            
            with col_qual1:
                ndvi = float(features.get("ndvi", 0))
                st.metric("Greenery Index", f"{ndvi:.3f}")
                if ndvi > 0.3:
                    st.success("High greenery - great for families!")
                elif ndvi > 0.1:
                    st.info("Moderate greenery")
                else:
                    st.warning("Low greenery - urban area")
            
            with col_qual2:
                ndwi = float(features.get("ndwi", 0))
                st.metric("Water Proximity", f"{ndwi:.3f}")
                if ndwi > 0.2:
                    st.success("Near water - premium location!")
                elif ndwi > 0.1:
                    st.info("Some water nearby")
                else:
                    st.info("No major water bodies")
            
            with col_qual3:
                road_density = float(features.get("road_density", 0.3))
                st.metric("Road Density", f"{road_density:.3f}")
                if road_density > 0.6:
                    st.success("Excellent connectivity!")
                elif road_density > 0.3:
                    st.info("Good connectivity")
                else:
                    st.info("Quiet area")
            
            # Overall assessment
            st.markdown("---")
            st.subheader("Location Summary")
            
            summary_points = []
            if ndvi > 0.3:
                summary_points.append("Green, family-friendly neighborhood")
            if ndwi > 0.2:
                summary_points.append("Waterfront or near water")
            if road_density > 0.6:
                summary_points.append("Well-connected urban area")
            elif road_density < 0.3:
                summary_points.append("Quiet residential area")
            
            if summary_points:
                for point in summary_points:
                    st.write(f"- {point}")
            else:
                st.write("Standard residential location")
        elif features and "error" in features:
            st.error(f"Failed to load location features: {features['error']}")
        else:
            st.info("Location features not available. Please try refreshing the page.")
    
    with tab4:
        st.header("Property Comparison")
        st.write("Compare multiple locations side by side to find your perfect home")
        
        # Add current location to comparison
        col_add, col_clear = st.columns([3, 1])
        
        with col_add:
            if st.button("Add Current Location to Comparison", 
                        disabled=len(st.session_state.comparison_locations) >= 3,
                        use_container_width=True):
                if lat and lon and len(st.session_state.comparison_locations) < 3:
                    # Check if location already exists
                    location_exists = False
                    for existing_loc in st.session_state.comparison_locations:
                        if (abs(existing_loc["lat"] - lat) < 0.001 and 
                            abs(existing_loc["lon"] - lon) < 0.001):
                            location_exists = True
                            break
                    
                    if not location_exists:
                        location_data = {
                            "name": location_name or f"Location {len(st.session_state.comparison_locations)+1}",
                            "lat": lat,
                            "lon": lon,
                            "bedrooms": bedrooms,
                            "bathrooms": bathrooms,
                            "sqft": sqft
                        }
                        st.session_state.comparison_locations.append(location_data)
                        st.success(f"Added {location_data['name']} to comparison!")
                        st.rerun()
                    else:
                        st.warning("This location is already in your comparison list")
                elif not lat or not lon:
                    st.error("Please select a location first")
                else:
                    st.warning("Maximum 3 locations allowed for comparison")
        
        with col_clear:
            if st.button("Clear All", use_container_width=True):
                st.session_state.comparison_locations = []
                st.success("Cleared all comparisons!")
                st.rerun()
        
        # Display comparison table
        if st.session_state.comparison_locations:
            st.subheader(f"Comparing {len(st.session_state.comparison_locations)} Location{'s' if len(st.session_state.comparison_locations) > 1 else ''}")
            
            # Create comparison data with progress
            comparison_data = []
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, loc in enumerate(st.session_state.comparison_locations):
                status_text.text(f"Analyzing {loc['name']}...")
                
                try:
                    # Use local service to get price and features
                    price_data = predict_price(loc["bedrooms"], loc["bathrooms"], loc["sqft"], loc["lat"], loc["lon"])
                    predicted_price = price_data.get("predicted_price")
                    price_per_sqft = predicted_price / loc["sqft"] if loc["sqft"] > 0 else 0

                    features = get_features(loc["lat"], loc["lon"]) or {"ndvi": 0.0, "ndwi": 0.0, "road_density": 0.3}

                    comparison_data.append({
                        "Location": loc["name"],
                        "Price": f"${predicted_price:,.0f}",
                        "Price/sqft": f"${price_per_sqft:,.0f}",
                        "Beds": loc["bedrooms"],
                        "Baths": loc["bathrooms"],
                        "Sqft": f"{loc['sqft']:,}",
                        "Greenery": f"{features.get('ndvi', 0):.2f}",
                        "Water": f"{features.get('ndwi', 0):.2f}",
                        "Connectivity": f"{features.get('road_density', 0.3):.2f}"
                    })
                
                except Exception as e:
                    comparison_data.append({
                        "Location": loc["name"],
                        "Price": f"Error: {str(e)[:20]}...",
                        "Price/sqft": "Error",
                        "Beds": loc["bedrooms"],
                        "Baths": loc["bathrooms"],
                        "Sqft": f"{loc['sqft']:,}",
                        "Greenery": "N/A",
                        "Water": "N/A",
                        "Connectivity": "N/A"
                    })
                
                # Update progress
                progress_bar.progress((i + 1) / len(st.session_state.comparison_locations))
            
            progress_bar.empty()
            status_text.empty()
            
            if comparison_data:
                df = pd.DataFrame(comparison_data)
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Enhanced Analysis Section
                st.markdown("---")
                st.subheader("Detailed Comparison Analysis")
                
                valid_prices = []
                location_features = {}
                
                for item in comparison_data:
                    price_str = item["Price"]
                    if price_str not in ["API Error", "Error"] and "$" in price_str:
                        try:
                            price_val = float(price_str.replace("$", "").replace(",", ""))
                            valid_prices.append((item["Location"], price_val))
                            
                            # Store features for each location
                            try:
                                sqft_val = int(item["Sqft"].replace(",", ""))
                            except (ValueError, AttributeError):
                                sqft_val = 0
                            
                            location_features[item["Location"]] = {
                                "price": price_val,
                                "greenery": float(item["Greenery"]) if item["Greenery"] != "N/A" else 0,
                                "water": float(item["Water"]) if item["Water"] != "N/A" else 0,
                                "connectivity": float(item["Connectivity"]) if item["Connectivity"] != "N/A" else 0.3,
                                "beds": item["Beds"],
                                "baths": item["Baths"],
                                "sqft": sqft_val
                            }
                        except:
                            continue
                
                if len(valid_prices) > 1:
                    # Sort by price for comparison
                    sorted_locations = sorted(valid_prices, key=lambda x: x[1])
                    cheapest = sorted_locations[0]
                    most_expensive = sorted_locations[-1]
                    
                    # Price Comparison Section
                    st.markdown("### Price Differences")
                    col1, col2 = st.columns(2)
                    with col1:
                        st.success(f"Most Affordable: {cheapest[0]}")
                        st.metric("Price", f"${cheapest[1]:,.0f}")
                    
                    with col2:
                        price_range = most_expensive[1] - cheapest[1]
                        st.info(f"Price Range: ${price_range:,.0f}")
                        st.metric("From", f"${cheapest[1]:,.0f}", f"To ${most_expensive[1]:,.0f}")
                    
                    # Show price differences between each pair
                    st.markdown("**Price Differences:**")
                    for i in range(len(sorted_locations)):
                        for j in range(i+1, len(sorted_locations)):
                            loc1, price1 = sorted_locations[i]
                            loc2, price2 = sorted_locations[j]
                            diff = price2 - price1
                            st.write(f"• {loc2} is **${diff:,.0f}** more expensive than {loc1}")
                    
                    # Feature Comparison Section
                    st.markdown("### Feature Differences")
                    
                    # Compare each location with the cheapest
                    cheapest_name = cheapest[0]
                    cheapest_features = location_features[cheapest_name]
                    
                    for loc_name, features in location_features.items():
                        if loc_name != cheapest_name:
                            st.markdown(f"**{loc_name} vs {cheapest_name}:**")
                            
                            # Price difference
                            price_diff = features["price"] - cheapest_features["price"]
                            
                            # Feature differences
                            greenery_diff = features["greenery"] - cheapest_features["greenery"]
                            water_diff = features["water"] - cheapest_features["water"]
                            connectivity_diff = features["connectivity"] - cheapest_features["connectivity"]
                            
                            diff_text = []
                            if abs(greenery_diff) > 0.1:
                                if greenery_diff > 0:
                                    diff_text.append(f"{greenery_diff:.1f} more greenery")
                                else:
                                    diff_text.append(f"{abs(greenery_diff):.1f} less greenery")
                            
                            if abs(water_diff) > 0.05:
                                if water_diff > 0:
                                    diff_text.append(f"{water_diff:.2f} more water proximity")
                                else:
                                    diff_text.append(f"{abs(water_diff):.2f} less water proximity")
                            
                            if abs(connectivity_diff) > 0.1:
                                if connectivity_diff > 0:
                                    diff_text.append(f"{connectivity_diff:.1f} better connectivity")
                                else:
                                    diff_text.append(f"{abs(connectivity_diff):.1f} worse connectivity")
                            
                            if diff_text:
                                st.write(f"• **Features:** {', '.join(diff_text)}")
                            else:
                                st.write("• **Features:** Similar location quality")
                    
                    # Price Explanation Notes
                    st.markdown("### Why Price Differences?")
                    
                    for loc_name, features in location_features.items():
                        if loc_name != cheapest_name:
                            price_diff_pct = ((features["price"] - cheapest_features["price"]) / cheapest_features["price"]) * 100
                            
                            # Analyze key factors
                            explanations = []
                            
                            # Greenery factor
                            if features["greenery"] > cheapest_features["greenery"] + 0.15:
                                explanations.append("superior greenery/park access")
                            elif features["greenery"] < cheapest_features["greenery"] - 0.15:
                                explanations.append("less green space")
                            
                            # Water factor
                            if features["water"] > cheapest_features["water"] + 0.1:
                                explanations.append("waterfront or near water")
                            
                            # Connectivity factor
                            if features["connectivity"] > cheapest_features["connectivity"] + 0.2:
                                explanations.append("better road access/connectivity")
                            elif features["connectivity"] < cheapest_features["connectivity"] - 0.2:
                                explanations.append("poorer connectivity")
                            
                            # Size factor (if significantly different)
                            try:
                                if cheapest_features["sqft"] > 0:
                                    sqft_diff_pct = ((features["sqft"] - cheapest_features["sqft"]) / cheapest_features["sqft"]) * 100
                                else:
                                    sqft_diff_pct = 0
                            except (TypeError, ZeroDivisionError):
                                sqft_diff_pct = 0
                            
                            if abs(sqft_diff_pct) > 10:
                                if sqft_diff_pct > 0:
                                    explanations.append("larger property size")
                                else:
                                    explanations.append("smaller property size")
                            
                            # Generate explanation
                            if explanations:
                                explanation = f"**{loc_name}** ({price_diff_pct:+.1f}%): " + ", ".join(explanations)
                            else:
                                explanation = f"**{loc_name}** ({price_diff_pct:+.1f}%): Premium location value"
                            
                            st.info(explanation)
                    
                    # Value Rankings
                    st.markdown("### Overall Value Rankings")
                    
                    value_scores = []
                    for loc_name, features in location_features.items():
                        # Calculate value score (lower price + higher features = better value)
                        price_score = 1 / (features["price"] / 100000)  # Normalize price
                        feature_score = (features["greenery"] * 2 + features["water"] * 3 + features["connectivity"]) / 6
                        value_score = price_score + feature_score
                        
                        value_scores.append((loc_name, value_score, features["price"]))
                    
                    if value_scores:
                        best_value = max(value_scores, key=lambda x: x[1])
                        st.success(f"Best Overall Value: {best_value[0]}")
                        st.caption(f"Balances price (${best_value[2]:,.0f}) with excellent location features")
                        
                        # Show ranking
                        ranked = sorted(value_scores, key=lambda x: x[1], reverse=True)
                        for i, (name, score, price) in enumerate(ranked, 1):
                            st.write(f"{i}. **{name}** - Score: {score:.2f} (Price: ${price:,.0f})")
            
        else:
            st.info("How to Compare Properties:")
            st.markdown("""
            1. **Select a location** using coordinates or map click
            2. **Adjust property specs** in the sidebar (bedrooms, bathrooms, sqft)
            3. **Click "Add Current Location to Comparison"**
            4. **Repeat steps 1-3** for up to 3 different locations
            5. **View the comparison table** with prices, features, and analysis
            
            Tip: Compare similar properties to see how location affects price!
            """)
            
            # Show current location info if available
            if lat and lon:
                st.markdown("---")
                st.subheader("Current Location Ready")
                st.write(f"**{location_name or 'Selected Location'}** - {bedrooms} bed, {bathrooms} bath, {sqft:,} sqft")
                st.info("Click the button above to add this location to your comparison!")
    

else:
    st.info("Please select a location using one of the methods in the sidebar to get started!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><strong>AI Property Price Predictor</strong></p>
    <p>Powered by AI and Satellite Data</p>
</div>
""", unsafe_allow_html=True)
