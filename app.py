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

# Local service (replace backend HTTP calls)
from price_predictor_service import predict_price, get_features, get_nearby_amenities

# Initialize session state
for key in ['selected_lat', 'selected_lon', 'location_name', 'location_features', 'comparison_locations']:
    if key not in st.session_state:
        st.session_state[key] = [] if key == 'comparison_locations' else None

# Set page config
st.set_page_config(
    layout="wide",
    page_title="AI Property Price Predictor",
    initial_sidebar_state="expanded",
    page_icon="🏠",
)

# Map creation function
def create_map(lat, lon, location_name=None):
    """Create a fresh map object"""
    m = folium.Map(
        location=[lat, lon],
        zoom_start=15,
        tiles="cartodbpositron",
        attr="CartoDB Positron",
        control_scale=True,
    )
    
    # Add marker
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
    
    # Add plugins
    MousePosition().add_to(m)
    Fullscreen().add_to(m)
    
    return m

# Custom CSS
st.markdown("""
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
</style>
""", unsafe_allow_html=True)

# Hero section
st.markdown("""
<div class="pp-hero">
  <div class="pp-inline">
    <div>
      <div class="pp-hero-title">AI Property Price Predictor</div>
      <div class="pp-hero-sub">Modern price insights using property specs + location signals.</div>
    </div>
    <div class="pp-pill">Live • Streamlit</div>
  </div>
</div>
""", unsafe_allow_html=True)

# Sidebar - Location Selection
with st.sidebar:
    st.header("📍 Location Selection")
    
    # Location input method selection
    search_method = st.radio(
        "Choose input method:",
        ["📌 Enter Coordinates", "🗺️ Click on Map"],
        key="search_method"
    )
    
    # Get current location from session state
    lat = st.session_state.selected_lat
    lon = st.session_state.selected_lon
    location_name = st.session_state.location_name

    # Coordinate input fields
    if search_method == "📌 Enter Coordinates":
        col1, col2 = st.columns(2)
        with col1:
            lat_input = st.number_input("Latitude", 
                                      value=lat or 28.6139, 
                                      format="%.5f", 
                                      step=0.0001,
                                      key="lat_input")
        with col2:
            lon_input = st.number_input("Longitude", 
                                      value=lon or 77.2090, 
                                      format="%.5f", 
                                      step=0.0001,
                                      key="lon_input")
        
        if st.button("✅ Use Coordinates", use_container_width=True):
            st.session_state.selected_lat = lat_input
            st.session_state.selected_lon = lon_input
            st.session_state.location_name = f"{lat_input:.5f}, {lon_input:.5f}"
            st.session_state.location_features = None  # Clear cached features
            st.rerun()
    else:
        st.info("Click on the map to select a location.")
    
    st.markdown("---")
    
    # Property Details
    st.header("🏡 Property Details")
    bedrooms = st.slider("Bedrooms", 1, 6, 3, key="bed")
    bathrooms = st.slider("Bathrooms", 1.0, 4.0, 2.0, 0.5, key="bath")
    sqft = st.slider("Living Area (sqft)", 500, 4000, 1500, 50, key="sqft")

# Main content
col_map, col_info = st.columns([2, 1], gap="large")

# Map Display
with col_map:
    st.markdown(
        '<div class="pp-card pp-map-card"><div class="pp-map-head">📍 Property Location</div>',
        unsafe_allow_html=True,
    )
    
    # Default coordinates (New Delhi)
    default_lat, default_lon = 28.6139, 77.2090
    lat = st.session_state.selected_lat or default_lat
    lon = st.session_state.selected_lon or default_lon
    
    # Create map
    m = create_map(lat, lon, location_name)
    
    # Display map and handle clicks
    try:
        map_data = st_folium(
            m,
            height=560,
            width="100%",
            key="main_map"
        )
        
        # Handle map clicks
        if search_method == "🗺️ Click on Map" and map_data and map_data.get("last_clicked"):
            clicked = map_data["last_clicked"]
            new_lat = float(clicked["lat"])
            new_lon = float(clicked["lng"])
            
            # Only update if location changed
            if (st.session_state.selected_lat != new_lat or 
                st.session_state.selected_lon != new_lon):
                st.session_state.selected_lat = new_lat
                st.session_state.selected_lon = new_lon
                st.session_state.location_name = f"{new_lat:.5f}, {new_lon:.5f}"
                st.session_state.location_features = None
                st.rerun()
                
    except Exception as e:
        st.warning("⚠️ Map temporarily unavailable. Please refresh the page.")
    
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
        
        # Get location features
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
            
            # Display metrics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Greenery (NDVI)", f"{ndvi_val:.3f}")
                st.metric("Connectivity", f"{road_val:.3f}")
            with col2:
                st.metric("Water (NDWI)", f"{ndwi_val:.3f}")
            
            # Warning if features are default/zero
            if ndvi_val == 0 and ndwi_val == 0 and (road_val == 0 or road_val == 0.3):
                st.warning("Satellite features are all zero or default. Check API access.")
        else:
            st.error(f"Error loading features: {features['error']}")

