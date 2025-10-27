from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import settings
from .db import Base, engine
from .routes import jobs as jobs_routes
from .routes import estimate as estimate_routes
from .routes import match as match_routes
from .routes import contracts as contracts_routes
from .routes import settlement as settlement_routes
from .routes import zones as zones_routes
from .routes import stores as stores_routes
from .routes import demand as demand_routes
from .routes import demand_insights
from .routes import earnings as earnings_routes
from .routes import analytics_pack
from .routes import hotspots as hotspots_routes
from .routes import credit as credit_routes
from .routes import mg as mg_routes


def create_app() -> FastAPI:
    app = FastAPI(title="Eleride Platform Orchestration API", version="0.1.0")

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(o) for o in settings.cors_origins] if not settings.cors_origin_regex else [],
        allow_origin_regex=settings.cors_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Create tables (best-effort; avoid crash if DB temporarily unreachable)
    try:
        Base.metadata.create_all(bind=engine)
    except Exception:
        pass

    @app.get("/healthz")
    def healthz():
        try:
            with engine.connect() as conn:
                conn.exec_driver_sql("SELECT 1")
            return {"status": "ok"}
        except Exception as e:
            return {"status": "db_error", "detail": str(e)}
    
    # Routers
    app.include_router(jobs_routes.router)
    app.include_router(estimate_routes.router)
    app.include_router(match_routes.router)
    app.include_router(contracts_routes.router)
    app.include_router(settlement_routes.router)
    app.include_router(zones_routes.router)
    app.include_router(stores_routes.router)
    app.include_router(demand_routes.router)
    app.include_router(demand_insights.router)
    app.include_router(earnings_routes.router)
    app.include_router(analytics_pack.router)
    app.include_router(hotspots_routes.router)
    app.include_router(credit_routes.router)
    app.include_router(mg_routes.router)

    return app


app = create_app()


