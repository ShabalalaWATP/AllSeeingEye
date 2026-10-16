"""Synthetic terminal records for retention boundary and backlog tests."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import func, select

from ase.adapters.persistence.mfa_models import MfaChallengeRow
from ase.adapters.persistence.models import AccountRequestRow, PasswordTokenRow, RefreshTokenRow
from ase.adapters.persistence.session_activity import RefreshFamilyActivityRow
from ase.adapters.persistence.token_families import RefreshFamilyRevocationRow
from ase.adapters.persistence.web_push_models import PushDeliveryRow, PushDeviceRow


def password(user, deadline, *, used=None):
    return PasswordTokenRow(
        id=uuid4(),
        user_id=user.id,
        token_hash=uuid4().hex,
        purpose="reset",
        expires_at=deadline,
        used_at=used,
        created_at=deadline - timedelta(days=1),
    )


def challenge(user, deadline, *, consumed=None):
    return MfaChallengeRow(
        token_hash=uuid4().hex,
        user_id=user.id,
        security_version=0,
        purpose="login",
        expires_at=deadline,
        enrollment_required=True,
        attempts=0,
        revision=0,
        code_hash="synthetic-code-hash",
        pending_encrypted="synthetic-enrolment",
        consumed_at=consumed,
    )


def request(deadline, *, status="approved"):
    return AccountRequestRow(
        id=uuid4(),
        email="synthetic@example.invalid",
        display_name="Synthetic",
        reason="Synthetic request",
        status=status,
        decided_at=deadline,
        created_at=deadline - timedelta(days=1),
    )


def refresh(user, expiry, *, family=None, revoked=None):
    return RefreshTokenRow(
        id=uuid4(),
        user_id=user.id,
        token_hash=uuid4().hex,
        family_id=family or uuid4(),
        issued_at=expiry - timedelta(days=14),
        expires_at=expiry,
        revoked_at=revoked,
        mfa_verified=False,
    )


async def seed(container, *rows):
    async with container.session_factory() as session:
        session.add_all(rows)
        await session.commit()


async def count(container, model):
    async with container.session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model))


async def push_family(container, user, expiry, receipts):
    token = refresh(user, expiry)
    device = PushDeviceRow(
        id=uuid4(),
        user_id=user.id,
        family_id=token.family_id,
        security_version=0,
        endpoint_hash=uuid4().hex,
        encrypted_subscription="synthetic-encrypted-subscription",
        created_at=expiry - timedelta(days=1),
        next_check_at=expiry,
    )
    await seed(container, token, device)
    await seed(
        container,
        RefreshFamilyActivityRow(
            family_id=token.family_id, user_id=user.id, last_activity_at=expiry
        ),
        RefreshFamilyRevocationRow(family_id=token.family_id, revoked_at=expiry),
        *[
            PushDeliveryRow(
                id=uuid4(),
                device_id=device.id,
                alert_id=uuid4(),
                state="sent",
                created_at=expiry,
                updated_at=expiry,
            )
            for _ in range(receipts)
        ],
    )
    return token, device
