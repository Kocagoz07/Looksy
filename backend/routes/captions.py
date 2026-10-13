"""AI caption + hashtag writer powered by Claude Sonnet 4.5 (streamed via SSE)."""

import json
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from typing import List, Literal, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent, TextDelta, StreamDone

import deps

router = APIRouter()
logger = logging.getLogger(__name__)

CLAUDE_PROVIDER = "anthropic"
CLAUDE_MODEL = "claude-sonnet-4-5-20250929"

SYSTEM_PROMPT = """You are Looksy's in-house fashion copywriter. Looksy is an Instagram-style fashion social app.
Write scroll-stopping, authentic captions for fashion posts. Never invent brand names or prices that were not given.
Keep each caption under 220 characters, at most 2 emojis per caption, no hashtags inside captions.

Respond ONLY in this exact format, nothing before or after:
CAPTION 1: <caption>
CAPTION 2: <caption>
CAPTION 3: <caption>
HASHTAGS: <12 to 15 relevant hashtags separated by spaces, mix of popular and niche>"""


class CaptionRequest(BaseModel):
    draft: Optional[str] = Field(None, max_length=2200)
    tone: Literal["chic", "playful", "minimal", "bold", "luxury"] = "chic"
    location: Optional[str] = Field(None, max_length=200)
    venue: Optional[str] = Field(None, max_length=200)
    music: Optional[str] = Field(None, max_length=300)
    products: List[str] = Field(default_factory=list, max_length=20)
    total_price: Optional[float] = None
    image_base64: Optional[str] = Field(None, max_length=4_000_000)


def build_prompt(req: CaptionRequest, category: Optional[str]) -> str:
    lines = [f"Tone: {req.tone}"]
    if category:
        lines.append(f"Audience: {category}'s fashion")
    if req.draft:
        lines.append(f"Creator's draft / idea: {req.draft}")
    if req.location or req.venue:
        lines.append(f"Location: {', '.join(x for x in [req.venue, req.location] if x)}")
    if req.products:
        lines.append(f"Products worn: {', '.join(req.products)}")
    if req.total_price:
        lines.append(f"Total look price: €{req.total_price:.0f}")
    if req.music:
        lines.append(f"Soundtrack: {req.music}")
    if req.image_base64:
        lines.append("The outfit photo is attached — describe what you actually see.")
    return "Write 3 caption options and hashtags for this post.\n" + "\n".join(lines)


def parse_output(text: str) -> dict:
    captions = [
        c.strip().strip('"')
        for c in re.findall(
            r"CAPTION\s*\d\s*:\s*(.+?)(?=\n\s*CAPTION\s*\d\s*:|\n\s*HASHTAGS\s*:|\Z)", text, re.S | re.I
        )
        if c.strip()
    ]
    match = re.search(r"HASHTAGS\s*:\s*(.+)", text, re.S | re.I)
    hashtags = list(dict.fromkeys(re.findall(r"#\w+", match.group(1)))) if match else []
    return {"captions": captions[:3], "hashtags": hashtags[:15]}


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


@router.post("/ai/captions/generate")
async def generate_captions(payload: CaptionRequest, request: Request):
    user = await deps.get_current_user(request)
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    api_key = os.environ.get("EMERGENT_LLM_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="AI service not configured")

    image_b64 = payload.image_base64.split(",", 1)[-1] if payload.image_base64 else None
    generation_id = f"cap_{uuid.uuid4().hex[:12]}"
    chat = LlmChat(
        api_key=api_key, session_id=generation_id, system_message=SYSTEM_PROMPT
    ).with_model(CLAUDE_PROVIDER, CLAUDE_MODEL)
    message = UserMessage(
        text=build_prompt(payload, user.category),
        file_contents=[ImageContent(image_b64)] if image_b64 else None,
    )

    async def event_stream():
        full = []
        try:
            async for ev in chat.stream_message(message):
                if isinstance(ev, TextDelta):
                    full.append(ev.content)
                    yield _sse({"type": "delta", "content": ev.content})
                elif isinstance(ev, StreamDone):
                    break
        except Exception as e:
            logger.error(f"Caption generation failed: {e}")
            yield _sse({"type": "error", "detail": "Caption writer is unavailable. Please try again."})
            return

        result = parse_output("".join(full))
        await deps.db.caption_generations.insert_one({
            "generation_id": generation_id,
            "user_id": user.user_id,
            "tone": payload.tone,
            "draft": payload.draft,
            "used_image": bool(image_b64),
            "model": CLAUDE_MODEL,
            "raw": "".join(full),
            **result,
            "created_at": datetime.now(timezone.utc).isoformat(),
        })
        yield _sse({"type": "done", "generation_id": generation_id, **result})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
