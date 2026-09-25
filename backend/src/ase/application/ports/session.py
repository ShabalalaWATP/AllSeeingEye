"""The session re-validation seam that use cases ask the delivery layer for."""

from collections.abc import Awaitable, Callable

# Re-validates the caller's session and raises Unauthenticated once it has ended.
# Use cases call it after private reads or external work, before persisting or
# releasing protected material. The HTTP layer supplies SessionFence.confirm.
SessionCheck = Callable[[], Awaitable[None]]
