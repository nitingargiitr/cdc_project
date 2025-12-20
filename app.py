"""
User-Friendly Property Price Predictor
Focus on practical features for normal users - nearby amenities, location quality, etc.
Mobile-optimized with improved map interaction
"""
import streamlit as st
import folium
from streamlit_folium import st_folium
from folium.plugins import MousePosition, Fullscreen, Geocoder
import pandas as pd
import os

# Local service (replace backend HTTP calls)
from price_predictor_service import predict_price, get_features, get_nearby_amenities

st.set_page_config(
    layout="wide",
    page_title="AI Property Price Predictor",
    initial_sidebar_state="expanded"
)

# ✅ IMPROVED: Mobile-responsive map with better controls
def create_map(lat, lon, location_name=None, zoom_start=15, is_mobile=False):
    """Create optimized map with responsive controls"""
    # Adjust zoom for mobile viewing
    if is_mobile:
        map_height = 400
        zoom_start = max(12, zoom_start - 1)  # Slightly wider view on mobile
    else:
        map_height = 600
    
    m = folium.Map(
        location=[lat, lon],
        zoom_start=zoom_start,
        tiles='OpenStreetMap',
        zoom_control=True,
        prefer_canvas=True,
        max_zoom=20,
        min_zoom=10
    )
    
    # Add a prominent marker with better styling
    folium.Marker(
        [lat, lon],
        popup=f"<div style='width: 200px;'><b style='font-size: 14px;'>{location_name or 'Selected Location'}</b><br>"
              f"<code style='font-size: 11px;'>Lat: {lat:.5f}<br>Lon: {lon:.5f}</code>"
              f"<br><br><button onclick='alert(\"Location pinned!\")' style='width: 100%; padding: 5px; background: #1f77b4; color: white; border: none; border-radius: 4px; cursor: pointer;'>✓ Pin Location</button></div>",
        tooltip="👈 Click to view location details",
        icon=folium.Icon(color="red", icon="home", prefix="fa", icon_color="white", prefix_color="white"),
    ).add_to(m)
    
    # Add search radius circle for amenities
    folium.Circle(
        location=[lat, lon],
        radius=1000,
        popup="Amenities search radius: 1km",
        color="#1f77b4",
        fill=True,
        fillColor="#1f77b4",
        fillOpacity=0.08,
        weight=2,
        dash_array="5, 5"
    ).add_to(m)
    
    # Add helpful guide circle for 500m
    folium.Circle(
        location=[lat, lon],
        radius=500,
        color="#4CAF50",
        fill=False,
        weight=1,
        opacity=0.4,
        dash_array="2, 2",
        popup="500m radius"
    ).add_to(m)
    
    # Add compass and position controls
    MousePosition(position='bottomleft').add_to(m)
    Fullscreen().add_to(m)
    
    # Add geocoding search for better location discovery
    Geocoder().add_to(m)
    
    return m

