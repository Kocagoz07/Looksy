# Photo Location Feature - Technical Design Document

## Executive Summary

This document outlines the architecture for a photo location feature that allows users to tag photos with locations via GPS or manual map selection, with strong privacy controls.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MOBILE CLIENT                                       │
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         LOCATION SERVICES                                │   │
│  │  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐               │   │
│  │  │ GPS Provider  │  │ Map Picker    │  │ Recent/Saved  │               │   │
│  │  │ (CoreLocation │  │ (MapKit/      │  │ Locations     │               │   │
│  │  │  / Fused)     │  │  Google Maps) │  │ Cache         │               │   │
│  │  └───────┬───────┘  └───────┬───────┘  └───────┬───────┘               │   │
│  │          │                  │                  │                        │   │
│  │          └──────────────────┼──────────────────┘                        │   │
│  │                             ▼                                           │   │
│  │  ┌─────────────────────────────────────────────────────────────────┐   │   │
│  │  │                  LOCATION MANAGER                                │   │   │
│  │  │  • Permission handling       • Coordinate normalization         │   │   │
│  │  │  • Accuracy management       • Privacy zone detection           │   │   │
│  │  │  • Battery optimization      • Location fuzzing                 │   │   │
│  │  └─────────────────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
│                                      ▼                                          │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      GEOCODING SERVICE                                   │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │   │
│  │  │ Reverse         │  │ Forward         │  │ Place Search    │         │   │
│  │  │ Geocoding       │  │ Geocoding       │  │ (POI Lookup)    │         │   │
│  │  │ (Coords→Addr)   │  │ (Addr→Coords)   │  │                 │         │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                      │                                          │
└──────────────────────────────────────┼──────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              BACKEND SERVICES                                    │
│                                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐              │
│  │   Location API   │  │  Geocoding Proxy │  │  Privacy Engine  │              │
│  │                  │  │                  │  │                  │              │
│  │  • CRUD ops      │  │  • Rate limiting │  │  • Zone masking  │              │
│  │  • Validation    │  │  • Caching       │  │  • Fuzzing       │              │
│  │  • Geospatial    │  │  • Provider      │  │  • Consent mgmt  │              │
│  │    queries       │  │    fallback      │  │  • Data retention│              │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘              │
│           │                     │                     │                         │
│           └─────────────────────┼─────────────────────┘                         │
│                                 ▼                                               │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                         DATA LAYER                                       │   │
│  │                                                                          │   │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐         │   │
│  │  │   MongoDB       │  │   Redis Cache   │  │   Elasticsearch │         │   │
│  │  │   (Primary)     │  │   (Geocode)     │  │   (Geo Search)  │         │   │
│  │  │                 │  │                 │  │                 │         │   │
│  │  │  • Posts        │  │  • Geocode      │  │  • Location     │         │   │
│  │  │  • Locations    │  │    results      │  │    indexing     │         │   │
│  │  │  • User prefs   │  │  • Popular      │  │  • Nearby       │         │   │
│  │  │  • Privacy zones│  │    places       │  │    search       │         │   │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘         │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Database Schema

### 2.1 MongoDB Collections

```javascript
// locations collection - Stores location data
{
  "_id": ObjectId,
  "location_id": "loc_abc123xyz",
  
  // Core coordinates (stored with precision)
  "coordinates": {
    "type": "Point",
    "coordinates": [-122.4194, 37.7749]  // [longitude, latitude] - GeoJSON format
  },
  
  // Geocoded address components
  "address": {
    "formatted": "123 Market St, San Francisco, CA 94103, USA",
    "street_number": "123",
    "street_name": "Market Street",
    "neighborhood": "Financial District",
    "city": "San Francisco",
    "state": "California",
    "state_code": "CA",
    "country": "United States",
    "country_code": "US",
    "postal_code": "94103"
  },
  
  // Place information (if POI)
  "place": {
    "place_id": "ChIJIQBpAG2ahYAR_6128GcTUEo",  // Google/Apple Place ID
    "name": "Ferry Building",
    "category": "landmark",
    "categories": ["tourist_attraction", "market", "landmark"],
    "phone": "+1-415-983-8000",
    "website": "https://www.ferrybuildingmarketplace.com",
    "hours": {...},
    "photos": [...]
  },
  
  // Display settings
  "display": {
    "name": "Ferry Building",           // User-facing name
    "short_name": "Ferry Building, SF", // Shortened version
    "icon": "landmark"                  // Category icon
  },
  
  // Statistics
  "stats": {
    "post_count": 1547,
    "recent_post_count": 23,  // Last 7 days
    "trending_score": 8.5
  },
  
  // Metadata
  "source": "google_places",  // google_places, apple_maps, user_created, gps
  "verified": true,
  "created_at": ISODate,
  "updated_at": ISODate
}

// post_locations collection - Links posts to locations with privacy
{
  "_id": ObjectId,
  "post_id": "post_xyz789",
  "user_id": "user_123abc",
  "location_id": "loc_abc123xyz",
  
  // Original coordinates (private - never exposed publicly)
  "original_coordinates": {
    "type": "Point",
    "coordinates": [-122.41941234, 37.77491234]
  },
  
  // Public coordinates (may be fuzzed based on privacy settings)
  "public_coordinates": {
    "type": "Point", 
    "coordinates": [-122.419, 37.775]  // Reduced precision
  },
  
  // Privacy settings for this post's location
  "privacy": {
    "precision_level": "neighborhood",  // exact, street, neighborhood, city, hidden
    "show_on_map": true,
    "show_in_location_feed": true,
    "exclude_from_search": false
  },
  
  // Timestamps
  "tagged_at": ISODate,
  "photo_taken_at": ISODate  // From EXIF if available
}

// user_location_settings collection - User's location privacy preferences
{
  "_id": ObjectId,
  "user_id": "user_123abc",
  
  // Default privacy settings
  "default_privacy": {
    "precision_level": "neighborhood",
    "show_on_map": true,
    "show_in_location_feed": true,
    "allow_location_suggestions": true
  },
  
  // Privacy zones (locations to never share precisely)
  "privacy_zones": [
    {
      "zone_id": "zone_home",
      "name": "Home",
      "center": {
        "type": "Point",
        "coordinates": [-122.4100, 37.7800]
      },
      "radius_meters": 200,
      "action": "fuzz_to_neighborhood"  // fuzz_to_neighborhood, fuzz_to_city, hide_completely
    },
    {
      "zone_id": "zone_work",
      "name": "Work",
      "center": {
        "type": "Point",
        "coordinates": [-122.3900, 37.7900]
      },
      "radius_meters": 100,
      "action": "fuzz_to_neighborhood"
    }
  ],
  
  // Location history settings
  "history": {
    "save_location_history": true,
    "history_retention_days": 90,
    "allow_timeline_view": false
  },
  
  // Saved/favorite locations
  "saved_locations": [
    {
      "location_id": "loc_abc123xyz",
      "nickname": "My favorite cafe",
      "saved_at": ISODate
    }
  ],
  
  "updated_at": ISODate
}

// geocode_cache collection - Cache for geocoding results (TTL indexed)
{
  "_id": ObjectId,
  "cache_key": "reverse_37.7749_-122.4194_en",  // type_lat_lng_locale
  "coordinates": {
    "latitude": 37.7749,
    "longitude": -122.4194
  },
  "result": {
    "formatted_address": "...",
    "components": {...},
    "place_id": "..."
  },
  "provider": "google",
  "locale": "en",
  "created_at": ISODate,
  "expires_at": ISODate  // TTL index - auto-delete after 30 days
}
```

### 2.2 MongoDB Indexes

```javascript
// Geospatial indexes for location queries
db.locations.createIndex({ "coordinates": "2dsphere" })
db.post_locations.createIndex({ "public_coordinates": "2dsphere" })
db.post_locations.createIndex({ "original_coordinates": "2dsphere" })
db.user_location_settings.createIndex({ "privacy_zones.center": "2dsphere" })

// Compound indexes for common queries
db.locations.createIndex({ "address.city": 1, "address.country_code": 1 })
db.locations.createIndex({ "place.name": "text", "address.formatted": "text" })
db.locations.createIndex({ "stats.trending_score": -1 })

db.post_locations.createIndex({ "location_id": 1, "tagged_at": -1 })
db.post_locations.createIndex({ "user_id": 1, "tagged_at": -1 })
db.post_locations.createIndex({ "post_id": 1 }, { unique: true })

// TTL index for geocode cache
db.geocode_cache.createIndex({ "expires_at": 1 }, { expireAfterSeconds: 0 })
db.geocode_cache.createIndex({ "cache_key": 1 }, { unique: true })
```

---

## 3. API Endpoints

### 3.1 Location Management APIs

