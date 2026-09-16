import unittest
from datetime import datetime, timedelta, timezone

from core.keyhole_powerhouse import (
    InMemorySecretStore,
    KeyholePowerhouse,
    SimpleKeyBox,
)


class FakeSearchAdapter:
    async def execute(self, payload, credential):
        secret = credential.get("api_key", credential.get("access_token", ""))
        return {
            "query": payload["query"],
            "authorization": f"Bearer {secret}",
            "source_urls": ["https://example.com/source"],
            "results": [{"name": "Example Sohar Workshop"}],
        }


class KeyholePowerhouseTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.store = InMemorySecretStore()
        self.keybox = SimpleKeyBox(self.store)
        locker = self.keybox.connect_api_key(
            provider="search_api",
            label="Sohar Discovery",
            api_key="super-secret-test-key",
            allowed_capabilities=["search.public"],
        )
        self.locker_id = locker["locker_id"]
        self.gateway = KeyholePowerhouse(self.keybox)
        self.gateway.register_provider("search_api", FakeSearchAdapter())

    async def test_listing_never_returns_secret(self):
        listing = self.keybox.list_lockers()
        self.assertNotIn("super-secret-test-key", repr(listing))
        self.assertIn("secret_fingerprint", listing[0])

    async def test_open_execute_receipt_and_redaction(self):
        grant = self.gateway.open(
            locker_id=self.locker_id,
            subject_id="sohar_autotechserv_prospects",
            capabilities=["search.public"],
            ttl_seconds=300,
            request_budget=2,
        )
        result = await self.gateway.execute(
            grant_id=grant["grant_id"],
            task_type="public_business_research",
            requested_capability="search.public",
            payload={"query": "automotive workshops Sohar Oman"},
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["receipt"]["authorization_result"], "ALLOWED")
        self.assertEqual(result["result"]["authorization"], "[REDACTED]")
        self.assertNotIn("super-secret-test-key", repr(result))
        self.assertEqual(
            result["receipt"]["source_urls"],
            ["https://example.com/source"],
        )

    async def test_capability_outside_grant_is_denied(self):
        grant = self.gateway.open(
            locker_id=self.locker_id,
            subject_id="sohar_autotechserv_prospects",
            capabilities=["search.public"],
        )
        result = await self.gateway.execute(
            grant_id=grant["grant_id"],
            task_type="send_email",
            requested_capability="email.send",
            payload={"to": "x@example.com"},
        )
        self.assertFalse(result["ok"])
        self.assertIn(
            "capability_not_in_grant",
            result["receipt"]["authorization_result"],
        )

    async def test_revoke_locker_blocks_execution(self):
        grant = self.gateway.open(
            locker_id=self.locker_id,
            subject_id="sohar_autotechserv_prospects",
            capabilities=["search.public"],
        )
        self.keybox.revoke(self.locker_id)
        result = await self.gateway.execute(
            grant_id=grant["grant_id"],
            task_type="public_business_research",
            requested_capability="search.public",
            payload={"query": "Sohar"},
        )
        self.assertFalse(result["ok"])

    async def test_oauth_expiry_moves_locker_to_expired(self):
        oauth = self.keybox.connect_oauth(
            provider="google_drive",
            label="Workspace Read",
            access_token="oauth-access-token",
            allowed_capabilities=["drive.read"],
            account_display="person@example.com",
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )
        refreshed = {x["locker_id"]: x for x in self.keybox.list_lockers()}
        self.assertEqual(refreshed[oauth["locker_id"]]["status"], "EXPIRED")


if __name__ == "__main__":
    unittest.main()
