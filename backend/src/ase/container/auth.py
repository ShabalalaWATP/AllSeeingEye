"""Authentication composition, including restricted MFA and personal security."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from ase.adapters.persistence.account_sessions import SqlAccountSessionRepository
from ase.adapters.persistence.mfa import SqlMfaRepository
from ase.adapters.persistence.profile import SqlProfileRepository
from ase.adapters.persistence.recovery_codes import SqlRecoveryCodeRepository
from ase.adapters.persistence.totp import SqlTotpRepository
from ase.adapters.security.totp import EncryptedTotpProvider
from ase.application.account.profile import ProfileUseCase
from ase.application.account.session_management import AccountSessionManagement
from ase.application.auth.account_requests import ForgotPasswordUseCase, RequestAccountUseCase
from ase.application.auth.change_password import ChangePasswordUseCase
from ase.application.auth.login import LoginUseCase
from ase.application.auth.mfa import MfaUseCase
from ase.application.auth.mfa_context import MfaContext
from ase.application.auth.mfa_management import MfaManagement
from ase.application.auth.recovery_codes import RecoveryCodesUseCase
from ase.application.auth.refresh import LogoutUseCase, RefreshUseCase
from ase.application.auth.sessions import SessionFactory
from ase.application.auth.set_password import SetPasswordUseCase
from ase.application.auth.totp import TotpUseCase

if TYPE_CHECKING:
    from ase.application.auditing import Auditor
    from ase.application.dto import RateLimits
    from ase.application.ports import (
        Clock,
        EmailSender,
        LinkBuilder,
        PasswordHasher,
        RateLimiter,
        TokenGenerator,
    )
    from ase.application.ports.llm import SecretCipher
    from ase.container.repositories import Repositories


class AuthWiring:
    if TYPE_CHECKING:
        cipher: SecretCipher
        clock: Clock
        hasher: PasswordHasher
        limiter: RateLimiter
        limits: RateLimits
        generator: TokenGenerator
        links: LinkBuilder
        email_sender: EmailSender
        _dummy_hash: str

        def repositories(self, session: AsyncSession) -> Repositories: ...
        def _auditor(self, repos: Repositories) -> Auditor: ...
        def _sessions(self, repos: Repositories) -> SessionFactory: ...

    def mfa(self, session: AsyncSession) -> MfaUseCase:
        r = self.repositories(session)
        return MfaUseCase(
            MfaContext(
                SqlMfaRepository(session),
                SqlTotpRepository(session),
                EncryptedTotpProvider(self.cipher),
                r.users,
                self.hasher,
                self.generator,
                self.email_sender,
                self.clock,
                self.limiter,
                self._auditor(r),
                r.uow,
                r.refresh_tokens,
                self._sessions(r),
                SqlRecoveryCodeRepository(session),
            )
        )

    def mfa_management(self, session: AsyncSession) -> MfaManagement:
        return MfaManagement(self.mfa(session))

    def login(self, session: AsyncSession) -> LoginUseCase:
        r = self.repositories(session)
        return LoginUseCase(
            r.users, self.hasher, self._sessions(r), self.clock, self.limiter, self.limits,
            self._auditor(r), r.uow, self._dummy_hash, mfa=self.mfa(session),
        )  # fmt: skip

    def totp(self, session: AsyncSession) -> TotpUseCase:
        r = self.repositories(session)
        return TotpUseCase(
            SqlTotpRepository(session),
            EncryptedTotpProvider(self.cipher),
            self.hasher,
            r.refresh_tokens,
            self.clock,
            self.limiter,
            self._auditor(r),
            r.uow,
            r.users,
            SqlMfaRepository(session),
        )

    def refresh(self, session: AsyncSession) -> RefreshUseCase:
        r = self.repositories(session)
        return RefreshUseCase(
            r.users, r.refresh_tokens, self.generator, self._sessions(r), self.clock,
            self._auditor(r), r.uow,
        )  # fmt: skip

    def logout(self, session: AsyncSession) -> LogoutUseCase:
        r = self.repositories(session)
        return LogoutUseCase(r.refresh_tokens, self.generator, self.clock, self._auditor(r), r.uow)

    def request_account(self, session: AsyncSession) -> RequestAccountUseCase:
        r = self.repositories(session)
        return RequestAccountUseCase(
            r.users, r.requests, self.clock, self.limiter, self.limits, self._auditor(r), r.uow
        )

    def forgot_password(self, session: AsyncSession) -> ForgotPasswordUseCase:
        r = self.repositories(session)
        return ForgotPasswordUseCase(
            r.users, r.password_tokens, self.generator, self.links, self.email_sender, self.clock,
            self.limiter, self.limits, self._auditor(r), r.uow,
        )  # fmt: skip

    def set_password(self, session: AsyncSession) -> SetPasswordUseCase:
        r = self.repositories(session)
        return SetPasswordUseCase(
            r.users, r.password_tokens, r.refresh_tokens, self.hasher, self.generator, self.clock,
            self.limiter, self.limits, self._auditor(r), r.uow,
        )  # fmt: skip

    def change_password(self, session: AsyncSession) -> ChangePasswordUseCase:
        r = self.repositories(session)
        return ChangePasswordUseCase(
            r.users, r.password_tokens, r.refresh_tokens, self.hasher, self.totp(session),
            self.clock, self.limiter, self._auditor(r), r.uow, self.mfa_management(session),
        )  # fmt: skip

    def profile(self, session: AsyncSession) -> ProfileUseCase:
        r = self.repositories(session)
        return ProfileUseCase(
            r.users,
            SqlProfileRepository(session),
            self._auditor(r),
            r.uow,
            r.refresh_tokens,
            self.clock,
        )

    def account_sessions(self, session: AsyncSession) -> AccountSessionManagement:
        r = self.repositories(session)
        return AccountSessionManagement(
            r.users,
            r.refresh_tokens,
            SqlAccountSessionRepository(session),
            self.clock,
            self._auditor(r),
            r.uow,
        )

    def recovery_codes(self, session: AsyncSession) -> RecoveryCodesUseCase:
        return RecoveryCodesUseCase(self.mfa(session))