```yaml
# ==================== LOCATION CRUD ====================

# Search for locations (places, addresses)
GET /api/locations/search
Query Parameters:
  q: string              # Search query
  lat: float            # Current latitude (for proximity)
  lng: float            # Current longitude
  radius: int           # Search radius in meters (default: 5000)
  types: string[]       # Filter by types: poi, address, city, region
  limit: int            # Max results (default: 20)
Response:
  {
    "results": [
      {
        "location_id": "loc_abc123",
        "name": "Ferry Building",
        "address": "1 Ferry Building, San Francisco, CA",
        "coordinates": { "lat": 37.7955, "lng": -122.3937 },
        "distance_meters": 450,
        "category": "landmark",
        "post_count": 1547,
        "icon": "landmark"
      }
    ],
    "has_more": true
  }

# Get location details
GET /api/locations/{location_id}
Response:
  {
    "location_id": "loc_abc123",
    "name": "Ferry Building",
    "full_address": "1 Ferry Building, San Francisco, CA 94111",
    "coordinates": { "lat": 37.7955, "lng": -122.3937 },
    "place": {
      "category": "landmark",
      "phone": "+1-415-983-8000",
      "website": "https://...",
      "hours": {...}
    },
    "stats": {
      "post_count": 1547,
      "recent_posts": 23
    },
    "recent_posts": [...]  # Preview of recent posts
  }

# Get posts at a location
GET /api/locations/{location_id}/posts
Query Parameters:
  cursor: string
  limit: int
Response:
  {
    "posts": [...],
    "next_cursor": "..."
  }

# Get nearby locations
GET /api/locations/nearby
Query Parameters:
  lat: float (required)
  lng: float (required)
  radius: int (default: 1000, max: 10000)
  limit: int (default: 20)
Response:
  {
    "locations": [
      {
        "location_id": "...",
        "name": "...",
        "distance_meters": 150,
        ...
      }
    ]
  }

# Get trending locations
GET /api/locations/trending
Query Parameters:
  lat: float            # Optional - for local trending
  lng: float
  timeframe: string     # day, week, month
  limit: int
Response:
  {
    "locations": [...],
    "timeframe": "week"
  }

# ==================== GEOCODING ====================

# Reverse geocode (coordinates to address)
POST /api/geocode/reverse
Body:
  {
    "latitude": 37.7749,
    "longitude": -122.4194,
    "locale": "en"       # Optional
  }
Response:
  {
    "formatted_address": "123 Market St, San Francisco, CA 94103",
    "components": {
      "street_number": "123",
      "street_name": "Market Street",
      "neighborhood": "Financial District",
      "city": "San Francisco",
      "state": "California",
      "country": "United States",
      "postal_code": "94103"
    },
    "place": {           # If near a POI
      "place_id": "...",
      "name": "Starbucks",
      "category": "cafe"
    },
    "location_id": "loc_existing123"  # If location already exists
  }

# Forward geocode (address to coordinates)
POST /api/geocode/forward
Body:
  {
    "address": "Ferry Building, San Francisco",
    "locale": "en"
  }
Response:
  {
    "results": [
      {
        "formatted_address": "1 Ferry Building, San Francisco, CA 94111",
        "coordinates": { "lat": 37.7955, "lng": -122.3937 },
        "location_id": "loc_abc123",
        "confidence": 0.95
      }
    ]
  }

# ==================== POST LOCATION TAGGING ====================

# Add location to post
POST /api/posts/{post_id}/location
Body:
  {
    "location_id": "loc_abc123",        # Use existing location
    # OR
    "coordinates": {                     # Create from coordinates
      "latitude": 37.7749,
      "longitude": -122.4194
    },
    "privacy": {                         # Optional - override defaults
      "precision_level": "neighborhood",
      "show_on_map": true
    }
  }
Response:
  {
    "post_id": "post_xyz",
    "location": {
      "location_id": "loc_abc123",
      "name": "Ferry Building",
      "display_address": "San Francisco, CA"  # Based on privacy
    },
    "privacy_applied": "neighborhood"
  }

# Update post location privacy
PATCH /api/posts/{post_id}/location
Body:
  {
    "privacy": {
      "precision_level": "city",
      "show_on_map": false
    }
  }

# Remove location from post
DELETE /api/posts/{post_id}/location

# ==================== USER LOCATION SETTINGS ====================

# Get user's location settings
GET /api/users/me/location-settings
Response:
  {
    "default_privacy": {...},
    "privacy_zones": [...],
    "saved_locations": [...],
    "history_settings": {...}
  }

# Update location settings
PATCH /api/users/me/location-settings
Body:
  {
    "default_privacy": {
      "precision_level": "neighborhood"
    }
  }

# Add privacy zone
POST /api/users/me/location-settings/privacy-zones
Body:
  {
    "name": "Home",
    "latitude": 37.7800,
    "longitude": -122.4100,
    "radius_meters": 200,
    "action": "fuzz_to_neighborhood"
  }

# Delete privacy zone
DELETE /api/users/me/location-settings/privacy-zones/{zone_id}

# Save a location
POST /api/users/me/saved-locations
Body:
  {
    "location_id": "loc_abc123",
    "nickname": "My favorite cafe"
  }

# Get user's location history (if enabled)
GET /api/users/me/location-history
Query Parameters:
  start_date: string
  end_date: string
Response:
  {
    "history": [
      {
        "date": "2024-01-15",
        "locations": [...]
      }
    ]
  }

# Delete location history
DELETE /api/users/me/location-history
Query Parameters:
  before_date: string   # Delete history before this date
```

---

## 4. Backend Implementation

### 4.1 Location Service (Python/FastAPI)

