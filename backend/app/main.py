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
from .routes import energy as energy_routes
from .routes import maintenance as maint_routes
from .routes import underwriting as uw_routes
from .routes import cashflow as cf_routes
from .routes import expansion as exp_routes
from .routes import retention as ret_routes
from .beckn import routers as beckn_routes
from .routes import launch as launch_routes


def create_app() -> FastAPI:
    app = FastAPI(title="Eleride Platform Orchestration API", version="0.1.0")

    # CORS
    # CORS: allow explicit origins (includes localhost by default); use regex only if provided
    allow_origins = [str(o) for o in settings.cors_origins]
    allow_regex = settings.cors_origin_regex
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allow_origins,
        allow_origin_regex=allow_regex,
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
    app.include_router(energy_routes.router)
    app.include_router(maint_routes.router)
    app.include_router(uw_routes.router)
    app.include_router(cf_routes.router)
    app.include_router(exp_routes.router)
    app.include_router(ret_routes.router)
    app.include_router(beckn_routes.router)
    app.include_router(launch_routes.router)

    # Avoid 307 redirects by serving both slash and no-slash at root
    @app.get("/")
    def root():
        return {"ok": True, "docs": "/docs"}

    return app


app = create_app()


