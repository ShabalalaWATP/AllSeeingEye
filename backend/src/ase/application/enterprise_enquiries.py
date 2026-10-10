"""Bound public submission volume without disclosing stored enquiry details."""

import hashlib
import json
from dataclasses import asdict
from datetime import UTC
from uuid import uuid4

from ase.application.auditing import Auditor
from ase.application.ports import Clock, RateLimiter, UnitOfWork
from ase.application.ports.enterprise_enquiries import EnquiryRepository, OperatorNoticeSender
from ase.domain.audit import AuditAction
from ase.domain.enterprise_enquiries import EnquiryDetails, EnquiryStatus, EnterpriseEnquiry
from ase.domain.errors import RateLimited


class SubmitEnquiry:
    def __init__(
        self,
        repository: EnquiryRepository,
        notices: OperatorNoticeSender,
        limiter: RateLimiter,
        clock: Clock,
        auditor: Auditor,
        uow: UnitOfWork,
    ) -> None:
        self.repository, self.notices, self.limiter = repository, notices, limiter
        self.clock, self.auditor, self.uow = clock, auditor, uow

    async def execute(
        self, details: EnquiryDetails, client_key: str, *, honeypot: str = ""
    ) -> None:
        ip_key = hashlib.sha256(client_key.encode()).hexdigest()
        retry = self.limiter.hit(f"enquiry:ip:{ip_key}", 3, 3600)
        if retry is not None:
            raise RateLimited(retry)
        if honeypot:
            return
        email_key = hashlib.sha256(details.email.encode()).hexdigest()
        for key, limit in ((f"enquiry:email:{email_key}", 2), ("enquiry:global", 50)):
            retry = self.limiter.hit(key, limit, 86400)
            if retry is not None:
                raise RateLimited(retry)
        now = self.clock.now()
        content = json.dumps(asdict(details), sort_keys=True, ensure_ascii=True)
        submission_key = hashlib.sha256(
            (now.astimezone(UTC).date().isoformat() + content).encode()
        ).hexdigest()
        enquiry = EnterpriseEnquiry(uuid4(), details, EnquiryStatus.NEW, now, now)
        if not await self.repository.add_once(enquiry, submission_key):
            await self.uow.rollback()
            return
        await self.auditor.record(AuditAction.ENQUIRY_SUBMITTED, subject=str(enquiry.id))
        await self.uow.commit()
        # Commit private storage before external I/O. A failed notification never loses the enquiry.
        await self.notices.send_operator_notice(
            f"Enquiry reference: {enquiry.id}\nName: {details.name}\nEmail: {details.email}\n"
            f"Organisation: {details.organisation}\nRole: {details.role}\n"
            f"Deployment: {details.deployment_interest}\n"
            f"Expected users: {details.expected_users}\n\n"
            f"{details.message}"
        )