```python
# backend/services/location_service.py

from typing import Optional, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import math
import uuid

from motor.motor_asyncio import AsyncIOMotorDatabase
from pydantic import BaseModel, Field
import aiohttp

# ==================== MODELS ====================

class Coordinates(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)

class AddressComponents(BaseModel):
    formatted: str
    street_number: Optional[str] = None
    street_name: Optional[str] = None
    neighborhood: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    state_code: Optional[str] = None
    country: Optional[str] = None
    country_code: Optional[str] = None
    postal_code: Optional[str] = None

class PrivacySettings(BaseModel):
    precision_level: str = "neighborhood"  # exact, street, neighborhood, city, hidden
    show_on_map: bool = True
    show_in_location_feed: bool = True
    exclude_from_search: bool = False

class PrivacyZone(BaseModel):
    zone_id: str
    name: str
    center: Coordinates
    radius_meters: int
    action: str  # fuzz_to_neighborhood, fuzz_to_city, hide_completely

# ==================== LOCATION SERVICE ====================

class LocationService:
    """Handles all location-related operations"""
    
    # Precision levels in meters
    PRECISION_LEVELS = {
        "exact": 0,
        "street": 50,
        "neighborhood": 500,
        "city": 5000,
        "hidden": None
    }
    
    def __init__(self, db: AsyncIOMotorDatabase, geocoding_api_key: str):
        self.db = db
        self.geocoding_api_key = geocoding_api_key
        self.geocode_cache_ttl = 30 * 24 * 60 * 60  # 30 days
    
    # ==================== GEOCODING ====================
    
    async def reverse_geocode(
        self,
        latitude: float,
        longitude: float,
        locale: str = "en"
    ) -> dict:
        """Convert coordinates to address"""
        
        # Check cache first
        cache_key = f"reverse_{latitude:.6f}_{longitude:.6f}_{locale}"
        cached = await self._get_geocode_cache(cache_key)
        if cached:
            return cached
        
        # Call geocoding provider
        result = await self._call_geocoding_api(
            "reverse",
            latitude=latitude,
            longitude=longitude,
            locale=locale
        )
        
        # Cache result
        await self._set_geocode_cache(cache_key, result)
        
        # Check if location already exists
        existing = await self._find_nearby_location(latitude, longitude, threshold_meters=50)
        if existing:
            result["location_id"] = existing["location_id"]
        
        return result
    
    async def forward_geocode(
        self,
        address: str,
        locale: str = "en",
        bias_location: Optional[Coordinates] = None
    ) -> List[dict]:
        """Convert address to coordinates"""
        
        cache_key = f"forward_{hashlib.md5(address.lower().encode()).hexdigest()}_{locale}"
        cached = await self._get_geocode_cache(cache_key)
        if cached:
            return cached
        
        result = await self._call_geocoding_api(
            "forward",
            address=address,
            locale=locale,
            bias_location=bias_location
        )
        
        await self._set_geocode_cache(cache_key, result)
        return result
    
    async def _call_geocoding_api(
        self,
        mode: str,
        **kwargs
    ) -> dict:
        """Call external geocoding API (Google Maps / Apple Maps)"""
        
        async with aiohttp.ClientSession() as session:
            if mode == "reverse":
                url = (
                    f"https://maps.googleapis.com/maps/api/geocode/json"
                    f"?latlng={kwargs['latitude']},{kwargs['longitude']}"
                    f"&language={kwargs['locale']}"
                    f"&key={self.geocoding_api_key}"
                )
            else:  # forward
                url = (
                    f"https://maps.googleapis.com/maps/api/geocode/json"
                    f"?address={kwargs['address']}"
                    f"&language={kwargs['locale']}"
                    f"&key={self.geocoding_api_key}"
                )
            
            async with session.get(url) as response:
                data = await response.json()
                
                if data["status"] != "OK":
                    raise GeocodingError(f"Geocoding failed: {data['status']}")
                
                return self._parse_geocoding_response(data, mode)
    
    def _parse_geocoding_response(self, data: dict, mode: str) -> dict:
        """Parse Google Maps geocoding response"""
        
        if mode == "reverse":
            result = data["results"][0] if data["results"] else {}
            
            components = {}
            for comp in result.get("address_components", []):
                types = comp["types"]
                if "street_number" in types:
                    components["street_number"] = comp["long_name"]
                elif "route" in types:
                    components["street_name"] = comp["long_name"]
                elif "neighborhood" in types or "sublocality" in types:
                    components["neighborhood"] = comp["long_name"]
                elif "locality" in types:
                    components["city"] = comp["long_name"]
                elif "administrative_area_level_1" in types:
                    components["state"] = comp["long_name"]
                    components["state_code"] = comp["short_name"]
                elif "country" in types:
                    components["country"] = comp["long_name"]
                    components["country_code"] = comp["short_name"]
                elif "postal_code" in types:
                    components["postal_code"] = comp["long_name"]
            
            return {
                "formatted_address": result.get("formatted_address", ""),
                "components": components,
                "place_id": result.get("place_id")
            }
        
        else:  # forward
            results = []
            for result in data["results"][:5]:
                location = result["geometry"]["location"]
                results.append({
                    "formatted_address": result["formatted_address"],
                    "coordinates": {
                        "lat": location["lat"],
                        "lng": location["lng"]
                    },
                    "place_id": result["place_id"],
                    "confidence": 0.9 if result["geometry"].get("location_type") == "ROOFTOP" else 0.7
                })
            return results
    
    # ==================== LOCATION CRUD ====================
    
    async def search_locations(
        self,
        query: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius_meters: int = 5000,
        types: Optional[List[str]] = None,
        limit: int = 20
    ) -> List[dict]:
        """Search for locations by text query"""
        
        pipeline = []
        
        # Text search
        pipeline.append({
            "$match": {
                "$text": {"$search": query}
            }
        })
        
        # Add distance if coordinates provided
        if latitude and longitude:
            pipeline.insert(0, {
                "$geoNear": {
                    "near": {
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    },
                    "distanceField": "distance_meters",
                    "maxDistance": radius_meters,
                    "spherical": True
                }
            })
        
        # Filter by types
        if types:
            pipeline.append({
                "$match": {"place.category": {"$in": types}}
            })
        
        # Project fields
        pipeline.append({
            "$project": {
                "_id": 0,
                "location_id": 1,
                "display.name": 1,
                "address.formatted": 1,
                "coordinates": 1,
                "place.category": 1,
                "stats.post_count": 1,
                "distance_meters": 1
            }
        })
        
        pipeline.append({"$limit": limit})
        
        results = await self.db.locations.aggregate(pipeline).to_list(limit)
        return results
    
    async def get_nearby_locations(
        self,
        latitude: float,
        longitude: float,
        radius_meters: int = 1000,
        limit: int = 20
    ) -> List[dict]:
        """Get locations near a point"""
        
        pipeline = [
            {
                "$geoNear": {
                    "near": {
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    },
                    "distanceField": "distance_meters",
                    "maxDistance": radius_meters,
                    "spherical": True
                }
            },
            {
                "$match": {
                    "stats.post_count": {"$gt": 0}  # Only locations with posts
                }
            },
            {
                "$sort": {"stats.post_count": -1}
            },
            {
                "$limit": limit
            },
            {
                "$project": {
                    "_id": 0,
                    "location_id": 1,
                    "display": 1,
                    "coordinates": 1,
                    "place.category": 1,
                    "stats.post_count": 1,
                    "distance_meters": 1
                }
            }
        ]
        
        return await self.db.locations.aggregate(pipeline).to_list(limit)
    
    async def get_or_create_location(
        self,
        latitude: float,
        longitude: float,
        place_id: Optional[str] = None
    ) -> dict:
        """Get existing location or create new one"""
        
        # Try to find existing
        if place_id:
            existing = await self.db.locations.find_one(
                {"place.place_id": place_id},
                {"_id": 0}
            )
            if existing:
                return existing
        
        # Find nearby
        existing = await self._find_nearby_location(latitude, longitude, threshold_meters=50)
        if existing:
            return existing
        
        # Create new location
        geocode_result = await self.reverse_geocode(latitude, longitude)
        
        location = {
            "location_id": f"loc_{uuid.uuid4().hex[:12]}",
            "coordinates": {
                "type": "Point",
                "coordinates": [longitude, latitude]
            },
            "address": geocode_result.get("components", {}),
            "display": {
                "name": self._generate_display_name(geocode_result),
                "short_name": self._generate_short_name(geocode_result)
            },
            "place": {
                "place_id": geocode_result.get("place_id")
            },
            "stats": {
                "post_count": 0,
                "recent_post_count": 0
            },
            "source": "geocoding",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        await self.db.locations.insert_one(location)
        return location
    
    # ==================== PRIVACY ====================
    
    async def apply_privacy(
        self,
        user_id: str,
        latitude: float,
        longitude: float,
        privacy_settings: Optional[PrivacySettings] = None
    ) -> Tuple[float, float, str]:
        """
        Apply privacy settings to coordinates.
        Returns (fuzzed_lat, fuzzed_lng, applied_precision)
        """
        
        # Get user's settings
        user_settings = await self.db.user_location_settings.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        
        # Check privacy zones first
        if user_settings and user_settings.get("privacy_zones"):
            for zone in user_settings["privacy_zones"]:
                zone_center = zone["center"]["coordinates"]
                distance = self._calculate_distance(
                    latitude, longitude,
                    zone_center[1], zone_center[0]  # lat, lng
                )
                
                if distance <= zone["radius_meters"]:
                    # User is in a privacy zone
                    action = zone["action"]
                    if action == "hide_completely":
                        return None, None, "hidden"
                    elif action == "fuzz_to_city":
                        precision = "city"
                    else:
                        precision = "neighborhood"
                    
                    fuzzed_lat, fuzzed_lng = self._fuzz_coordinates(
                        latitude, longitude,
                        self.PRECISION_LEVELS[precision]
                    )
                    return fuzzed_lat, fuzzed_lng, precision
        
        # Apply default or requested privacy
        if privacy_settings:
            precision = privacy_settings.precision_level
        elif user_settings:
            precision = user_settings.get("default_privacy", {}).get("precision_level", "neighborhood")
        else:
            precision = "neighborhood"
        
        if precision == "hidden":
            return None, None, "hidden"
        elif precision == "exact":
            return latitude, longitude, "exact"
        else:
            fuzz_distance = self.PRECISION_LEVELS.get(precision, 500)
            fuzzed_lat, fuzzed_lng = self._fuzz_coordinates(
                latitude, longitude, fuzz_distance
            )
            return fuzzed_lat, fuzzed_lng, precision
    
    def _fuzz_coordinates(
        self,
        latitude: float,
        longitude: float,
        distance_meters: int
    ) -> Tuple[float, float]:
        """Add random noise to coordinates within specified distance"""
        
        import random
        
        # Convert distance to degrees (approximate)
        # 1 degree latitude ≈ 111km
        # 1 degree longitude ≈ 111km * cos(latitude)
        
        lat_offset = distance_meters / 111000  # degrees
        lng_offset = distance_meters / (111000 * math.cos(math.radians(latitude)))
        
        # Random angle and distance
        angle = random.uniform(0, 2 * math.pi)
        distance_factor = random.uniform(0.5, 1.0)  # At least 50% of max distance
        
        fuzzed_lat = latitude + (lat_offset * distance_factor * math.sin(angle))
        fuzzed_lng = longitude + (lng_offset * distance_factor * math.cos(angle))
        
        # Round to reduce precision
        if distance_meters >= 5000:
            fuzzed_lat = round(fuzzed_lat, 2)
            fuzzed_lng = round(fuzzed_lng, 2)
        elif distance_meters >= 500:
            fuzzed_lat = round(fuzzed_lat, 3)
            fuzzed_lng = round(fuzzed_lng, 3)
        else:
            fuzzed_lat = round(fuzzed_lat, 4)
            fuzzed_lng = round(fuzzed_lng, 4)
        
        return fuzzed_lat, fuzzed_lng
    
    # ==================== HELPERS ====================
    
    async def _find_nearby_location(
        self,
        latitude: float,
        longitude: float,
        threshold_meters: int
    ) -> Optional[dict]:
        """Find existing location within threshold distance"""
        
        result = await self.db.locations.find_one({
            "coordinates": {
                "$near": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    },
                    "$maxDistance": threshold_meters
                }
            }
        }, {"_id": 0})
        
        return result
    
    def _calculate_distance(
        self,
        lat1: float, lon1: float,
        lat2: float, lon2: float
    ) -> float:
        """Calculate distance between two points in meters (Haversine)"""
        
        R = 6371000  # Earth's radius in meters
        
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)
        
        a = (math.sin(delta_phi / 2) ** 2 +
             math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        return R * c
    
    def _generate_display_name(self, geocode_result: dict) -> str:
        """Generate user-friendly display name"""
        components = geocode_result.get("components", {})
        
        if components.get("neighborhood"):
            return components["neighborhood"]
        elif components.get("city"):
            return components["city"]
        else:
            return geocode_result.get("formatted_address", "Unknown Location")
    
    def _generate_short_name(self, geocode_result: dict) -> str:
        """Generate short display name"""
        components = geocode_result.get("components", {})
        
        parts = []
        if components.get("neighborhood"):
            parts.append(components["neighborhood"])
        if components.get("city"):
            parts.append(components["city"])
        
        return ", ".join(parts[:2]) if parts else "Unknown"
    
    async def _get_geocode_cache(self, cache_key: str) -> Optional[dict]:
        """Get cached geocoding result"""
        cached = await self.db.geocode_cache.find_one(
            {"cache_key": cache_key},
            {"_id": 0, "result": 1}
        )
        return cached["result"] if cached else None
    
    async def _set_geocode_cache(self, cache_key: str, result: dict):
        """Cache geocoding result"""
        await self.db.geocode_cache.update_one(
            {"cache_key": cache_key},
            {
                "$set": {
                    "result": result,
                    "created_at": datetime.now(timezone.utc),
                    "expires_at": datetime.now(timezone.utc) + timedelta(days=30)
                }
            },
            upsert=True
        )


class GeocodingError(Exception):
    pass
```

