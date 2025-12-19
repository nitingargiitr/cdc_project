"""
User-Friendly Property Price Predictor
Focus on practical features for normal users - nearby amenities, location quality, etc.
"""
import streamlit as st
import requests
import folium
from streamlit_folium import st_folium
from folium.plugins import MousePosition, Fullscreen
import pandas as pd

st.set_page_config(layout="wide", page_title="AI Property Price Predictor", initial_sidebar_state="expanded")

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 1rem;
    }
    .amenity-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        border-left: 4px solid #1f77b4;
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🏠 AI Property Price Predictor</h1>', unsafe_allow_html=True)
st.markdown("**Find your perfect home with AI-powered price predictions and location insights**")

# Initialize session state
for key in ['selected_lat', 'selected_lon', 'location_name', 'location_features', 'comparison_locations']:
    if key not in st.session_state:
        st.session_state[key] = [] if key == 'comparison_locations' else None

# Sidebar - Location Selection
st.sidebar.header("📍 Location Selection")

search_method = st.sidebar.radio(
    "Choose input method:",
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
st.sidebar.markdown("---")
st.sidebar.header("🏡 Property Details")
bedrooms = st.sidebar.slider("Bedrooms", 1, 6, 3, key="bed")
bathrooms = st.sidebar.slider("Bathrooms", 1.0, 4.0, 2.0, 0.5, key="bath")
sqft = st.sidebar.slider("Living Area (sqft)", 500, 4000, 1500, 50, key="sqft")

# Map Display
col_map, col_info = st.columns([2, 1])

with col_map:
    if lat and lon:
        m = folium.Map(location=[lat, lon], zoom_start=15, tiles='OpenStreetMap')
        
        # Add marker
        folium.Marker(
            [lat, lon],
            popup=folium.Popup(f"<b>{location_name or 'Selected Location'}</b><br>Lat: {lat:.5f}<br>Lon: {lon:.5f}", max_width=200),
            tooltip="Selected Location",
            icon=folium.Icon(color="red", icon="home", prefix="fa")
        ).add_to(m)
        
        # Add analysis radius circle
        folium.Circle(
            location=[lat, lon],
            radius=1000,
            popup="Nearby amenities search radius: 1km",
            color="#3186cc",
            fill=True,
            fillColor="#3186cc",
            fillOpacity=0.1
        ).add_to(m)
        
        # Add plugins
        MousePosition().add_to(m)
        Fullscreen().add_to(m)
        
        # Handle map clicks
        if search_method == "🗺️ Click on Map":
            map_data = st_folium(m, height=600, key="main_map")
            if map_data and map_data.get("last_clicked"):
                clicked = map_data["last_clicked"]
                st.session_state.selected_lat = float(clicked["lat"])
                st.session_state.selected_lon = float(clicked["lng"])
                st.session_state.location_name = f"{float(clicked['lat']):.5f}, {float(clicked['lng']):.5f}"
                st.session_state.location_features = None  # Clear cached features
                st.rerun()
        else:
            st_folium(m, height=600, key="main_map")
    else:
        m = folium.Map(location=[28.6139, 77.2090], zoom_start=10)
        if search_method == "🗺️ Click on Map":
            map_data = st_folium(m, height=600, key="main_map")
            if map_data and map_data.get("last_clicked"):
                clicked = map_data["last_clicked"]
                st.session_state.selected_lat = float(clicked["lat"])
                st.session_state.selected_lon = float(clicked["lng"])
                st.session_state.location_name = f"{float(clicked['lat']):.5f}, {float(clicked['lng']):.5f}"
                st.session_state.location_features = None  # Clear cached features
                st.rerun()
        else:
            st_folium(m, height=600, key="main_map")
        st.info("👆 Select a location to get started")

# Location Info Panel
with col_info:
    if lat and lon:
        st.subheader("📍 Location Info")
        st.write(f"**{location_name or 'Selected Location'}**")
        st.write(f"Lat: `{lat:.5f}`")
        st.write(f"Lon: `{lon:.5f}`")
        
        # Quick location features
        if st.session_state.location_features is None:
            try:
                features_res = requests.get(
                    "http://127.0.0.1:8000/features",
                    params={"lat": lat, "lon": lon},
                    timeout=20
                )
                if features_res.status_code == 200:
                    st.session_state.location_features = features_res.json()
                else:
                    st.session_state.location_features = {"error": "Failed to fetch features"}
            except:
                st.session_state.location_features = {"error": "Connection failed"}
        
        features = st.session_state.location_features
        if "error" not in features:
            st.metric("🌳 Greenery", f"{features.get('ndvi', 0):.3f}")
            st.metric("💧 Water", f"{features.get('ndwi', 0):.3f}")
            st.metric("🛣️ Roads", f"{features.get('road_density', 0):.3f}")

# Main Analysis Section
if lat and lon:
    st.markdown("---")
    
    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["Price Prediction", "Nearby Amenities", "Location Quality", "Property Comparison"])
    
    with tab1:
        st.header("Price Prediction")
        
        try:
            explain_res = requests.get(
                "http://127.0.0.1:8000/explain",
                params={"bedrooms": bedrooms, "bathrooms": bathrooms, "sqft_living": sqft, "lat": lat, "lon": lon},
                timeout=30
            )
            
            if explain_res.status_code == 200:
                result = explain_res.json()
                price = result["predicted_price"]
                
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
                amenities_res = requests.get(
                    "http://127.0.0.1:8000/nearby-amenities",
                    params={"lat": lat, "lon": lon, "radius": amenity_radius},
                    timeout=30
                )
                
                if amenities_res.status_code == 200:
                    amenities_data = amenities_res.json()
                    
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
                else:
                    st.error("Could not fetch amenities data")
            except Exception as e:
                st.error(f"Error: {str(e)}")
    
    with tab3:
        st.header("Location Quality")
        st.write("Understand the quality of this location")
        
        features = st.session_state.location_features
        if features and "error" not in features:
            col_qual1, col_qual2, col_qual3 = st.columns(3)
            
            with col_qual1:
                ndvi = features.get("ndvi", 0)
                st.metric("Greenery Index", f"{ndvi:.3f}")
                if ndvi > 0.3:
                    st.success("High greenery - great for families!")
                elif ndvi > 0.1:
                    st.info("Moderate greenery")
                else:
                    st.warning("Low greenery - urban area")
            
            with col_qual2:
                ndwi = features.get("ndwi", 0)
                st.metric("Water Proximity", f"{ndwi:.3f}")
                if ndwi > 0.2:
                    st.success("Near water - premium location!")
                elif ndwi > 0.1:
                    st.info("Some water nearby")
                else:
                    st.info("No major water bodies")
            
            with col_qual3:
                road_density = features.get("road_density", 0.3)
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
                    # Get price prediction
                    price_res = requests.get(
                        "http://127.0.0.1:8000/explain",
                        params={
                            "bedrooms": loc["bedrooms"], 
                            "bathrooms": loc["bathrooms"], 
                            "sqft_living": loc["sqft"], 
                            "lat": loc["lat"], 
                            "lon": loc["lon"]
                        },
                        timeout=15
                    )
                    
                    if price_res.status_code == 200:
                        price_data = price_res.json()
                        predicted_price = price_data["predicted_price"]
                        price_per_sqft = predicted_price / loc["sqft"] if loc["sqft"] > 0 else 0
                        
                        # Get location features
                        features_res = requests.get(
                            "http://127.0.0.1:8000/features",
                            params={"lat": loc["lat"], "lon": loc["lon"]},
                            timeout=15
                        )
                        
                        features = {"ndvi": 0.0, "ndwi": 0.0, "road_density": 0.3}
                        if features_res.status_code == 200:
                            features_data = features_res.json()
                            if isinstance(features_data, dict):
                                features = features_data
                        
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
                    else:
                        comparison_data.append({
                            "Location": loc["name"],
                            "Price": "API Error",
                            "Price/sqft": "API Error",
                            "Beds": loc["bedrooms"],
                            "Baths": loc["bathrooms"],
                            "Sqft": f"{loc['sqft']:,}",
                            "Greenery": "N/A",
                            "Water": "N/A",
                            "Connectivity": "N/A"
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
