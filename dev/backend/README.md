# Backend (FastAPI)

Production-ready structure for the AI Battle Tools API.

## Structure

```
dev/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI app (entry module)
│   │   ├── services.py     # Business logic (Analyzer/Advisor)
│   │   └── models.py       # Pydantic request/response schemas
│   └── README.md           # This file
├── run_api.py               # Starts uvicorn -> backend.app.main:app
│
├── battle_advisor/          # Simulation + AI advisor (library)
├── combat_analyzer/         # Log analyzer (library)
└── sourse/                  # Data: CSV + sample battle logs
```

Notes:
- run_api.py points to `backend.app.main:app`.
- The older `dev/api/` module is now superseded by `dev/backend/app/`. Keep it only if you need to diff; otherwise we can remove it to avoid confusion.

## Run

```bash
cd /Users/himanshu.dahiya/Desktop/data/dev
source venv/bin/activate
python run_api.py                # http://localhost:8000
python run_api.py --reload       # dev mode w/ auto-reload
```

## Endpoints

- Health: `GET /health`
- Analyzer: `GET /analyzer/battles`, `POST /analyzer/analyze`
- Advisor: `POST /advisor/start`, `POST /advisor/action`, `POST /advisor/accept-recommendation`, `POST /advisor/play-turn`, `POST /advisor/next-turn`, `GET /advisor/sessions`, `DELETE /advisor/session/{id}`

Detailed docs are in:
- Swagger: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- Text docs: `dev/api/README.md` (can move here if you prefer)

## Conventions

- Keep FastAPI-only code in `backend/app/`.
- Keep reusable domain logic in `battle_advisor/` and `combat_analyzer/`.
- Add new endpoints by:
  1) Defining request/response models in `models.py`
  2) Implementing service logic in `services.py`
  3) Wiring routes in `main.py`

## Next steps (optional)

- Remove legacy `dev/api/` folder to reduce duplication
- Move `dev/api/README.md` to `dev/backend/README.md` (or merge)
- Add tests folder `dev/backend/tests/` for endpoint tests
- Add Dockerfile if you plan to deploy
