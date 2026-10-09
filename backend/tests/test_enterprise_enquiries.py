"""Public enquiries are private, bounded and never an account or mailing endpoint."""

import pytest
from sqlalchemy import select

from ase.adapters.persistence.enterprise_enquiries import EnterpriseEnquiryRow
from ase.adapters.persistence.models import AuditLogRow

PAYLOAD = {
    "name": "Example Analyst",
    "email": "analyst@example.com",
    "organisation": "Example",
    "deployment_interest": "on_premises",
    "expected_users": "11_50",
    "message": "Please advise.",
}


class Notices:
    available = True

    def __init__(self):
        self.messages = []

    async def send_operator_notice(self, body):
        self.messages.append(body)
        return True


@pytest.fixture
def enquiries(container):
    container.settings = container.settings.model_copy(
        update={"enterprise_enquiries_enabled": True}
    )
    container.operator_notices = Notices()
    return container


async def test_disabled_route_reveals_nothing(client):
    assert (await client.post("/api/enquiries", json=PAYLOAD)).status_code == 404


async def test_accepted_submission_has_uniform_private_response(client, enquiries):
    result = await client.post("/api/enquiries", json=PAYLOAD)
    assert result.status_code == 202
    assert result.headers["cache-control"] == "no-store"
    assert result.json() == {"message": "Thank you. Your enquiry has been received."}
    assert len(enquiries.operator_notices.messages) == 1
    assert "analyst@example.com" in enquiries.operator_notices.messages[0]


async def test_honeypot_and_duplicate_are_indistinguishable(client, enquiries):
    first = await client.post("/api/enquiries", json={**PAYLOAD, "website": "spam"})
    assert not enquiries.operator_notices.messages
    second = await client.post("/api/enquiries", json=PAYLOAD)
    third = await client.post("/api/enquiries", json=PAYLOAD)
    assert first.status_code == second.status_code == third.status_code == 202
    assert first.json() == second.json() == third.json()
    assert len(enquiries.operator_notices.messages) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("name", ""),
        ("name", "a" * 101),
        ("name", "a\r\nb"),
        ("email", "invalid"),
        ("organisation", "a" * 151),
        ("role", "a\nb"),
        ("message", "a" * 2001),
        ("deployment_interest", "invalid"),
        ("expected_users", "invalid"),
        ("status", "closed"),
    ],
)
async def test_untrusted_fields_rejected(client, enquiries, field, value):
    result = await client.post("/api/enquiries", json={**PAYLOAD, field: value})
    assert result.status_code == 422
    assert not enquiries.operator_notices.messages


async def test_email_rate_limit_returns_retry_after(client, enquiries):
    for _ in range(2):
        assert (await client.post("/api/enquiries", json=PAYLOAD)).status_code == 202
    result = await client.post("/api/enquiries", json=PAYLOAD)
    assert result.status_code == 429
    assert int(result.headers["retry-after"]) > 0


async def test_storage_and_audit_exclude_client_address_and_private_audit_text(client, enquiries):
    result = await client.post(
        "/api/enquiries",
        json={
            **PAYLOAD,
            "name": "  Ex\x00ample\u200b  ",
            "email": "ANALYST@EXAMPLE.COM",
            "message": "First\nSecond\x00",
            "role": "  Analyst  ",
        },
    )
    assert result.status_code == 202
    async with enquiries.session_factory() as session:
        row = (await session.scalars(select(EnterpriseEnquiryRow))).one()
        audit = (await session.scalars(select(AuditLogRow))).one()
        assert row.name == "Example" and row.email == "analyst@example.com"
        assert row.message == "First\nSecond" and row.role == "Analyst"
        assert row.status == "new" and row.created_at == row.updated_at
        assert audit.action == "enquiry.submitted" and audit.subject == str(row.id)
        assert audit.ip is None and audit.details == {}
        assert "ip" not in EnterpriseEnquiryRow.__table__.columns


async def test_ip_limit_applies_across_email_addresses(client, enquiries):
    for index in range(3):
        response = await client.post(
            "/api/enquiries", json={**PAYLOAD, "email": f"user{index}@example.com"}
        )
        assert response.status_code == 202
    assert (await client.post("/api/enquiries", json=PAYLOAD)).status_code == 429


async def test_global_cap_applies_to_an_unseen_client(client, enquiries):
    for _ in range(50):
        assert enquiries.limiter.hit("enquiry:global", 50, 86400) is None
    assert (await client.post("/api/enquiries", json=PAYLOAD)).status_code == 429
    assert not enquiries.operator_notices.messages


async def test_request_size_limit_precedes_storage(client, enquiries):
    response = await client.post("/api/enquiries", json={**PAYLOAD, "message": "x" * 70_000})
    assert response.status_code == 413
    assert not enquiries.operator_notices.messages


async def test_failed_operator_delivery_does_not_lose_submission(client, enquiries):
    class Unavailable:
        available = True

        async def send_operator_notice(self, body):
            return False

    enquiries.operator_notices = Unavailable()
    assert (await client.post("/api/enquiries", json=PAYLOAD)).status_code == 202
    async with enquiries.session_factory() as session:
        assert len((await session.scalars(select(EnterpriseEnquiryRow))).all()) == 1


async def test_public_flag_follows_enquiry_setting(client, enquiries):
    assert (await client.get("/api/site")).json()["enterprise_enquiries_enabled"] is True
