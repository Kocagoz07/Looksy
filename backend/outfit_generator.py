"""
AI Outfit Generator for Looksy
Uses AI to generate personalized outfit suggestions based on user preferences
"""

import os
import json
import uuid
import logging
from datetime import datetime, timezone
from typing import Optional, List, Dict
from motor.motor_asyncio import AsyncIOMotorDatabase
from emergentintegrations.llm.chat import LlmChat, UserMessage

logger = logging.getLogger(__name__)


class OutfitGenerator:
    """AI-powered outfit generation and styling suggestions"""
    
    STYLE_CATEGORIES = [
        "casual", "formal", "streetwear", "bohemian", "minimalist",
        "vintage", "sporty", "elegant", "edgy", "preppy"
    ]
    
    OCCASIONS = [
        "everyday", "work", "date night", "party", "wedding",
        "beach", "travel", "workout", "interview", "brunch"
    ]
    
    SEASONS = ["spring", "summer", "fall", "winter", "all-season"]
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
        self.api_key = os.environ.get("EMERGENT_LLM_KEY")
    
    async def initialize(self):
        """Initialize indexes for outfit collections"""
        try:
            await self.db.generated_outfits.create_index("outfit_id", unique=True)
            await self.db.generated_outfits.create_index("user_id")
            await self.db.generated_outfits.create_index("created_at")
            await self.db.user_style_profiles.create_index("user_id", unique=True)
            logger.info("Outfit generator indexes created")
        except Exception as e:
            logger.warning(f"Outfit index creation: {e}")
    
    async def generate_outfit(
        self,
        user_id: str,
        occasion: str = "everyday",
        style: str = "casual",
        season: str = "all-season",
        budget: Optional[str] = None,
        color_preference: Optional[str] = None,
        additional_notes: Optional[str] = None
    ) -> dict:
        """Generate a personalized outfit suggestion using AI"""
        
        if not self.api_key:
            raise ValueError("AI API key not configured")
        
        # Get user's style profile if exists
        style_profile = await self.get_user_style_profile(user_id)
        
        # Build the prompt
        prompt = self._build_outfit_prompt(
            occasion=occasion,
            style=style,
            season=season,
            budget=budget,
            color_preference=color_preference,
            additional_notes=additional_notes,
            style_profile=style_profile
        )
        
        try:
            # Initialize AI chat
            chat = LlmChat(
                api_key=self.api_key,
                session_id=f"outfit_{user_id}_{uuid.uuid4().hex[:8]}",
                system_message="""You are a professional fashion stylist and outfit curator for Looksy, a fashion social media platform.
                
Your task is to create detailed, stylish outfit suggestions. Be creative, trendy, and consider the user's preferences.

Always respond in valid JSON format with this structure:
{
    "outfit_name": "Creative name for the outfit",
    "description": "Brief description of the overall look and vibe",
    "items": [
        {
            "category": "top/bottom/shoes/accessory/outerwear",
            "item": "Specific item name",
            "color": "Color suggestion",
            "style_tip": "How to wear or style this piece",
            "price_range": "Budget-friendly/Mid-range/Premium"
        }
    ],
    "styling_tips": ["Tip 1", "Tip 2", "Tip 3"],
    "best_for": ["occasion 1", "occasion 2"],
    "celebrity_inspiration": "Optional: Celebrity known for this style",
    "hashtags": ["#tag1", "#tag2", "#tag3"]
}"""
            ).with_model("openai", "gpt-4o-mini")
            
            # Send message and get response
            user_message = UserMessage(text=prompt)
            response = await chat.send_message(user_message)
            
            # Parse the AI response
            outfit_data = self._parse_outfit_response(response)
            
            # Save the generated outfit
            outfit_id = f"outfit_{uuid.uuid4().hex[:12]}"
            now = datetime.now(timezone.utc).isoformat()
            
            outfit_record = {
                "outfit_id": outfit_id,
                "user_id": user_id,
                "request": {
                    "occasion": occasion,
                    "style": style,
                    "season": season,
                    "budget": budget,
                    "color_preference": color_preference,
                    "additional_notes": additional_notes
                },
                "generated_outfit": outfit_data,
                "created_at": now,
                "saved": False,
                "shared": False
            }
            
            await self.db.generated_outfits.insert_one(outfit_record)
            
            return {
                "outfit_id": outfit_id,
                "outfit": outfit_data,
                "created_at": now
            }
            
        except Exception as e:
            logger.error(f"Error generating outfit: {e}")
            raise ValueError(f"Failed to generate outfit: {str(e)}")
    
    def _build_outfit_prompt(
        self,
        occasion: str,
        style: str,
        season: str,
        budget: Optional[str],
        color_preference: Optional[str],
        additional_notes: Optional[str],
        style_profile: Optional[dict]
    ) -> str:
        """Build the AI prompt for outfit generation"""
        
        prompt_parts = [
            "Create a complete outfit for the following requirements:",
            f"- Occasion: {occasion}",
            f"- Style: {style}",
            f"- Season: {season}"
        ]
        
        if budget:
            prompt_parts.append(f"- Budget: {budget}")
        
        if color_preference:
            prompt_parts.append(f"- Color preference: {color_preference}")
        
        if additional_notes:
            prompt_parts.append(f"- Additional notes: {additional_notes}")
        
        if style_profile:
            prompt_parts.append("\nUser's style preferences:")
            if style_profile.get("favorite_styles"):
                prompt_parts.append(f"- Favorite styles: {', '.join(style_profile['favorite_styles'])}")
            if style_profile.get("favorite_colors"):
                prompt_parts.append(f"- Favorite colors: {', '.join(style_profile['favorite_colors'])}")
            if style_profile.get("body_type"):
                prompt_parts.append(f"- Body type: {style_profile['body_type']}")
            if style_profile.get("avoid"):
                prompt_parts.append(f"- Prefers to avoid: {', '.join(style_profile['avoid'])}")
        
        prompt_parts.append("\nProvide a complete outfit with 4-6 items including top, bottom, shoes, and accessories.")
        prompt_parts.append("Make sure the outfit is cohesive, stylish, and appropriate for the occasion.")
        
        return "\n".join(prompt_parts)
    
    def _parse_outfit_response(self, response: str) -> dict:
        """Parse and validate the AI response"""
        try:
            # Try to extract JSON from the response
            response = response.strip()
            
            # Handle markdown code blocks
            if response.startswith("```"):
                lines = response.split("\n")
                json_lines = []
                in_json = False
                for line in lines:
                    if line.startswith("```json"):
                        in_json = True
                        continue
                    elif line.startswith("```"):
                        in_json = False
                        continue
                    if in_json:
                        json_lines.append(line)
                response = "\n".join(json_lines)
            
            outfit_data = json.loads(response)
            
            # Validate required fields
            required_fields = ["outfit_name", "description", "items"]
            for field in required_fields:
                if field not in outfit_data:
                    outfit_data[field] = "Not provided" if field != "items" else []
            
            return outfit_data
            
        except json.JSONDecodeError:
            # Return a basic structure if parsing fails
            return {
                "outfit_name": "Custom Outfit",
                "description": response[:500] if len(response) > 500 else response,
                "items": [],
                "styling_tips": [],
                "raw_response": response
            }
    
    async def get_user_outfits(self, user_id: str, limit: int = 20) -> List[dict]:
        """Get user's generated outfits history"""
        outfits = await self.db.generated_outfits.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        return outfits
    
    async def save_outfit(self, user_id: str, outfit_id: str) -> bool:
        """Mark an outfit as saved/favorite"""
        result = await self.db.generated_outfits.update_one(
            {"outfit_id": outfit_id, "user_id": user_id},
            {"$set": {"saved": True, "saved_at": datetime.now(timezone.utc).isoformat()}}
        )
        return result.modified_count > 0
    
    async def get_user_style_profile(self, user_id: str) -> Optional[dict]:
        """Get user's style profile"""
        profile = await self.db.user_style_profiles.find_one(
            {"user_id": user_id},
            {"_id": 0}
        )
        return profile
    
    async def update_user_style_profile(self, user_id: str, profile_data: dict) -> dict:
        """Update user's style preferences"""
        now = datetime.now(timezone.utc).isoformat()
        
        update_data = {
            "user_id": user_id,
            "favorite_styles": profile_data.get("favorite_styles", []),
            "favorite_colors": profile_data.get("favorite_colors", []),
            "body_type": profile_data.get("body_type"),
            "sizes": profile_data.get("sizes", {}),
            "avoid": profile_data.get("avoid", []),
            "budget_preference": profile_data.get("budget_preference"),
            "updated_at": now
        }
        
        await self.db.user_style_profiles.update_one(
            {"user_id": user_id},
            {"$set": update_data, "$setOnInsert": {"created_at": now}},
            upsert=True
        )
        
        return update_data
    
    async def get_trending_styles(self, limit: int = 10) -> List[dict]:
        """Get trending styles based on recent outfit generations"""
        
        # Aggregate styles from recent generations
        pipeline = [
            {"$match": {"created_at": {"$gte": (datetime.now(timezone.utc).replace(day=1)).isoformat()}}},
            {"$group": {"_id": "$request.style", "count": {"$sum": 1}}},
            {"$sort": {"count": -1}},
            {"$limit": limit}
        ]
        
        results = await self.db.generated_outfits.aggregate(pipeline).to_list(limit)
        return [{"style": r["_id"], "popularity": r["count"]} for r in results if r["_id"]]
