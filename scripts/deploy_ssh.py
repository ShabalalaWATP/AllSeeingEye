"""Root-owned OpenSSH forced-command entry point. Never evaluates a shell command."""

import os
import re
import sys

from deploy_vps import main


def parse_command(command: str) -> tuple[str, bool]:
    match = re.fullmatch(r"(deploy|check) ([0-9a-f]{40})", command)
    if match is None:
        raise ValueError("Only deploy/check followed by a full Git SHA is allowed.")
    return match[2], match[1] == "check"


if __name__ == "__main__":
    try:
        sha, check_only = parse_command(os.environ.get("SSH_ORIGINAL_COMMAND", ""))
    except ValueError as exc:
        sys.exit(str(exc))
    sys.exit(main(sha, check_only=check_only))
