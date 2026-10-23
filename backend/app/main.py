from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes.ask import router as ask_router
from backend.app.api.routes.health import router as health_router
from backend.app.api.routes.home import router as home_router
from backend.app.api.routes.macro import router as macro_router
from backend.app.api.routes.relationships import router as relationships_router

app = FastAPI(
    title="MacroLens API",
    version="1.0.0-alpha.1",
    description="Production API boundary for MacroLens Research.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(home_router)
app.include_router(ask_router)
app.include_router(macro_router)
app.include_router(relationships_router)
