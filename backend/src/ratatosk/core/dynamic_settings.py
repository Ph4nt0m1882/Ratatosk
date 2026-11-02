import json
import os
from pathlib import Path

from pydantic import BaseModel, Field, field_validator

from ratatosk.core.config import settings


class DynamicSettingsData(BaseModel):
    """Runtime settings persisted in app_dir/settings.json and editable at runtime."""

    agent_name: str = Field(default="Ratatosk", min_length=1, max_length=100)
    currency: str = Field(default="USD", min_length=3, max_length=3)

    # Session & token lifetimes
    access_token_expire_minutes: int = Field(default=15, gt=0)
    refresh_token_expire_days: int = Field(default=15, gt=0)

    # Attachment retention policies
    keep_generated_attachments: bool = True
    attachment_retention_days_on_delete: int = Field(default=7, ge=0)
    expire_attachments_on_archive: bool = False
    attachment_retention_days_on_archive: int = Field(default=30, ge=0)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, v: str) -> str:
        return v.strip().upper()


class DynamicSettingsUpdate(BaseModel):
    agent_name: str | None = Field(default=None, min_length=1, max_length=100)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    access_token_expire_minutes: int | None = Field(default=None, gt=0)
    refresh_token_expire_days: int | None = Field(default=None, gt=0)
    keep_generated_attachments: bool | None = None
    attachment_retention_days_on_delete: int | None = Field(default=None, ge=0)
    expire_attachments_on_archive: bool | None = None
    attachment_retention_days_on_archive: int | None = Field(default=None, ge=0)

    @field_validator("currency")
    @classmethod
    def _normalize_currency(cls, v: str | None) -> str | None:
        return v.strip().upper() if v is not None else None


class DynamicSettingsManager:
    def __init__(self, file_path: Path) -> None:
        self._file_path = file_path
        self._data = self._load()

    def _load(self) -> DynamicSettingsData:
        if self._file_path.exists():
            try:
                raw = json.loads(self._file_path.read_text(encoding="utf-8"))
                data = DynamicSettingsData.model_validate(raw)
                # Backfill any newly introduced default fields on disk
                if set(DynamicSettingsData.model_fields.keys()) - set(raw.keys()):
                    self._save(data)
                return data
            except (ValueError, OSError):
                pass

        data = DynamicSettingsData()
        self._save(data)
        return data

    def _save(self, data: DynamicSettingsData) -> None:
        self._file_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = self._file_path.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps(data.model_dump(), indent=4, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp_path, self._file_path)

    @property
    def data(self) -> DynamicSettingsData:
        return self._data

    def update(self, patch: DynamicSettingsUpdate) -> DynamicSettingsData:
        updates = patch.model_dump(exclude_none=True)
        if updates:
            merged = {**self._data.model_dump(), **updates}
            self._data = DynamicSettingsData.model_validate(merged)
            self._save(self._data)
        return self._data

    def reset(self) -> DynamicSettingsData:
        self._data = DynamicSettingsData()
        self._save(self._data)
        return self._data

    @property
    def agent_name(self) -> str:
        return self._data.agent_name

    @property
    def currency(self) -> str:
        return self._data.currency

    @property
    def access_token_expire_minutes(self) -> int:
        return self._data.access_token_expire_minutes

    @property
    def refresh_token_expire_days(self) -> int:
        return self._data.refresh_token_expire_days

    @property
    def keep_generated_attachments(self) -> bool:
        return self._data.keep_generated_attachments

    @property
    def attachment_retention_days_on_delete(self) -> int:
        return self._data.attachment_retention_days_on_delete

    @property
    def expire_attachments_on_archive(self) -> bool:
        return self._data.expire_attachments_on_archive

    @property
    def attachment_retention_days_on_archive(self) -> int:
        return self._data.attachment_retention_days_on_archive


dynamic_settings = DynamicSettingsManager(settings.settings_file)

