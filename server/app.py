from fastapi import FastAPI
# Optional CORS:
# from fastapi.middleware.cors import CORSMiddleware

from .firebase import init_firebase
from .storage import ensure_portfolio_seed
from .routes import api

def create_app() -> FastAPI:
    init_firebase()
    ensure_portfolio_seed()

    app = FastAPI(title="UnoClick Backend")
    # Optional: CORS if your Netlify app calls this API
    # import os
    # NETLIFY_ORIGIN = os.getenv("NETLIFY_ORIGIN", "")
    # if NETLIFY_ORIGIN:
    #     app.add_middleware(
    #         CORSMiddleware,
    #         allow_origins=[NETLIFY_ORIGIN],
    #         allow_methods=["*"],
    #         allow_headers=["*"],
    #     )

    app.include_router(api)
    return app

app = create_app()