### 4.2 API Endpoints (FastAPI)

```python
# backend/routes/location_routes.py

from fastapi import APIRouter, HTTPException, Request, Query
from typing import Optional, List
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/locations", tags=["locations"])

# ==================== REQUEST/RESPONSE MODELS ====================

class ReverseGeocodeRequest(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    locale: str = "en"

class ForwardGeocodeRequest(BaseModel):
    address: str = Field(..., min_length=1, max_length=500)
    locale: str = "en"

class AddLocationToPostRequest(BaseModel):
    location_id: Optional[str] = None
    coordinates: Optional[dict] = None
    privacy: Optional[dict] = None

class PrivacyZoneRequest(BaseModel):
    name: str = Field(..., max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_meters: int = Field(..., ge=50, le=5000)
    action: str = Field(..., pattern="^(fuzz_to_neighborhood|fuzz_to_city|hide_completely)$")

# ==================== ENDPOINTS ====================

@router.get("/search")
async def search_locations(
    request: Request,
    q: str = Query(..., min_length=1),
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    radius: int = Query(5000, ge=100, le=50000),
    types: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50)
):
    """Search for locations by name or address"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    type_list = types.split(",") if types else None
    
    results = await location_service.search_locations(
        query=q,
        latitude=lat,
        longitude=lng,
        radius_meters=radius,
        types=type_list,
        limit=limit
    )
    
    return {"results": results, "has_more": len(results) == limit}


@router.get("/nearby")
async def get_nearby_locations(
    request: Request,
    lat: float = Query(..., ge=-90, le=90),
    lng: float = Query(..., ge=-180, le=180),
    radius: int = Query(1000, ge=100, le=10000),
    limit: int = Query(20, ge=1, le=50)
):
    """Get locations near a point"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    locations = await location_service.get_nearby_locations(
        latitude=lat,
        longitude=lng,
        radius_meters=radius,
        limit=limit
    )
    
    return {"locations": locations}


@router.get("/trending")
async def get_trending_locations(
    request: Request,
    lat: Optional[float] = Query(None, ge=-90, le=90),
    lng: Optional[float] = Query(None, ge=-180, le=180),
    timeframe: str = Query("week", pattern="^(day|week|month)$"),
    limit: int = Query(20, ge=1, le=50)
):
    """Get trending locations"""
    
    # Build aggregation based on timeframe
    timeframe_days = {"day": 1, "week": 7, "month": 30}[timeframe]
    
    pipeline = [
        {
            "$match": {
                "stats.recent_post_count": {"$gt": 0}
            }
        },
        {
            "$sort": {"stats.trending_score": -1}
        },
        {
            "$limit": limit
        }
    ]
    
    # Add geo filter if location provided
    if lat and lng:
        pipeline.insert(0, {
            "$geoNear": {
                "near": {"type": "Point", "coordinates": [lng, lat]},
                "distanceField": "distance",
                "maxDistance": 50000,
                "spherical": True
            }
        })
    
    locations = await db.locations.aggregate(pipeline).to_list(limit)
    
    return {"locations": locations, "timeframe": timeframe}


@router.get("/{location_id}")
async def get_location(request: Request, location_id: str):
    """Get location details"""
    
    location = await db.locations.find_one(
        {"location_id": location_id},
        {"_id": 0}
    )
    
    if not location:
        raise HTTPException(status_code=404, detail="Location not found")
    
    # Get recent posts preview
    recent_posts = await db.post_locations.aggregate([
        {"$match": {"location_id": location_id, "privacy.show_in_location_feed": True}},
        {"$sort": {"tagged_at": -1}},
        {"$limit": 9},
        {"$lookup": {
            "from": "posts",
            "localField": "post_id",
            "foreignField": "post_id",
            "as": "post"
        }},
        {"$unwind": "$post"},
        {"$project": {
            "_id": 0,
            "post_id": 1,
            "post.image_id": 1,
            "post.likes_count": 1
        }}
    ]).to_list(9)
    
    location["recent_posts"] = recent_posts
    
    return location


@router.get("/{location_id}/posts")
async def get_location_posts(
    request: Request,
    location_id: str,
    cursor: Optional[str] = None,
    limit: int = Query(20, ge=1, le=50)
):
    """Get posts tagged at a location"""
    
    query = {
        "location_id": location_id,
        "privacy.show_in_location_feed": True
    }
    
    if cursor:
        query["tagged_at"] = {"$lt": cursor}
    
    post_locations = await db.post_locations.find(
        query,
        {"_id": 0}
    ).sort("tagged_at", -1).limit(limit + 1).to_list(limit + 1)
    
    has_more = len(post_locations) > limit
    if has_more:
        post_locations = post_locations[:limit]
    
    # Get full post data
    post_ids = [pl["post_id"] for pl in post_locations]
    posts = await db.posts.find(
        {"post_id": {"$in": post_ids}},
        {"_id": 0}
    ).to_list(limit)
    
    next_cursor = post_locations[-1]["tagged_at"] if post_locations else None
    
    return {
        "posts": posts,
        "next_cursor": next_cursor if has_more else None
    }


# ==================== GEOCODING ====================

@router.post("/geocode/reverse")
async def reverse_geocode(request: Request, body: ReverseGeocodeRequest):
    """Convert coordinates to address"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        result = await location_service.reverse_geocode(
            latitude=body.latitude,
            longitude=body.longitude,
            locale=body.locale
        )
        return result
    except GeocodingError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/geocode/forward")
async def forward_geocode(request: Request, body: ForwardGeocodeRequest):
    """Convert address to coordinates"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        results = await location_service.forward_geocode(
            address=body.address,
            locale=body.locale
        )
        return {"results": results}
    except GeocodingError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ==================== POST LOCATION ====================

@router.post("/posts/{post_id}/location")
async def add_location_to_post(
    request: Request,
    post_id: str,
    body: AddLocationToPostRequest
):
    """Add location tag to a post"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    # Verify post ownership
    post = await db.posts.find_one({"post_id": post_id, "user_id": user.user_id})
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Get or create location
    if body.location_id:
        location = await db.locations.find_one({"location_id": body.location_id})
        if not location:
            raise HTTPException(status_code=404, detail="Location not found")
        latitude = location["coordinates"]["coordinates"][1]
        longitude = location["coordinates"]["coordinates"][0]
    elif body.coordinates:
        latitude = body.coordinates["latitude"]
        longitude = body.coordinates["longitude"]
        location = await location_service.get_or_create_location(latitude, longitude)
    else:
        raise HTTPException(status_code=400, detail="location_id or coordinates required")
    
    # Apply privacy
    privacy_settings = PrivacySettings(**body.privacy) if body.privacy else None
    public_lat, public_lng, precision = await location_service.apply_privacy(
        user_id=user.user_id,
        latitude=latitude,
        longitude=longitude,
        privacy_settings=privacy_settings
    )
    
    # Create post_location record
    post_location = {
        "post_id": post_id,
        "user_id": user.user_id,
        "location_id": location["location_id"],
        "original_coordinates": {
            "type": "Point",
            "coordinates": [longitude, latitude]
        },
        "public_coordinates": {
            "type": "Point",
            "coordinates": [public_lng, public_lat]
        } if public_lat else None,
        "privacy": {
            "precision_level": precision,
            "show_on_map": body.privacy.get("show_on_map", True) if body.privacy else True,
            "show_in_location_feed": body.privacy.get("show_in_location_feed", True) if body.privacy else True
        },
        "tagged_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Upsert (update if exists)
    await db.post_locations.update_one(
        {"post_id": post_id},
        {"$set": post_location},
        upsert=True
    )
    
    # Update location stats
    await db.locations.update_one(
        {"location_id": location["location_id"]},
        {"$inc": {"stats.post_count": 1, "stats.recent_post_count": 1}}
    )
    
    # Determine display address based on privacy
    display_address = _get_display_address(location, precision)
    
    return {
        "post_id": post_id,
        "location": {
            "location_id": location["location_id"],
            "name": location["display"]["name"],
            "display_address": display_address
        },
        "privacy_applied": precision
    }


@router.delete("/posts/{post_id}/location")
async def remove_location_from_post(request: Request, post_id: str):
    """Remove location tag from post"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    result = await db.post_locations.delete_one({
        "post_id": post_id,
        "user_id": user.user_id
    })
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Location tag not found")
    
    return {"message": "Location removed"}


# ==================== USER SETTINGS ====================

@router.get("/users/me/location-settings")
async def get_location_settings(request: Request):
    """Get user's location privacy settings"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    settings = await db.user_location_settings.find_one(
        {"user_id": user.user_id},
        {"_id": 0}
    )
    
    if not settings:
        # Return defaults
        return {
            "default_privacy": {
                "precision_level": "neighborhood",
                "show_on_map": True,
                "show_in_location_feed": True
            },
            "privacy_zones": [],
            "saved_locations": []
        }
    
    return settings


@router.patch("/users/me/location-settings")
async def update_location_settings(request: Request, body: dict):
    """Update user's location settings"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    update = {"$set": {"updated_at": datetime.now(timezone.utc).isoformat()}}
    
    if "default_privacy" in body:
        update["$set"]["default_privacy"] = body["default_privacy"]
    
    await db.user_location_settings.update_one(
        {"user_id": user.user_id},
        update,
        upsert=True
    )
    
    return {"message": "Settings updated"}


@router.post("/users/me/location-settings/privacy-zones")
async def add_privacy_zone(request: Request, body: PrivacyZoneRequest):
    """Add a privacy zone"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    zone = {
        "zone_id": f"zone_{uuid.uuid4().hex[:8]}",
        "name": body.name,
        "center": {
            "type": "Point",
            "coordinates": [body.longitude, body.latitude]
        },
        "radius_meters": body.radius_meters,
        "action": body.action
    }
    
    await db.user_location_settings.update_one(
        {"user_id": user.user_id},
        {
            "$push": {"privacy_zones": zone},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        },
        upsert=True
    )
    
    return zone


@router.delete("/users/me/location-settings/privacy-zones/{zone_id}")
async def delete_privacy_zone(request: Request, zone_id: str):
    """Delete a privacy zone"""
    
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    await db.user_location_settings.update_one(
        {"user_id": user.user_id},
        {
            "$pull": {"privacy_zones": {"zone_id": zone_id}},
            "$set": {"updated_at": datetime.now(timezone.utc).isoformat()}
        }
    )
    
    return {"message": "Privacy zone deleted"}


def _get_display_address(location: dict, precision: str) -> str:
    """Get display address based on privacy level"""
    address = location.get("address", {})
    
    if precision == "exact" or precision == "street":
        return address.get("formatted", location["display"]["name"])
    elif precision == "neighborhood":
        parts = []
        if address.get("neighborhood"):
            parts.append(address["neighborhood"])
        if address.get("city"):
            parts.append(address["city"])
        return ", ".join(parts) if parts else location["display"]["name"]
    elif precision == "city":
        parts = []
        if address.get("city"):
            parts.append(address["city"])
        if address.get("state_code"):
            parts.append(address["state_code"])
        return ", ".join(parts) if parts else address.get("country", "")
    else:
        return ""
```

