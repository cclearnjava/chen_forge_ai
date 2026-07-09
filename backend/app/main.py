from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.agents import router as agents_router
from app.api.leads import router as leads_router
from app.api.artifacts import router as artifacts_router
from app.api.decisions import router as decisions_router
from app.api.delivery import router as delivery_router
from app.api.customers import router as customers_router
from app.api.opportunities import router as opportunities_router
from app.api.conversations import router as conversations_router
from app.api.workspace_api import router as workspace_router
from app.api.notifications import router as notifications_router
from app.api.services import router as services_router
from app.api.knowledge import router as knowledge_router
from app.db import init_db

app = FastAPI(
    title="ChenForge AI API",
    version="0.1.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:3002"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(leads_router, prefix="/api/v1")
app.include_router(agents_router, prefix="/api/v1")
app.include_router(artifacts_router, prefix="/api/v1")
app.include_router(decisions_router, prefix="/api/v1")
app.include_router(delivery_router, prefix="/api/v1")
app.include_router(customers_router, prefix="/api/v1")
app.include_router(opportunities_router, prefix="/api/v1")
app.include_router(conversations_router, prefix="/api/v1")
app.include_router(workspace_router, prefix="/api/v1")
app.include_router(notifications_router, prefix="/api/v1")
app.include_router(services_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")


@app.on_event("startup")
def on_startup():
    init_db()