# Custom CSS with mobile responsiveness
st.markdown("""
<style>
    * {
        box-sizing: border-box;
    }
    
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    
    /* Mobile responsiveness */
    @media (max-width: 768px) {
        .main-header {
            font-size: 1.8rem;
            margin-bottom: 0.5rem;
        }
        
        /* Stack columns on mobile */
        [data-testid="column"] {
            min-width: 100% !important;
            flex: 1 !important;
        }
        
        /* Make buttons larger on mobile */
        button {
            font-size: 14px;
            padding: 8px 12px !important;
        }
        
        /* Improve map touch targets */
        .leaflet-control {
            padding: 8px !important;
        }
        
        .leaflet-control button {
            width: 40px !important;
            height: 40px !important;
            font-size: 18px !important;
        }
    }
    
    .amenity-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
    
    .location-selected {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
        font-weight: bold;
    }
    
    .map-controls-info {
        background-color: #e3f2fd;
        border-left: 4px solid #2196F3;
        padding: 0.75rem;
        border-radius: 4px;
        font-size: 0.85rem;
        margin: 0.5rem 0;
    }
    
    .zoom-hint {
        background: #fff3cd;
        border: 1px solid #ffc107;
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 0.85rem;
        margin: 0.5rem 0;
    }
    
    /* Improve coordinate display */
    .coord-display {
        font-family: 'Courier New', monospace;
        background-color: #f5f5f5;
        padding: 0.5rem;
        border-radius: 4px;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🏠 AI Property Price Predictor</h1>', unsafe_allow_html=True)
st.markdown("**Find your perfect home with AI-powered price predictions and location insights**")

# Initialize session state
for key in ['selected_lat', 'selected_lon', 'location_name', 'location_features', 'comparison_locations', 'zoom_level']:
    if key == 'comparison_locations':
        st.session_state[key] = []
    elif key == 'zoom_level':
        st.session_state[key] = 15
    else:
        st.session_state[key] = None

# ✅ IMPROVED: Better mobile detection and responsive sidebar
def is_mobile():
    """Simple mobile detection based on sidebar state"""
    # Note: Mobile users often use collapsed sidebar, but we'll use a session flag
    return st.session_state.get('mobile_mode', False)

# Sidebar - Location Selection with improved UX
st.sidebar.header("📍 Location Selection")
st.sidebar.markdown("### How to find your location:")

search_method = st.sidebar.radio(
    "Choose input method:",
    ["📌 Enter Coordinates", "🗺️ Click on Map", "🔍 Quick Search"],
    key="search_method",
    help="Coordinates: Precise latitude/longitude entry | Map Click: Visual selection | Quick Search: Search by place name"
)

lat = st.session_state.selected_lat
lon = st.session_state.selected_lon
location_name = st.session_state.location_name

# Enter Coordinates
if search_method == "📌 Enter Coordinates":
    st.sidebar.markdown('<div class="map-controls-info">💡 <strong>Tip:</strong> Enter precise coordinates to pinpoint your location</div>', unsafe_allow_html=True)
    
    col1, col2 = st.sidebar.columns(2)
    with col1:
        lat_input = st.number_input(
            "Latitude",
            value=lat or 28.6139,
            format="%.5f",
            step=0.0001,
            key="lat_in",
            help="North-South position (-90 to 90)"
        )
    with col2:
        lon_input = st.number_input(
            "Longitude",
            value=lon or 77.2090,
            format="%.5f",
            step=0.0001,
            key="lon_in",
            help="East-West position (-180 to 180)"
        )
    
    if st.sidebar.button("✅ Use Coordinates", use_container_width=True, key="coord_btn"):
        st.session_state.selected_lat = lat_input
        st.session_state.selected_lon = lon_input
        st.session_state.location_name = f"{lat_input:.5f}, {lon_input:.5f}"
        st.session_state.location_features = None
        st.success("✓ Location updated! Check the map to verify.")

elif search_method == "🗺️ Click on Map":
    st.sidebar.markdown('<div class="map-controls-info">💡 <strong>Tip:</strong> Click anywhere on the map to select your location, then zoom in for details</div>', unsafe_allow_html=True)
    st.sidebar.markdown('<div class="zoom-hint">🔍 <strong>Zoom Tips:</strong> Use map controls (+/-) to zoom in and out smoothly. The red marker updates with each click.</div>', unsafe_allow_html=True)
    
elif search_method == "🔍 Quick Search":
    st.sidebar.markdown('<div class="map-controls-info">💡 <strong>Tip:</strong> Use the search box on the map to find places by name</div>', unsafe_allow_html=True)
    search_query = st.sidebar.text_input(
        "Search location:",
        placeholder="e.g., Central Park, New York",
        help="Enter location name to search"
    )
    if search_query:
        st.sidebar.info("📍 Use the search icon (🔍) on the map to find this location")

st.sidebar.markdown("---")
st.sidebar.header("🏡 Property Details")

bedrooms = st.sidebar.slider("Bedrooms", 1, 6, 3, key="bed", help="Number of bedrooms")
bathrooms = st.sidebar.slider("Bathrooms", 1.0, 4.0, 2.0, 0.5, key="bath", help="Number of bathrooms")
sqft = st.sidebar.slider("Living Area (sqft)", 500, 4000, 1500, 50, key="sqft", help="Total living area in square feet")

# ✅ IMPROVED: Responsive layout based on screen size
if lat and lon:
    # Desktop layout: 2-column, Mobile layout: 1-column
    mobile = is_mobile()
    
    if mobile:
        # Mobile: Single column
        st.subheader("📍 Map & Location")
        col_map = st.container()
        col_info = st.container()
    else:
        # Desktop: Two columns
        col_map, col_info = st.columns([2, 1])
else:
    col_map = st.container()
    col_info = st.container()

with col_map:
    if lat and lon:
        # ✅ IMPROVED: Fresh map creation with zoom tracking
        m = create_map(
            lat,
            lon,
            location_name,
            zoom_start=st.session_state.zoom_level,
            is_mobile=is_mobile()
        )
        
        # ✅ IMPROVED: Better map rendering with error handling
        map_data = None
        try:
            map_height = 400 if is_mobile() else 600
            map_data = st_folium(
                m,
                height=map_height,
                width=None,  # Full width
                key="main_map"
            )
        except Exception as e:
            st.warning("⚠️ Map temporarily unavailable. Please try refreshing the page.")
        
        # ✅ IMPROVED: Better click handling with visual feedback
        if search_method == "🗺️ Click on Map" and map_data and map_data.get("last_clicked"):
            clicked = map_data["last_clicked"]
            new_lat = float(clicked["lat"])
            new_lon = float(clicked["lng"])
            
            # Update location
            st.session_state.selected_lat = new_lat
            st.session_state.selected_lon = new_lon
            st.session_state.location_name = f"{new_lat:.5f}, {new_lon:.5f}"
            st.session_state.location_features = None
            
            # Update zoom if available
            if "zoom" in map_data:
                st.session_state.zoom_level = map_data["zoom"]
            
            # Show success feedback
            st.toast("✓ Location pinned! Scroll right to see details.", icon="📍")
        
        # Display map controls help for current method
        if search_method == "🗺️ Click on Map":
            st.markdown("""
            <div style='background: #e8f4f8; padding: 0.75rem; border-radius: 4px; margin-top: 0.5rem; border-left: 4px solid #2196F3;'>
            <strong>📌 Map Controls:</strong>
            <ul style='margin: 0.5rem 0; padding-left: 1.5rem; font-size: 0.85rem;'>
            <li><strong>Zoom:</strong> Use +/- buttons or scroll wheel to zoom in/out</li>
            <li><strong>Pan:</strong> Click and drag to move around the map</li>
            <li><strong>Click:</strong> Click anywhere to pin your location</li>
            <li><strong>Search:</strong> Use the search icon (🔍) to find locations</li>
            <li><strong>Fullscreen:</strong> Use the fullscreen button for easier navigation</li>
            </ul>
            </div>
            """, unsafe_allow_html=True)
    else:
        # Default map with instructions
        st.markdown("""
        <div style='background: #fff3cd; padding: 1rem; border-radius: 4px; border-left: 4px solid #ffc107; margin-bottom: 1rem;'>
        <strong>🗺️ Map Instructions:</strong>
        <ol style='padding-left: 1.5rem; font-size: 0.9rem;'>
        <li>Select a location method from the sidebar (📌 Coordinates or 🗺️ Map Click)</li>
        <li>Enter your coordinates or click on the map</li>
        <li>The map will appear below and you can adjust your selection</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)
        
        m_default = folium.Map(location=[28.6139, 77.2090], zoom_start=10, tiles='OpenStreetMap')
        try:
            st_folium(
                m_default,
                height=400,
                width=None,
                key="default_map"
            )
        except Exception:
            st.warning("⚠️ Map temporarily unavailable. Please try refreshing the page.")

        if search_method == "🗺️ Click on Map" and map_data and map_data.get("last_clicked"):
            clicked = map_data["last_clicked"]
            st.session_state.selected_lat = float(clicked["lat"])
            st.session_state.selected_lon = float(clicked["lng"])
            st.session_state.location_name = f"{float(clicked['lat']):.5f}, {float(clicked['lng']):.5f}"
            st.session_state.location_features = None
        
        st.info("👆 Select a location to get started")