---

## 5. iOS Implementation

### 5.1 Location Manager

```swift
// iOS/Services/LocationManager.swift

import CoreLocation
import Combine

class LocationManager: NSObject, ObservableObject {
    
    // MARK: - Published Properties
    
    @Published var currentLocation: CLLocation?
    @Published var authorizationStatus: CLAuthorizationStatus = .notDetermined
    @Published var isLocating = false
    @Published var error: LocationError?
    
    // MARK: - Private Properties
    
    private let locationManager = CLLocationManager()
    private var locationContinuation: CheckedContinuation<CLLocation, Error>?
    
    // MARK: - Configuration
    
    struct Configuration {
        var desiredAccuracy: CLLocationAccuracy = kCLLocationAccuracyHundredMeters
        var distanceFilter: CLLocationDistance = 100
        var activityType: CLActivityType = .other
        var allowsBackgroundUpdates = false
    }
    
    var configuration = Configuration() {
        didSet {
            applyConfiguration()
        }
    }
    
    // MARK: - Initialization
    
    override init() {
        super.init()
        locationManager.delegate = self
        authorizationStatus = locationManager.authorizationStatus
        applyConfiguration()
    }
    
    // MARK: - Public Methods
    
    func requestPermission() {
        locationManager.requestWhenInUseAuthorization()
    }
    
    func requestCurrentLocation() async throws -> CLLocation {
        guard authorizationStatus == .authorizedWhenInUse || 
              authorizationStatus == .authorizedAlways else {
            throw LocationError.notAuthorized
        }
        
        isLocating = true
        
        return try await withCheckedThrowingContinuation { continuation in
            self.locationContinuation = continuation
            locationManager.requestLocation()
        }
    }
    
    func startUpdatingLocation() {
        guard authorizationStatus == .authorizedWhenInUse ||
              authorizationStatus == .authorizedAlways else {
            error = .notAuthorized
            return
        }
        
        isLocating = true
        locationManager.startUpdatingLocation()
    }
    
    func stopUpdatingLocation() {
        locationManager.stopUpdatingLocation()
        isLocating = false
    }
    
    // MARK: - Private Methods
    
    private func applyConfiguration() {
        locationManager.desiredAccuracy = configuration.desiredAccuracy
        locationManager.distanceFilter = configuration.distanceFilter
        locationManager.activityType = configuration.activityType
        locationManager.allowsBackgroundLocationUpdates = configuration.allowsBackgroundUpdates
    }
}

// MARK: - CLLocationManagerDelegate

extension LocationManager: CLLocationManagerDelegate {
    
    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        guard let location = locations.last else { return }
        
        // Filter out old or inaccurate locations
        let age = -location.timestamp.timeIntervalSinceNow
        guard age < 60, location.horizontalAccuracy >= 0, location.horizontalAccuracy < 500 else {
            return
        }
        
        currentLocation = location
        isLocating = false
        
        if let continuation = locationContinuation {
            locationContinuation = nil
            continuation.resume(returning: location)
        }
    }
    
    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        isLocating = false
        
        let locationError: LocationError
        if let clError = error as? CLError {
            switch clError.code {
            case .denied:
                locationError = .notAuthorized
            case .locationUnknown:
                locationError = .locationUnknown
            default:
                locationError = .unknown(clError.localizedDescription)
            }
        } else {
            locationError = .unknown(error.localizedDescription)
        }
        
        self.error = locationError
        
        if let continuation = locationContinuation {
            locationContinuation = nil
            continuation.resume(throwing: locationError)
        }
    }
    
    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        authorizationStatus = manager.authorizationStatus
    }
}

// MARK: - Errors

enum LocationError: Error, LocalizedError {
    case notAuthorized
    case locationUnknown
    case geocodingFailed(String)
    case unknown(String)
    
    var errorDescription: String? {
        switch self {
        case .notAuthorized:
            return "Location access not authorized"
        case .locationUnknown:
            return "Unable to determine location"
        case .geocodingFailed(let message):
            return "Geocoding failed: \(message)"
        case .unknown(let message):
            return message
        }
    }
}
```

### 5.2 Geocoding Service

