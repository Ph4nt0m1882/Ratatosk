from fastapi import APIRouter

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("", include_in_schema=False)
@router.get("/")
def health():
    return {
        "status": "ok",
    }


@router.get("/ready")
def readiness():
    return {
        "status_api": "ok",
    }