# Location Info Panel
if lat and lon:
    mobile = is_mobile()
    
    if not mobile:
        col_info.subheader("📍 Location Info")
        with col_info:
            st.markdown(f'<div class="location-selected">📍 {location_name or "Selected Location"}</div>', unsafe_allow_html=True)
            st.markdown(f'<div class="coord-display"><strong>Latitude:</strong> {lat:.5f}<br><strong>Longitude:</strong> {lon:.5f}</div>', unsafe_allow_html=True)
    else:
        st.subheader("📍 Location Info")
        st.markdown(f'<div class="location-selected">📍 {location_name or "Selected Location"}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="coord-display"><strong>Latitude:</strong> {lat:.5f}<br><strong>Longitude:</strong> {lon:.5f}</div>', unsafe_allow_html=True)
    
    # Quick location features (use local service)
    if st.session_state.location_features is None:
        try:
            st.session_state.location_features = get_features(lat, lon)
        except Exception:
            st.session_state.location_features = {"error": "Failed to fetch features"}

    features = st.session_state.location_features or {}
    
    # Display metrics in responsive layout
    if "error" not in features:
        if mobile:
            # Mobile: Single column
            st.markdown("**📊 Location Features:**")
            col1, col2, col3 = st.columns(3)
        else:
            col1, col2, col3 = col_info.columns(3)
        
        ndvi_val = features.get('ndvi', 0)
        ndwi_val = features.get('ndwi', 0)
        road_val = features.get('road_density', 0.3)
        
        with col1:
            st.metric("🌳 Greenery", f"{ndvi_val:.3f}")
        with col2:
            st.metric("💧 Water", f"{ndwi_val:.3f}")
        with col3:
            st.metric("🛣️ Roads", f"{road_val:.3f}")
        
        # Warn if all features are zero/default
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
                st.metric("Predicted Price", f"${price:,.0f}")
            with col_price2:
                price_per_sqft_val = price / sqft if sqft > 0 else 0
                st.metric("Price/sqft", f"${price_per_sqft_val:,.0f}")
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
