#!/usr/bin/env python3
"""
Shopping Truth Agent — Standalone FastAPI server
No framework dependencies. Runs anywhere with Python 3.10+.

Usage:
    pip install -r requirements.txt
    cp .env.example .env && nano .env   # add your API keys
    python main.py

Endpoints:
    GET  /health          → health check
    POST /analyze         → analyze a product (JSON response)
    GET  /analyze/stream  → analyze with SSE streaming
"""

import os
import asyncio
import json
from typing import Optional
from dotenv import load_dotenv

load_dotenv()  # Load .env file

try:
    from fastapi import FastAPI, Query
    from fastapi.responses import JSONResponse, StreamingResponse
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# ── Load API keys from environment ──
def load_keys() -> dict:
    return {
        # LLM (pick one — auto-detected in priority order)
        "OPENAI_API_KEY":      os.getenv("OPENAI_API_KEY", ""),
        "ANTHROPIC_API_KEY":   os.getenv("ANTHROPIC_API_KEY", ""),
        "GEMINI_API_KEY":      os.getenv("GEMINI_API_KEY", ""),
        "GROK_API_KEY":        os.getenv("GROK_API_KEY", ""),
        "OPENROUTER_API_KEY":  os.getenv("OPENROUTER_API_KEY", ""),
        # Data sources
        "YOUTUBE_API_KEY":     os.getenv("YOUTUBE_API_KEY", ""),
        "RAINFOREST_API_KEY":  os.getenv("RAINFOREST_API_KEY", ""),
        "SCRAPINGDOG_API_KEY": os.getenv("SCRAPINGDOG_API_KEY", ""),
        "SERPAPI_KEY":         os.getenv("SERPAPI_KEY", ""),
        "KEEPA_API_KEY":       os.getenv("KEEPA_API_KEY", ""),
        "REDDIT_CLIENT_ID":    os.getenv("REDDIT_CLIENT_ID", ""),
        "REDDIT_CLIENT_SECRET":os.getenv("REDDIT_CLIENT_SECRET", ""),
    }


# ── CLI mode (no FastAPI needed) ──
async def analyze_cli(url_or_asin: str):
    """Run analysis from CLI — prints output to terminal."""
    import sys
    sys.path.insert(0, ".")
    from agent.executor import execute

    keys = load_keys()
    if not keys.get("OPENAI_API_KEY"):
        print("❌ OPENAI_API_KEY not set in .env")
        return

    print(f"\n🔍 Analyzing: {url_or_asin}\n")
    async for event in execute(url_or_asin, keys):
        if event["event"] == "status":
            print(f"  {event['data']}")
        elif event["event"] == "result":
            print("\n" + "="*60)
            print(event["data"])
            print("="*60)
        elif event["event"] == "error":
            print(f"\n❌ Error: {event['data']}")


# ── FastAPI app ──
if FASTAPI_AVAILABLE:
    app = FastAPI(
        title="Shopping Truth Agent",
        description="Analyze Amazon products across 8+ data sources. Fake review detection, price prediction, coupon finder.",
        version="2.0.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        keys = load_keys()
        configured = {k: bool(v) for k, v in keys.items()}
        active = sum(1 for v in configured.values() if v)
        return {
            "ok": True,
            "service": "shopping-truth-agent",
            "version": "2.0.0",
            "keys_configured": active,
            "keys": configured,
        }

    @app.post("/analyze")
    async def analyze(body: dict):
        """
        Analyze a product URL or ASIN.

        Body: { "url": "https://amazon.in/dp/B0BX4L9143" }
        or:   { "url": "B0BX4L9143" }
        """
        url = body.get("url") or body.get("asin") or ""
        if not url:
            return JSONResponse({"error": "Provide 'url' or 'asin' in request body"}, status_code=400)

        keys = load_keys()
        result_text = ""
        error = None

        import sys
        sys.path.insert(0, ".")
        from agent.executor import execute

        async for event in execute(url, keys):
            if event["event"] == "result":
                result_text = event["data"]
            elif event["event"] == "error":
                error = event["data"]

        if error:
            return JSONResponse({"error": error}, status_code=400)

        return JSONResponse({"result": result_text, "ok": True})

    @app.get("/analyze/stream")
    async def analyze_stream(url: str = Query(..., description="Amazon product URL or ASIN")):
        """
        Stream analysis progress via Server-Sent Events (SSE).
        Each event: data: {"event": "status|result|error", "data": "..."}
        """
        import sys
        sys.path.insert(0, ".")
        from agent.executor import execute

        keys = load_keys()

        async def event_generator():
            async for event in execute(url, keys):
                yield f"data: {json.dumps(event)}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
            }
        )


# ── Entry point ──
if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # CLI mode: python main.py "amazon.in/dp/B0BX4L9143"
        asyncio.run(analyze_cli(sys.argv[1]))
    elif FASTAPI_AVAILABLE:
        # Server mode
        port = int(os.getenv("PORT", 8000))
        print(f"\n🚀 Shopping Truth Agent running on http://localhost:{port}")
        print(f"   POST /analyze  → analyze a product")
        print(f"   GET  /health   → check configured keys\n")
        uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
    else:
        print("❌ FastAPI not installed. Run: pip install fastapi uvicorn")
        print("   Or use CLI mode: python main.py <amazon-url>")