```swift
// iOS/Services/GeocodingService.swift

import CoreLocation
import MapKit

class GeocodingService {
    
    private let geocoder = CLGeocoder()
    private let backendURL: String
    
    init(backendURL: String) {
        self.backendURL = backendURL
    }
    
    // MARK: - Reverse Geocoding (Coordinates → Address)
    
    func reverseGeocode(
        latitude: Double,
        longitude: Double
    ) async throws -> GeocodingResult {
        
        let location = CLLocation(latitude: latitude, longitude: longitude)
        
        // Try Apple's geocoder first (free, no API limits for reasonable usage)
        do {
            let placemarks = try await geocoder.reverseGeocodeLocation(location)
            
            if let placemark = placemarks.first {
                return GeocodingResult(from: placemark)
            }
        } catch {
            print("Apple geocoding failed, trying backend: \(error)")
        }
        
        // Fallback to backend (which uses Google Maps)
        return try await reverseGeocodeViaBackend(latitude: latitude, longitude: longitude)
    }
    
    private func reverseGeocodeViaBackend(
        latitude: Double,
        longitude: Double
    ) async throws -> GeocodingResult {
        
        let url = URL(string: "\(backendURL)/api/geocode/reverse")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        
        let body = ["latitude": latitude, "longitude": longitude]
        request.httpBody = try JSONEncoder().encode(body)
        
        let (data, response) = try await URLSession.shared.data(for: request)
        
        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw LocationError.geocodingFailed("Backend error")
        }
        
        let result = try JSONDecoder().decode(BackendGeocodingResponse.self, from: data)
        return GeocodingResult(from: result)
    }
    
    // MARK: - Forward Geocoding (Address → Coordinates)
    
    func forwardGeocode(address: String) async throws -> [GeocodingResult] {
        
        let placemarks = try await geocoder.geocodeAddressString(address)
        
        return placemarks.compactMap { placemark in
            guard let location = placemark.location else { return nil }
            var result = GeocodingResult(from: placemark)
            result.coordinates = Coordinates(
                latitude: location.coordinate.latitude,
                longitude: location.coordinate.longitude
            )
            return result
        }
    }
    
    // MARK: - Place Search
    
    func searchPlaces(
        query: String,
        near location: CLLocation? = nil,
        radius: CLLocationDistance = 5000
    ) async throws -> [PlaceResult] {
        
        let request = MKLocalSearch.Request()
        request.naturalLanguageQuery = query
        
        if let location = location {
            request.region = MKCoordinateRegion(
                center: location.coordinate,
                latitudinalMeters: radius * 2,
                longitudinalMeters: radius * 2
            )
        }
        
        let search = MKLocalSearch(request: request)
        let response = try await search.start()
        
        return response.mapItems.map { item in
            PlaceResult(
                name: item.name ?? "",
                address: item.placemark.formattedAddress,
                coordinates: Coordinates(
                    latitude: item.placemark.coordinate.latitude,
                    longitude: item.placemark.coordinate.longitude
                ),
                category: item.pointOfInterestCategory?.rawValue,
                distance: location?.distance(from: CLLocation(
                    latitude: item.placemark.coordinate.latitude,
                    longitude: item.placemark.coordinate.longitude
                ))
            )
        }
    }
}

// MARK: - Models

struct Coordinates: Codable {
    let latitude: Double
    let longitude: Double
}

struct GeocodingResult {
    var formattedAddress: String
    var streetNumber: String?
    var streetName: String?
    var neighborhood: String?
    var city: String?
    var state: String?
    var stateCode: String?
    var country: String?
    var countryCode: String?
    var postalCode: String?
    var coordinates: Coordinates?
    var placeId: String?
    
    init(from placemark: CLPlacemark) {
        self.formattedAddress = [
            placemark.subThoroughfare,
            placemark.thoroughfare,
            placemark.locality,
            placemark.administrativeArea,
            placemark.postalCode,
            placemark.country
        ].compactMap { $0 }.joined(separator: ", ")
        
        self.streetNumber = placemark.subThoroughfare
        self.streetName = placemark.thoroughfare
        self.neighborhood = placemark.subLocality
        self.city = placemark.locality
        self.state = placemark.administrativeArea
        self.country = placemark.country
        self.countryCode = placemark.isoCountryCode
        self.postalCode = placemark.postalCode
    }
    
    init(from response: BackendGeocodingResponse) {
        self.formattedAddress = response.formattedAddress
        self.streetNumber = response.components.streetNumber
        self.streetName = response.components.streetName
        self.neighborhood = response.components.neighborhood
        self.city = response.components.city
        self.state = response.components.state
        self.stateCode = response.components.stateCode
        self.country = response.components.country
        self.countryCode = response.components.countryCode
        self.postalCode = response.components.postalCode
        self.placeId = response.placeId
    }
}

struct PlaceResult: Identifiable {
    let id = UUID()
    let name: String
    let address: String
    let coordinates: Coordinates
    let category: String?
    let distance: Double?
}

struct BackendGeocodingResponse: Codable {
    let formattedAddress: String
    let components: AddressComponents
    let placeId: String?
    
    struct AddressComponents: Codable {
        let streetNumber: String?
        let streetName: String?
        let neighborhood: String?
        let city: String?
        let state: String?
        let stateCode: String?
        let country: String?
        let countryCode: String?
        let postalCode: String?
    }
}

// MARK: - Extensions

extension CLPlacemark {
    var formattedAddress: String {
        [subThoroughfare, thoroughfare, locality, administrativeArea]
            .compactMap { $0 }
            .joined(separator: ", ")
    }
}

extension MKPlacemark {
    var formattedAddress: String {
        [subThoroughfare, thoroughfare, locality, administrativeArea]
            .compactMap { $0 }
            .joined(separator: ", ")
    }
}
```

### 5.3 Location Picker View (SwiftUI)

