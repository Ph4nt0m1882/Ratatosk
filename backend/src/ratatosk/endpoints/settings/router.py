from fastapi import APIRouter, Depends, HTTPException

from ratatosk.core.currency import currency_manager
from ratatosk.core.dynamic_settings import (
    DynamicSettingsData,
    DynamicSettingsUpdate,
    dynamic_settings,
)
from ratatosk.core.security import get_current_admin, get_current_user

router = APIRouter(
    prefix="/settings",
    tags=["Settings"],
    dependencies=[Depends(get_current_user)],
)


@router.get("")
async def get_settings() -> DynamicSettingsData:
    return dynamic_settings.data


@router.get("/currencies")
async def list_supported_currencies() -> list[str]:
    return sorted(currency_manager.dictionary.get("rates", {}).keys())


@router.patch("", dependencies=[Depends(get_current_admin)])
async def patch_settings(data: DynamicSettingsUpdate) -> DynamicSettingsData:
    if (
        data.currency is not None
        and data.currency not in currency_manager.dictionary.get("rates", {})
    ):
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported ISO 4217 currency code: '{data.currency}'",
        )
    return dynamic_settings.update(data)


@router.post("/reset", dependencies=[Depends(get_current_admin)])
async def reset_settings() -> DynamicSettingsData:
    return dynamic_settings.reset()

