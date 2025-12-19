"""
Nearby amenities detection for user-friendly location information.
"""
import requests
import numpy as np
from typing import Dict, List


def get_nearby_amenities(lat: float, lon: float, radius: int = 1000) -> Dict:
    """
    Get nearby amenities using Overpass API.
    Returns user-friendly information about schools, hospitals, shops, etc.
    """
    try:
        # Calculate bounding box
        lat_offset = radius / 111000
        lon_offset = radius / (111000 * np.cos(np.radians(lat)))
        
        bbox = f"{lat - lat_offset},{lon - lon_offset},{lat + lat_offset},{lon + lon_offset}"
        
        # Simplified query - search for amenities in a simpler way
        query = f"""
        [out:json][timeout:30];
        (
          node["amenity"]({bbox});
          way["amenity"]({bbox});
          relation["amenity"]({bbox});
        );
        out center;
        """
        
        url = "https://overpass-api.de/api/interpreter"
        
        # Retry logic for API rate limiting
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            try:
                response = requests.post(url, data={"data": query}, timeout=40)
                
                # Handle rate limiting (429) or server errors (too many requests)
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        return {
                            "total": 0,
                            "by_category": {},
                            "convenience_score": 0,
                            "convenience_rating": "Unknown",
                            "error": "Overpass API rate limited - please try again later"
                        }
                
                break  # Success, exit retry loop
                
            except requests.Timeout:
                if attempt < max_retries - 1:
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    return {
                        "total": 0,
                        "by_category": {},
                        "convenience_score": 0,
                        "convenience_rating": "Unknown",
                        "error": "Overpass API timeout - please try again"
                    }
        
        if response.status_code == 200:
            data = response.json()
            elements = data.get("elements", [])
            
            if not elements:
                return {
                    "total": 0,
                    "by_category": {},
                    "convenience_score": 0,
                    "convenience_rating": "Limited",
                    "error": None
                }
            
            # Categorize amenities
            amenities_by_category = {
                "Education": [],
                "Healthcare": [],
                "Shopping": [],
                "Dining": [],
                "Services": [],
                "Recreation": [],
                "Safety": []
            }
            
            category_mapping = {
                "school": "Education",
                "university": "Education",
                "college": "Education",
                "kindergarten": "Education",
                "hospital": "Healthcare",
                "clinic": "Healthcare",
                "pharmacy": "Healthcare",
                "dentist": "Healthcare",
                "doctors": "Healthcare",
                "supermarket": "Shopping",
                "marketplace": "Shopping",
                "shop": "Shopping",
                "bank": "Services",
                "atm": "Services",
                "post_office": "Services",
                "restaurant": "Dining",
                "cafe": "Dining",
                "bar": "Dining",
                "parking": "Services",
                "fuel": "Services",
                "gym": "Recreation",
                "cinema": "Recreation",
                "theatre": "Recreation",
                "library": "Recreation",
                "park": "Recreation",
                "police": "Safety",
                "fire_station": "Safety"
            }
            
            for element in elements:
                amenity_type = element.get("tags", {}).get("amenity", "unknown").lower()
                name = element.get("tags", {}).get("name", f"{amenity_type.title()}")
                
                # Skip if no name
                if name == "Unknown":
                    continue
                
                # Get coordinates
                if "center" in element:
                    coord = element["center"]
                elif "lat" in element:
                    coord = {"lat": element["lat"], "lon": element["lon"]}
                else:
                    continue
                
                category = category_mapping.get(amenity_type, "Services")
                
                amenities_by_category[category].append({
                    "name": name,
                    "type": amenity_type,
                    "lat": coord.get("lat"),
                    "lon": coord.get("lon")
                })
            
            # Count totals
            total_count = sum(len(amenities) for amenities in amenities_by_category.values())
            
            # Calculate convenience score (0-100)
            convenience_score = min(100, (total_count / 20) * 100)  # 20+ amenities = 100 score
            
            return {
                "total": total_count,
                "by_category": {k: v for k, v in amenities_by_category.items() if v},
                "convenience_score": round(convenience_score, 1),
                "convenience_rating": "Excellent" if convenience_score > 80 else "Very Good" if convenience_score > 60 else "Good" if convenience_score > 40 else "Fair" if convenience_score > 20 else "Limited",
                "error": None
            }
        else:
            return {
                "total": 0,
                "by_category": {},
                "convenience_score": 0,
                "convenience_rating": "Unknown",
                "error": f"Overpass API error: {response.status_code}"
            }
    except Exception as e:
        import traceback
        error_msg = str(e)
        print(f"Amenities error: {error_msg}")
        print(traceback.format_exc())
        return {
            "total": 0,
            "by_category": {},
            "convenience_score": 0,
            "convenience_rating": "Unknown",
            "error": f"Error: {error_msg}"
        }