```swift
// iOS/Views/LocationPickerView.swift

import SwiftUI
import MapKit

struct LocationPickerView: View {
    
    @Environment(\.dismiss) private var dismiss
    
    @StateObject private var locationManager = LocationManager()
    @StateObject private var viewModel: LocationPickerViewModel
    
    @Binding var selectedLocation: SelectedLocation?
    
    @State private var region = MKCoordinateRegion(
        center: CLLocationCoordinate2D(latitude: 37.7749, longitude: -122.4194),
        span: MKCoordinateSpan(latitudeDelta: 0.05, longitudeDelta: 0.05)
    )
    @State private var searchText = ""
    @State private var showingPrivacySettings = false
    
    init(selectedLocation: Binding<SelectedLocation?>, backendURL: String) {
        self._selectedLocation = selectedLocation
        self._viewModel = StateObject(wrappedValue: LocationPickerViewModel(backendURL: backendURL))
    }
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                // Search bar
                searchBar
                
                // Content
                if searchText.isEmpty {
                    // Map + Current location + Recent
                    mapAndSuggestions
                } else {
                    // Search results
                    searchResults
                }
            }
            .navigationTitle("Add Location")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarLeading) {
                    Button("Cancel") {
                        dismiss()
                    }
                }
                
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button {
                        showingPrivacySettings = true
                    } label: {
                        Image(systemName: "shield")
                    }
                }
            }
            .sheet(isPresented: $showingPrivacySettings) {
                LocationPrivacySettingsView()
            }
        }
        .onAppear {
            setupLocationManager()
        }
    }
    
    // MARK: - Search Bar
    
    private var searchBar: some View {
        HStack {
            Image(systemName: "magnifyingglass")
                .foregroundColor(.gray)
            
            TextField("Search places", text: $searchText)
                .textFieldStyle(.plain)
                .autocorrectionDisabled()
                .onChange(of: searchText) { newValue in
                    viewModel.search(query: newValue, near: locationManager.currentLocation)
                }
            
            if !searchText.isEmpty {
                Button {
                    searchText = ""
                } label: {
                    Image(systemName: "xmark.circle.fill")
                        .foregroundColor(.gray)
                }
            }
        }
        .padding(12)
        .background(Color(.systemGray6))
        .cornerRadius(10)
        .padding()
    }
    
    // MARK: - Map and Suggestions
    
    private var mapAndSuggestions: some View {
        ScrollView {
            VStack(spacing: 16) {
                // Interactive Map
                mapView
                
                // Use Current Location
                if locationManager.authorizationStatus == .authorizedWhenInUse ||
                   locationManager.authorizationStatus == .authorizedAlways {
                    currentLocationButton
                }
                
                // Nearby Places
                if !viewModel.nearbyPlaces.isEmpty {
                    nearbyPlacesSection
                }
                
                // Recent Locations
                if !viewModel.recentLocations.isEmpty {
                    recentLocationsSection
                }
            }
            .padding()
        }
    }
    
    // MARK: - Map View
    
    private var mapView: some View {
        ZStack {
            Map(coordinateRegion: $region, annotationItems: viewModel.mapAnnotations) { annotation in
                MapAnnotation(coordinate: annotation.coordinate) {
                    VStack {
                        Image(systemName: "mappin.circle.fill")
                            .font(.title)
                            .foregroundColor(.red)
                        
                        if annotation.isSelected {
                            Text(annotation.name)
                                .font(.caption)
                                .padding(4)
                                .background(Color.white)
                                .cornerRadius(4)
                                .shadow(radius: 2)
                        }
                    }
                }
            }
            .frame(height: 200)
            .cornerRadius(12)
            .onTapGesture { location in
                // Handle map tap to select location
                handleMapTap(at: location)
            }
            
            // Center pin for manual selection
            Image(systemName: "mappin")
                .font(.title)
                .foregroundColor(.blue)
        }
    }
    
    // MARK: - Current Location Button
    
    private var currentLocationButton: some View {
        Button {
            Task {
                await useCurrentLocation()
            }
        } label: {
            HStack {
                Image(systemName: "location.fill")
                    .foregroundColor(.blue)
                
                Text("Use Current Location")
                    .fontWeight(.medium)
                
                Spacer()
                
                if viewModel.isLoadingCurrentLocation {
                    ProgressView()
                }
            }
            .padding()
            .background(Color(.systemGray6))
            .cornerRadius(10)
        }
        .disabled(viewModel.isLoadingCurrentLocation)
    }
    
    // MARK: - Nearby Places
    
    private var nearbyPlacesSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Nearby")
                .font(.headline)
            
            ForEach(viewModel.nearbyPlaces) { place in
                LocationRow(place: place) {
                    selectPlace(place)
                }
            }
        }
    }
    
    // MARK: - Recent Locations
    
    private var recentLocationsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Recent")
                .font(.headline)
            
            ForEach(viewModel.recentLocations) { location in
                LocationRow(place: location) {
                    selectPlace(location)
                }
            }
        }
    }
    
    // MARK: - Search Results
    
    private var searchResults: some View {
        List {
            if viewModel.isSearching {
                HStack {
                    Spacer()
                    ProgressView()
                    Spacer()
                }
            } else if viewModel.searchResults.isEmpty {
                Text("No results found")
                    .foregroundColor(.secondary)
            } else {
                ForEach(viewModel.searchResults) { result in
                    LocationRow(place: result) {
                        selectPlace(result)
                    }
                }
            }
        }
        .listStyle(.plain)
    }
    
    // MARK: - Actions
    
    private func setupLocationManager() {
        if locationManager.authorizationStatus == .notDetermined {
            locationManager.requestPermission()
        }
        
        if let location = locationManager.currentLocation {
            region.center = location.coordinate
            viewModel.loadNearbyPlaces(near: location)
        }
    }
    
    private func useCurrentLocation() async {
        viewModel.isLoadingCurrentLocation = true
        
        do {
            let location = try await locationManager.requestCurrentLocation()
            let geocoded = try await viewModel.geocodingService.reverseGeocode(
                latitude: location.coordinate.latitude,
                longitude: location.coordinate.longitude
            )
            
            selectedLocation = SelectedLocation(
                coordinates: Coordinates(
                    latitude: location.coordinate.latitude,
                    longitude: location.coordinate.longitude
                ),
                name: geocoded.neighborhood ?? geocoded.city ?? "Current Location",
                address: geocoded.formattedAddress
            )
            
            dismiss()
            
        } catch {
            // Handle error
            print("Error getting current location: \(error)")
        }
        
        viewModel.isLoadingCurrentLocation = false
    }
    
    private func selectPlace(_ place: PlaceResult) {
        selectedLocation = SelectedLocation(
            coordinates: place.coordinates,
            name: place.name,
            address: place.address,
            locationId: nil  // Will be set by backend
        )
        dismiss()
    }
    
    private func handleMapTap(at location: CGPoint) {
        // Convert tap to coordinates and reverse geocode
        // Implementation depends on your map library
    }
}

// MARK: - Location Row

struct LocationRow: View {
    let place: PlaceResult
    let onTap: () -> Void
    
    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 12) {
                Image(systemName: iconForCategory(place.category))
                    .font(.title2)
                    .foregroundColor(.blue)
                    .frame(width: 40)
                
                VStack(alignment: .leading, spacing: 2) {
                    Text(place.name)
                        .font(.body)
                        .foregroundColor(.primary)
                    
                    Text(place.address)
                        .font(.caption)
                        .foregroundColor(.secondary)
                        .lineLimit(1)
                }
                
                Spacer()
                
                if let distance = place.distance {
                    Text(formatDistance(distance))
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.vertical, 8)
        }
    }
    
    private func iconForCategory(_ category: String?) -> String {
        switch category {
        case "restaurant", "food": return "fork.knife"
        case "cafe": return "cup.and.saucer.fill"
        case "store", "shopping": return "bag.fill"
        case "park": return "leaf.fill"
        case "gym", "fitness": return "figure.run"
        default: return "mappin.circle.fill"
        }
    }
    
    private func formatDistance(_ meters: Double) -> String {
        if meters < 1000 {
            return "\(Int(meters))m"
        } else {
            return String(format: "%.1fkm", meters / 1000)
        }
    }
}

// MARK: - Selected Location Model

struct SelectedLocation {
    let coordinates: Coordinates
    let name: String
    let address: String
    var locationId: String?
}
```

---

## 6. Android Implementation

### 6.1 Location Manager (Kotlin)

```kotlin
// Android/services/LocationManager.kt

package com.looksy.location

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.location.Location
import android.os.Looper
import androidx.core.content.ContextCompat
import com.google.android.gms.location.*
import kotlinx.coroutines.channels.awaitClose
import kotlinx.coroutines.flow.*
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlin.coroutines.resume
import kotlin.coroutines.resumeWithException

class LocationManager(private val context: Context) {
    
    private val fusedLocationClient = LocationServices.getFusedLocationProviderClient(context)
    
    // MARK: - Permission Check
    
    fun hasLocationPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            Manifest.permission.ACCESS_FINE_LOCATION
        ) == PackageManager.PERMISSION_GRANTED
    }
    
    // MARK: - Get Current Location (One-shot)
    
    suspend fun getCurrentLocation(
        priority: Int = Priority.PRIORITY_HIGH_ACCURACY,
        maxAge: Long = 60_000L  // Accept location up to 1 minute old
    ): Location = suspendCancellableCoroutine { continuation ->
        
        if (!hasLocationPermission()) {
            continuation.resumeWithException(LocationException.PermissionDenied)
            return@suspendCancellableCoroutine
        }
        
        // Try to get cached location first
        fusedLocationClient.lastLocation
            .addOnSuccessListener { lastLocation ->
                if (lastLocation != null && 
                    System.currentTimeMillis() - lastLocation.time < maxAge) {
                    continuation.resume(lastLocation)
                    return@addOnSuccessListener
                }
                
                // Request fresh location
                requestFreshLocation(priority, continuation)
            }
            .addOnFailureListener { e ->
                requestFreshLocation(priority, continuation)
            }
    }
    
    private fun requestFreshLocation(
        priority: Int,
        continuation: CancellableContinuation<Location>
    ) {
        val request = CurrentLocationRequest.Builder()
            .setPriority(priority)
            .setMaxUpdateAgeMillis(0)
            .setDurationMillis(10_000L)
            .build()
        
        try {
            fusedLocationClient.getCurrentLocation(request, null)
                .addOnSuccessListener { location ->
                    if (location != null) {
                        continuation.resume(location)
                    } else {
                        continuation.resumeWithException(LocationException.LocationUnavailable)
                    }
                }
                .addOnFailureListener { e ->
                    continuation.resumeWithException(LocationException.Unknown(e.message ?: "Unknown error"))
                }
        } catch (e: SecurityException) {
            continuation.resumeWithException(LocationException.PermissionDenied)
        }
    }
    
    // MARK: - Location Updates (Continuous)
    
    fun getLocationUpdates(
        intervalMs: Long = 10_000L,
        fastestIntervalMs: Long = 5_000L,
        priority: Int = Priority.PRIORITY_BALANCED_POWER_ACCURACY
    ): Flow<Location> = callbackFlow {
        
        if (!hasLocationPermission()) {
            throw LocationException.PermissionDenied
        }
        
        val request = LocationRequest.Builder(priority, intervalMs)
            .setMinUpdateIntervalMillis(fastestIntervalMs)
            .setWaitForAccurateLocation(false)
            .build()
        
        val callback = object : LocationCallback() {
            override fun onLocationResult(result: LocationResult) {
                result.lastLocation?.let { location ->
                    trySend(location)
                }
            }
            
            override fun onLocationAvailability(availability: LocationAvailability) {
                if (!availability.isLocationAvailable) {
                    // Location services unavailable
                }
            }
        }
        
        try {
            fusedLocationClient.requestLocationUpdates(
                request,
                callback,
                Looper.getMainLooper()
            )
        } catch (e: SecurityException) {
            throw LocationException.PermissionDenied
        }
        
        awaitClose {
            fusedLocationClient.removeLocationUpdates(callback)
        }
    }
}

// MARK: - Exceptions

sealed class LocationException : Exception() {
    object PermissionDenied : LocationException()
    object LocationUnavailable : LocationException()
    data class Unknown(override val message: String) : LocationException()
}
```

