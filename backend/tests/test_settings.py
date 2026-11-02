import json
import tempfile
import unittest
from pathlib import Path

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete

from ratatosk.app import app
from ratatosk.core.dynamic_settings import (
    DynamicSettingsManager,
    DynamicSettingsUpdate,
    dynamic_settings,
)
from ratatosk.core.security import create_access_token
from ratatosk.db.models import User
from ratatosk.db.session import async_session_maker, engine


class TestDynamicSettingsSuite(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._snapshot = dynamic_settings.data.model_copy(deep=True)
        self.user = User(username="__ut_settings_user__", is_active=True, is_admin=False)
        self.admin = User(
            username="__ut_settings_admin__", is_active=True, is_admin=True
        )

        async with async_session_maker() as session:
            await session.execute(
                delete(User).where(
                    User.username.in_(["__ut_settings_user__", "__ut_settings_admin__"])
                )
            )
            session.add_all([self.user, self.admin])
            await session.commit()
            await session.refresh(self.user)
            await session.refresh(self.admin)

        self.user_headers = {
            "Authorization": f"Bearer {create_access_token(self.user.id)}"
        }
        self.admin_headers = {
            "Authorization": f"Bearer {create_access_token(self.admin.id)}"
        }
        self.client = AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        )

    async def asyncTearDown(self) -> None:
        await self.client.aclose()
        dynamic_settings.update(DynamicSettingsUpdate(**self._snapshot.model_dump()))
        async with async_session_maker() as session:
            await session.execute(
                delete(User).where(User.id.in_([self.user.id, self.admin.id]))
            )
            await session.commit()
        await engine.dispose()

    def test_01_manager_disk_persistence_and_schema_backfill(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            # Partial legacy JSON missing newer fields
            path.write_text(json.dumps({"agent_name": "Muninn"}), encoding="utf-8")

            mgr = DynamicSettingsManager(path)
            self.assertEqual(mgr.agent_name, "Muninn")
            self.assertEqual(mgr.currency, "USD")

            # Verify missing fields were automatically backfilled on disk
            saved_disk = json.loads(path.read_text(encoding="utf-8"))
            self.assertIn("attachment_retention_days_on_delete", saved_disk)

            mgr.update(DynamicSettingsUpdate(currency="eur", expire_attachments_on_archive=True))
            mgr_reloaded = DynamicSettingsManager(path)
            self.assertEqual(mgr_reloaded.currency, "EUR")
            self.assertTrue(mgr_reloaded.expire_attachments_on_archive)

    async def test_02_endpoints_permissions_patch_validation_and_reset(self) -> None:
        # Unauthenticated -> 401
        r_401 = await self.client.get("/settings")
        self.assertEqual(r_401.status_code, 401)

        # Regular user can GET /settings and /settings/currencies
        r_get = await self.client.get("/settings", headers=self.user_headers)
        self.assertEqual(r_get.status_code, 200)
        self.assertIn("agent_name", r_get.json())

        r_curr = await self.client.get("/settings/currencies", headers=self.user_headers)
        self.assertEqual(r_curr.status_code, 200)
        self.assertIn("EUR", r_curr.json())
        self.assertIn("USD", r_curr.json())

        # Regular user forbidden from PATCH and POST /reset -> 403
        r_403 = await self.client.patch(
            "/settings", json={"agent_name": "Nope"}, headers=self.user_headers
        )
        self.assertEqual(r_403.status_code, 403)
        r_403_rst = await self.client.post("/settings/reset", headers=self.user_headers)
        self.assertEqual(r_403_rst.status_code, 403)

        # Admin PATCH with invalid currency -> 422
        r_bad_curr = await self.client.patch(
            "/settings", json={"currency": "ZZZ"}, headers=self.admin_headers
        )
        self.assertEqual(r_bad_curr.status_code, 422)

        # Admin PATCH valid updates -> 200 & reflected immediately
        r_patch = await self.client.patch(
            "/settings",
            json={
                "agent_name": "Huginn",
                "currency": "eur",
                "attachment_retention_days_on_delete": 14,
            },
            headers=self.admin_headers,
        )
        self.assertEqual(r_patch.status_code, 200)
        self.assertEqual(r_patch.json()["agent_name"], "Huginn")
        self.assertEqual(r_patch.json()["currency"], "EUR")
        self.assertEqual(r_patch.json()["attachment_retention_days_on_delete"], 14)

        # Admin POST /reset -> back to defaults
        r_rst = await self.client.post("/settings/reset", headers=self.admin_headers)
        self.assertEqual(r_rst.status_code, 200)
        self.assertEqual(r_rst.json()["agent_name"], "Ratatosk")
        self.assertEqual(r_rst.json()["currency"], "USD")


if __name__ == "__main__":
    unittest.main()

