"""The real persistence schema keeps MFA and provider selection metadata intact."""

from datetime import timedelta
from uuid import uuid4

from sqlalchemy import select

from ase.adapters.persistence.acled_credentials import AcledCredentialRow
from ase.adapters.persistence.encryption_rotation import ENCRYPTED_COLUMNS, rotate_encryption_key
from ase.adapters.persistence.firms_credentials import FirmsCredentialRow
from ase.adapters.persistence.mfa_models import MfaChallengeRow
from ase.adapters.persistence.models import LlmProfileRow
from ase.adapters.persistence.totp import AdminTotpRow
from ase.adapters.security.cipher import FernetCipher
from ase.container import Container
from ase.domain.users import User
from test_encryption_rotation import NEW, OLD


async def test_actual_consumers_preserve_enrolment_and_provider_state(
    container: Container, user: User
) -> None:
    cipher = FernetCipher(OLD)
    now = container.clock.now()
    async with container.session_factory() as session:
        session.add_all(
            [
                LlmProfileRow(
                    id=uuid4(),
                    name="rotation",
                    base_url="https://llm.example",
                    model="fixture",
                    api_key_encrypted=cipher.encrypt("llm-key"),
                    api_key_hint="key",
                    roles=[],
                    max_output_tokens=512,
                    temperature=0.2,
                    enabled=True,
                    created_at=now,
                    updated_at=now,
                ),
                AdminTotpRow(
                    user_id=user.id,
                    secret_encrypted=cipher.encrypt("active-totp"),
                    pending_encrypted=cipher.encrypt("pending-totp"),
                    pending_expires_at=now + timedelta(minutes=5),
                    last_step=123,
                ),
                MfaChallengeRow(
                    token_hash="c" * 64,
                    user_id=user.id,
                    security_version=0,
                    purpose="enrol-app",
                    expires_at=now + timedelta(minutes=5),
                    enrollment_required=True,
                    attempts=2,
                    revision=3,
                    pending_encrypted=cipher.encrypt("challenge-secret"),
                ),
                FirmsCredentialRow(
                    id=1,
                    revision=4,
                    active_revision=2,
                    active_encrypted=cipher.encrypt("active-firms"),
                    draft_encrypted=cipher.encrypt("draft-firms"),
                    draft_expires_at=now + timedelta(minutes=5),
                    draft_area="world",
                    test_generation=2,
                    tested_at=now,
                    tested_revision=4,
                    tested_actor=user.id,
                    tested_family=uuid4(),
                    tested_security_version=0,
                ),
                AcledCredentialRow(
                    id=1,
                    refresh_token_encrypted=cipher.encrypt("refresh-token"),
                    environment_fingerprint="f" * 64,
                    updated_at=now,
                ),
            ]
        )
        await session.commit()
    tables = [
        row.__table__
        for row in (
            LlmProfileRow,
            AdminTotpRow,
            MfaChallengeRow,
            FirmsCredentialRow,
            AcledCredentialRow,
        )
    ]
    async with container.engine.connect() as connection:
        before = {
            table.name: dict((await connection.execute(select(table))).mappings().one())
            for table in tables
        }
    assert await rotate_encryption_key(container.engine, OLD, NEW) == 7
    async with container.engine.connect() as connection:
        for table in tables:
            after = dict((await connection.execute(select(table))).mappings().one())
            for column in ENCRYPTED_COLUMNS[table.name]:
                assert FernetCipher(NEW).decrypt(after.pop(column)) == cipher.decrypt(
                    before[table.name].pop(column)
                )
            assert after == before[table.name]
