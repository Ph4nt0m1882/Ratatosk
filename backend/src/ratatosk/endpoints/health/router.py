from fastapi import APIRouter, Depends

from ratatosk.core.security import get_current_user

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", include_in_schema=False)
@router.get("/")
def health():
    return {
        "status": "ok",
    }


@router.get("/ready", dependencies=[Depends(get_current_user)])
def readiness():
    return {
        "status_api": "ok",
    }