### 6.2 Geocoding Service (Kotlin)

```kotlin
// Android/services/GeocodingService.kt

package com.looksy.location

import android.content.Context
import android.location.Address
import android.location.Geocoder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import java.util.*

class GeocodingService(
    private val context: Context,
    private val backendUrl: String
) {
    
    private val geocoder = Geocoder(context, Locale.getDefault())
    
    // MARK: - Reverse Geocoding
    
    suspend fun reverseGeocode(
        latitude: Double,
        longitude: Double,
        maxResults: Int = 1
    ): List<GeocodingResult> = withContext(Dispatchers.IO) {
        
        // Try Android's Geocoder first
        try {
            if (Geocoder.isPresent()) {
                val addresses = if (android.os.Build.VERSION.SDK_INT >= 33) {
                    // Use new async API on Android 13+
                    suspendCancellableCoroutine { continuation ->
                        geocoder.getFromLocation(latitude, longitude, maxResults) { addresses ->
                            continuation.resume(addresses)
                        }
                    }
                } else {
                    @Suppress("DEPRECATION")
                    geocoder.getFromLocation(latitude, longitude, maxResults) ?: emptyList()
                }
                
                if (addresses.isNotEmpty()) {
                    return@withContext addresses.map { it.toGeocodingResult() }
                }
            }
        } catch (e: Exception) {
            // Fall through to backend
        }
        
        // Fallback to backend
        reverseGeocodeViaBackend(latitude, longitude)
    }
    
    private suspend fun reverseGeocodeViaBackend(
        latitude: Double,
        longitude: Double
    ): List<GeocodingResult> {
        // Make API call to backend
        val response = apiClient.post<BackendGeocodingResponse>(
            "$backendUrl/api/geocode/reverse",
            mapOf(
                "latitude" to latitude,
                "longitude" to longitude
            )
        )
        
        return listOf(response.toGeocodingResult())
    }
    
    // MARK: - Forward Geocoding
    
    suspend fun forwardGeocode(
        address: String,
        maxResults: Int = 5
    ): List<GeocodingResult> = withContext(Dispatchers.IO) {
        
        try {
            if (Geocoder.isPresent()) {
                val addresses = if (android.os.Build.VERSION.SDK_INT >= 33) {
                    suspendCancellableCoroutine { continuation ->
                        geocoder.getFromLocationName(address, maxResults) { addresses ->
                            continuation.resume(addresses)
                        }
                    }
                } else {
                    @Suppress("DEPRECATION")
                    geocoder.getFromLocationName(address, maxResults) ?: emptyList()
                }
                
                return@withContext addresses.map { it.toGeocodingResult() }
            }
        } catch (e: Exception) {
            // Fall through to backend
        }
        
        forwardGeocodeViaBackend(address)
    }
    
    private suspend fun forwardGeocodeViaBackend(address: String): List<GeocodingResult> {
        val response = apiClient.post<BackendForwardGeocodingResponse>(
            "$backendUrl/api/geocode/forward",
            mapOf("address" to address)
        )
        
        return response.results.map { it.toGeocodingResult() }
    }
}

// MARK: - Models

data class GeocodingResult(
    val formattedAddress: String,
    val streetNumber: String? = null,
    val streetName: String? = null,
    val neighborhood: String? = null,
    val city: String? = null,
    val state: String? = null,
    val stateCode: String? = null,
    val country: String? = null,
    val countryCode: String? = null,
    val postalCode: String? = null,
    val latitude: Double? = null,
    val longitude: Double? = null,
    val placeId: String? = null
)

// MARK: - Extensions

fun Address.toGeocodingResult(): GeocodingResult {
    val addressLines = (0..maxAddressLineIndex).mapNotNull { getAddressLine(it) }
    
    return GeocodingResult(
        formattedAddress = addressLines.joinToString(", "),
        streetNumber = subThoroughfare,
        streetName = thoroughfare,
        neighborhood = subLocality,
        city = locality,
        state = adminArea,
        countryCode = countryCode,
        country = countryName,
        postalCode = postalCode,
        latitude = if (hasLatitude()) latitude else null,
        longitude = if (hasLongitude()) longitude else null
    )
}
```

---

## 7. Privacy & Security

### 7.1 Privacy Principles

```
┌─────────────────────────────────────────────────────────────────┐
│                    PRIVACY PROTECTION LAYERS                     │
│                                                                  │
│  1. COLLECTION MINIMIZATION                                     │
│     • Only collect location when user explicitly tags           │
│     • No background location tracking                           │
│     • Don't store full GPS precision server-side               │
│                                                                  │
│  2. USER CONTROL                                                │
│     • Granular privacy settings per post                       │
│     • Privacy zones (home, work) auto-protection               │
│     • Easy location removal from posts                         │
│     • Location history deletion                                │
│                                                                  │
│  3. DATA PROTECTION                                             │
│     • Coordinate fuzzing for non-exact precision               │
│     • Separate storage for original vs public coords           │
│     • Encrypted storage for privacy zones                      │
│     • No location sharing with third parties                   │
│                                                                  │
│  4. TRANSPARENCY                                                │
│     • Clear indication when location is shared                 │
│     • Show what precision level is being used                  │
│     • Audit log of location data access                        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.2 Coordinate Fuzzing Algorithm

```python
import math
import random
from typing import Tuple

def fuzz_coordinates(
    latitude: float,
    longitude: float,
    precision_meters: int,
    seed: Optional[str] = None
) -> Tuple[float, float]:
    """
    Add deterministic noise to coordinates.
    Using seed ensures same input always produces same fuzzed output.
    """
    
    if seed:
        random.seed(hash(seed))
    
    # Convert meters to degrees
    lat_degree_meters = 111_000  # ~111km per degree latitude
    lng_degree_meters = 111_000 * math.cos(math.radians(latitude))
    
    # Calculate offset in degrees
    lat_offset_max = precision_meters / lat_degree_meters
    lng_offset_max = precision_meters / lng_degree_meters
    
    # Generate random offset within circle
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0.3, 1.0)  # At least 30% of max
    
    lat_offset = lat_offset_max * distance * math.sin(angle)
    lng_offset = lng_offset_max * distance * math.cos(angle)
    
    fuzzed_lat = latitude + lat_offset
    fuzzed_lng = longitude + lng_offset
    
    # Round to appropriate precision
    if precision_meters >= 5000:  # City level
        return round(fuzzed_lat, 2), round(fuzzed_lng, 2)
    elif precision_meters >= 500:  # Neighborhood level
        return round(fuzzed_lat, 3), round(fuzzed_lng, 3)
    else:  # Street level
        return round(fuzzed_lat, 4), round(fuzzed_lng, 4)
```

### 7.3 Privacy Zone Detection

```python
async def check_privacy_zones(
    user_id: str,
    latitude: float,
    longitude: float,
    db: AsyncIOMotorDatabase
) -> Optional[dict]:
    """
    Check if coordinates fall within any user privacy zone.
    Returns the zone config if found, None otherwise.
    """
    
    user_settings = await db.user_location_settings.find_one(
        {"user_id": user_id},
        {"privacy_zones": 1}
    )
    
    if not user_settings or not user_settings.get("privacy_zones"):
        return None
    
    point = {
        "type": "Point",
        "coordinates": [longitude, latitude]
    }
    
    for zone in user_settings["privacy_zones"]:
        # Use MongoDB geospatial query
        is_in_zone = await db.user_location_settings.find_one({
            "user_id": user_id,
            "privacy_zones": {
                "$elemMatch": {
                    "zone_id": zone["zone_id"],
                    "center": {
                        "$geoWithin": {
                            "$centerSphere": [
                                [longitude, latitude],
                                zone["radius_meters"] / 6378100  # Convert to radians
                            ]
                        }
                    }
                }
            }
        })
        
        if is_in_zone:
            return zone
    
    return None
```

---

## 8. Summary

### Key Features
- **GPS Location**: Get current location with configurable accuracy
- **Map Selection**: Interactive map for manual location picking
- **Place Search**: Search for businesses, landmarks, addresses
- **Reverse Geocoding**: Convert coordinates to human-readable addresses
- **Privacy Controls**: Coordinate fuzzing, privacy zones, precision levels

### Privacy Levels
| Level | Precision | Use Case |
|-------|-----------|----------|
| Exact | 0m | Businesses, public venues |
| Street | 50m | General posts |
| Neighborhood | 500m | Default for most posts |
| City | 5km | Maximum privacy |
| Hidden | N/A | Location not shown |

### Tech Stack
- **iOS**: CoreLocation, MapKit, CLGeocoder
- **Android**: Fused Location Provider, Geocoder
- **Backend**: FastAPI, MongoDB (geospatial), Redis (cache)
- **Geocoding**: Google Maps API (with Apple fallback on iOS)
