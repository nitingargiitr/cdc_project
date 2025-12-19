"""
OpenAI helper functions for location search and enhanced features.
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# Initialize OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key) if api_key else None


def improve_location_query(query: str) -> str:
    """
    Use OpenAI to improve and normalize location queries.
    Helps with ambiguous queries like "Delhi" -> "Delhi, India"
    """
    if not client:
        return query  # Fallback to original query if no API key
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a location search assistant. Your job is to improve location queries for geocoding. Return ONLY the improved location query, nothing else. If the query is already clear, return it as-is. Examples: 'Delhi' -> 'Delhi, India', 'NYC' -> 'New York City, USA', 'Seattle' -> 'Seattle, WA, USA'"
                },
                {
                    "role": "user",
                    "content": f"Improve this location query for geocoding: {query}"
                }
            ],
            max_tokens=50,
            temperature=0.3
        )
        
        improved = response.choices[0].message.content.strip()
        return improved if improved else query
    except Exception as e:
        print(f"OpenAI error: {e}")
        return query  # Fallback to original


def generate_location_suggestions(query: str) -> list:
    """
    Generate location suggestions using OpenAI when search fails.
    """
    if not client:
        return []
    
    try:
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "You are a location search assistant. When a location search fails, suggest 3-5 alternative location names that might work. Return them as a comma-separated list, nothing else."
                },
                {
                    "role": "user",
                    "content": f"Location '{query}' not found. Suggest alternative location names:"
                }
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        suggestions_text = response.choices[0].message.content.strip()
        suggestions = [s.strip() for s in suggestions_text.split(",")]
        return suggestions[:5]  # Limit to 5 suggestions
    except Exception as e:
        print(f"OpenAI suggestions error: {e}")
        return []


def enhance_explanation(price: float, features: dict, base_explanation: str) -> str:
    """
    Use OpenAI to enhance the price explanation with more natural language.
    """
    if not client:
        return base_explanation
    
    try:
        prompt = f"""
        You are a real estate expert explaining property prices. 
        
        Property price: ${price:,.0f}
        Features: {features}
        Base explanation: {base_explanation}
        
        Create a more engaging, natural explanation (2-3 sentences) that explains why this property has this price. 
        Be conversational and helpful. Don't repeat the base explanation verbatim.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a friendly real estate expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7
        )
        
        enhanced = response.choices[0].message.content.strip()
        return enhanced if enhanced else base_explanation
    except Exception as e:
        print(f"OpenAI explanation error: {e}")
        return base_explanation


def analyze_location_context(lat: float, lon: float, features: dict) -> str:
    """
    Use OpenAI to provide context about the location based on features.
    """
    if not client:
        return ""
    
    try:
        prompt = f"""
        Based on these location features:
        - Greenery (NDVI): {features.get('ndvi', 0):.3f} (higher = more vegetation)
        - Water proximity (NDWI): {features.get('ndwi', 0):.3f} (higher = more water nearby)
        - Road density: {features.get('road_density', 0):.3f} (higher = more urbanized)
        - Coordinates: {lat:.5f}, {lon:.5f}
        
        Provide a brief 1-2 sentence description of what kind of area this appears to be (e.g., "urban residential area", "suburban neighborhood near water", etc.)
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a location analysis expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=100,
            temperature=0.7
        )
        
        context = response.choices[0].message.content.strip()
        return context
    except Exception as e:
        print(f"OpenAI context error: {e}")
        return ""

