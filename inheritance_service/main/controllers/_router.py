# mypy: ignore-errors

from fastapi import APIRouter

from . import access_decision, probe, retrieve


router = APIRouter()

router.include_router(probe.router, tags=["probe"])
router.include_router(retrieve.router, tags=["retrieve"])
router.include_router(access_decision.router, tags=["access_decision"])