# Main Analysis Section
if lat and lon:
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Price Prediction", "Nearby Amenities", "Location Quality", "Property Comparison"])
    
    with tab1:
        st.header("Price Prediction")
        
        try:
            # Get price prediction
            result = predict_price(bedrooms, bathrooms, sqft, lat, lon)
            price = result.get("predicted_price")

            # Price Display
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Predicted Price", f"${price:,.0f}")
            with col2:
                price_per_sqft = price / sqft if sqft > 0 else 0
                st.metric("Price/sqft", f"${price_per_sqft:,.0f}")
            with col3:
                st.metric("Property Size", f"{sqft:,} sqft")

            # Explanation
            if result.get("explanation"):
                st.info(f"**Why this price?** {result['explanation']}")
                
            if result.get("location_context"):
                st.caption(f"Location context: {result['location_context']}")
                
        except Exception as e:
            st.error(f"Error getting price prediction: {str(e)}")
    
    with tab2:
        st.header("Nearby Amenities")
        st.write("Discover what's nearby - schools, hospitals, shops, and more!")
        
        # Range slider
        amenity_radius = st.slider(
            "Search Range (meters)",
            min_value=100,
            max_value=1000,
            value=500,
            step=100,
            key="amenity_range"
        )
        
        with st.spinner("Finding nearby amenities..."):
            try:
                amenities = get_nearby_amenities(lat, lon, amenity_radius)
                
                if amenities.get("error"):
                    st.error(f"Error: {amenities['error']}")
                else:
                    st.success(f"Found {len(amenities.get('amenities', []))} amenities within {amenity_radius}m")
                    
                    # Display amenities by category
                    categories = {}
                    for amenity in amenities.get('amenities', []):
                        cat = amenity.get('type', 'Other')
                        if cat not in categories:
                            categories[cat] = []
                        categories[cat].append(amenity)
                    
                    for category, items in categories.items():
                        with st.expander(f"{category} ({len(items)})", expanded=True):
                            for item in items[:10]:  # Show first 10 of each category
                                st.write(f"**{item.get('name', 'Unnamed')}**")
                                if item.get('distance'):
                                    st.caption(f"Distance: {item['distance']}m")
            except Exception as e:
                st.error(f"Error fetching amenities: {str(e)}")
    
    with tab3:
        st.header("Location Quality")
        st.write("Understand the quality of this location")
        
        if "error" not in features:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                ndvi = float(features.get("ndvi", 0))
                st.metric("Greenery Index", f"{ndvi:.3f}")
                if ndvi > 0.3:
                    st.success("High greenery - great for families!")
                elif ndvi > 0.1:
                    st.info("Moderate greenery")
                else:
                    st.warning("Low greenery - urban area")
            
            with col2:
                ndwi = float(features.get("ndwi", 0))
                st.metric("Water Proximity", f"{ndwi:.3f}")
                if ndwi > 0.2:
                    st.success("Near water - premium location!")
                elif ndwi > 0.1:
                    st.info("Some water nearby")
                else:
                    st.info("No major water bodies")
            
            with col3:
                road_density = float(features.get("road_density", 0.3))
                st.metric("Road Density", f"{road_density:.3f}")
                if road_density > 0.6:
                    st.success("Excellent connectivity!")
                elif road_density > 0.3:
                    st.info("Good connectivity")
                else:
                    st.info("Quiet area")
        else:
            st.error("Could not load location quality data")
    
    with tab4:
        st.header("Property Comparison")
        st.write("Compare multiple locations side by side")
        
        # Add current location to comparison
        if st.button("➕ Add to Comparison", 
                    help="Add current location to comparison list",
                    key="add_to_compare"):
            if "comparison_locations" not in st.session_state:
                st.session_state.comparison_locations = []
            
            # Check if already in comparison
            location_exists = any(
                loc.get("lat") == lat and loc.get("lon") == lon 
                for loc in st.session_state.comparison_locations
            )
            
            if not location_exists:
                st.session_state.comparison_locations.append({
                    "name": location_name or f"Location {len(st.session_state.comparison_locations) + 1}",
                    "lat": lat,
                    "lon": lon,
                    "bedrooms": bedrooms,
                    "bathrooms": bathrooms,
                    "sqft": sqft
                })
                st.success("Added to comparison!")
                st.rerun()
            else:
                st.warning("This location is already in your comparison list")
        
        # Show comparison table if we have locations
        if st.session_state.comparison_locations:
            st.subheader("Comparison Table")
            
            # Create comparison data
            comparison_data = []
            
            for loc in st.session_state.comparison_locations:
                try:
                    # Get price prediction
                    price_data = predict_price(
                        loc["bedrooms"], 
                        loc["bathrooms"], 
                        loc["sqft"], 
                        loc["lat"], 
                        loc["lon"]
                    )
                    
                    # Get features
                    loc_features = get_features(loc["lat"], loc["lon"]) or {}
                    
                    comparison_data.append({
                        "Location": loc["name"],
                        "Price": f"${price_data.get('predicted_price', 0):,.0f}",
                        "Price/sqft": f"${price_data.get('predicted_price', 0) / loc['sqft']:,.0f}" if loc['sqft'] > 0 else "N/A",
                        "Beds": loc["bedrooms"],
                        "Baths": loc["bathrooms"],
                        "Sqft": f"{loc['sqft']:,}",
                        "Greenery": f"{loc_features.get('ndvi', 0):.2f}",
                        "Water": f"{loc_features.get('ndwi', 0):.2f}",
                        "Connectivity": f"{loc_features.get('road_density', 0.3):.2f}"
                    })
                except Exception as e:
                    st.error(f"Error comparing location: {str(e)}")
            
            # Display comparison table
            if comparison_data:
                df = pd.DataFrame(comparison_data)
                st.dataframe(df, use_container_width=True)
                
                # Add clear button
                if st.button("Clear Comparison", type="secondary"):
                    st.session_state.comparison_locations = []
                    st.rerun()
            else:
                st.info("No comparison data available")
        else:
            st.info("Add locations to compare their features and prices")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 1rem;'>
    <p><strong>AI Property Price Predictor</strong></p>
    <p>Powered by AI and Satellite Data</p>
</div>
""", unsafe_allow_html=True)