#!/usr/bin/env python3
"""
Run the FastAPI server for AI Battle Tools.

Usage:
    python run_api.py                    # Run on default port 8000
    python run_api.py --port 8080        # Run on custom port
    python run_api.py --reload           # Run with auto-reload (dev mode)
"""
import argparse
import uvicorn


def main():
    parser = argparse.ArgumentParser(description="Run AI Battle Tools API")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║              AI Battle Tools API Server                      ║
╠══════════════════════════════════════════════════════════════╣
║  Health:                                                     ║
║    GET  /health                  - Health check              ║
║                                                              ║
║  Analyzer:                                                   ║
║    GET  /analyzer/battles        - List battles              ║
║    POST /analyzer/analyze        - Analyze a battle          ║
║                                                              ║
║  Advisor:                                                    ║
║    POST /advisor/start           - Start battle session      ║
║    POST /advisor/action          - Apply skill action        ║
║    POST /advisor/accept-recommendation - Accept AI choice    ║
║    POST /advisor/play-turn       - Action + advance turn     ║
║    POST /advisor/next-turn       - Advance to next turn      ║
║                                                              ║
║  Documentation:                                              ║
║    http://{args.host}:{args.port}/docs       - Swagger UI              ║
║    http://{args.host}:{args.port}/redoc      - ReDoc                   ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload
    )


if __name__ == "__main__":
    main()
