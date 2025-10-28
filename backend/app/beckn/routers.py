from fastapi import APIRouter, Request
from pydantic import BaseModel
from typing import Any, Dict
import time
from ..routes.launch import list_launch_stores, launch_plan


router = APIRouter(prefix="/beckn", tags=["beckn"])


class BecknContext(BaseModel):
    domain: str | None = None
    country: str | None = None
    city: str | None = None
    action: str | None = None
    bap_id: str | None = None
    bap_uri: str | None = None
    bpp_id: str | None = None
    bpp_uri: str | None = None
    transaction_id: str | None = None
    message_id: str | None = None
    timestamp: str | None = None


def _ctx(action: str) -> Dict[str, Any]:
    return {
        "domain": "nic2004:60232",
        "country": "IND",
        "city": "*",
        "action": action,
        "bpp_id": "eleride-bpp",
        "bpp_uri": "http://localhost:8000/beckn",
        "transaction_id": str(int(time.time()*1000)),
        "message_id": str(int(time.time()*1000)+1),
        "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
    }


@router.post("/bpp/search")
async def bpp_search(req: Request):
    body = await req.json()
    # Build a minimal Beckn catalog from launch-ready stores
    providers: list[dict[str, Any]] = []
    try:
        stores = list_launch_stores()
        for s in stores:
            if s.readiness_score < 60:
                continue
            try:
                plan = launch_plan(s.store)
                items = []
                for sh in plan.get("staffing",{}).get("shifts", []):
                    items.append({
                        "id": f"{s.store}:{sh['name']}",
                        "descriptor": {"name": f"{s.store} - {sh['name']}"},
                        "tags": {"riders": sh.get('riders')}
                    })
                if items:
                    providers.append({"id": s.store, "descriptor": {"name": s.store}, "items": items})
            except Exception:
                continue
    except Exception:
        providers = []
    return {"context": _ctx("on_search"), "message": {"catalog": {"providers": providers}}}


@router.post("/bpp/select")
async def bpp_select(req: Request):
    _ = await req.json()
    return {"context": _ctx("on_select"), "message": {"order": {"status": "PENDING"}}}


@router.post("/bpp/confirm")
async def bpp_confirm(req: Request):
    _ = await req.json()
    return {"context": _ctx("on_confirm"), "message": {"order": {"status": "CONFIRMED"}}}


@router.post("/bpp/status")
async def bpp_status(req: Request):
    _ = await req.json()
    return {"context": _ctx("on_status"), "message": {"order": {"status": "IN_PROGRESS"}}}


