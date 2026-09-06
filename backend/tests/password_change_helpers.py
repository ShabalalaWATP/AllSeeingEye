"""Outstanding link fixtures for account credential transition tests."""

from datetime import timedelta
from uuid import uuid4

from ase.container import Container
from ase.domain.tokens import PasswordToken, TokenPurpose
from ase.domain.users import User

# Synthetic password used only by isolated account fixtures, never an operator credential.
NEW_PASSWORD = "Revised-Observatory-Passphrase-2026"  # gitleaks:allow


async def outstanding_link(
    container: Container,
    user: User,
    purpose: TokenPurpose = TokenPurpose.RESET,
) -> str:
    secret = container.generator.new_secret()
    now = container.clock.now()
    async with container.session_factory() as session:
        await container.repositories(session).password_tokens.add(
            PasswordToken(
                id=uuid4(),
                user_id=user.id,
                token_hash=container.generator.hash(secret),
                purpose=purpose,
                expires_at=now + timedelta(hours=1),
                used_at=None,
                created_at=now,
            )
        )
        await session.commit()
    return secret
