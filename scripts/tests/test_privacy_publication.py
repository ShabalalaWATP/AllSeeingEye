"""Publication gate tests, using only local content and mocked deployment calls."""

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import deploy_vps
from privacy_publication import (
    PublicationError,
    policy_hash,
    require_publication,
    validate_publication,
)

DIRECTORY = Path(__file__).resolve().parents[2] / "frontend/src/features/public-policy"


def candidate():
    files = {
        path.name: path.read_text(encoding="utf-8")
        for path in DIRECTORY.iterdir()
        if path.is_file()
    }
    notice = json.loads(files["privacy.json"])
    notice["operator"] = dict.fromkeys(
        notice["operator"], "Confirmed installation detail"
    )
    for purpose in notice["purposes"]:
        purpose["lawfulBasis"] = "Confirmed basis and assessment"
    files["privacy.json"] = json.dumps(notice)
    files["service.json"] = json.dumps(
        {
            "terms": "Approved installation terms",
            "businessDisclosure": "Confirmed business disclosures",
            "accessibilityContact": "Confirmed accessibility contact",
        }
    )
    files["approval.json"] = json.dumps(
        {
            "approvedBy": "Operator",
            "approvedOn": "2026-10-10",
            "contentSha256": policy_hash(files),
        }
    )
    return files


class PolicyValidationTests(unittest.TestCase):
    def test_changed_service_wording_requires_fresh_approval(self):
        files = candidate()
        validate_publication(files)
        service = json.loads(files["service.json"])
        service["terms"] = "Changed installation terms"
        files["service.json"] = json.dumps(service)
        with self.assertRaisesRegex(PublicationError, "changed or unapproved"):
            validate_publication(files)

    def test_matching_privacy_approval_cannot_publish_incomplete_service_details(self):
        for key in ("terms", "businessDisclosure", "accessibilityContact"):
            files = candidate()
            service = json.loads(files["service.json"])
            service[key] = None
            files["service.json"] = json.dumps(service)
            approval = json.loads(files["approval.json"])
            approval["contentSha256"] = policy_hash(files)
            files["approval.json"] = json.dumps(approval)
            with self.subTest(key=key), self.assertRaises(PublicationError):
                validate_publication(files)

    def test_current_draft_is_blocked(self):
        files = {
            path.name: path.read_text(encoding="utf-8")
            for path in DIRECTORY.iterdir()
            if path.is_file()
        }
        notice = json.loads(files["privacy.json"])
        notice["operator"]["controllerName"] = None
        files["privacy.json"] = json.dumps(notice)
        with self.assertRaisesRegex(PublicationError, "incomplete"):
            validate_publication(files)

    def test_exact_approved_content_passes_and_any_wording_change_invalidates(self):
        files = candidate()
        validate_publication(files)
        for name in (
            "privacy.json",
            "storage.json",
            "AttributionsPage.tsx",
            "attributions.generated.json",
        ):
            changed = copy.copy(files)
            changed[name] += "\nchanged"
            with self.subTest(name=name), self.assertRaises(PublicationError):
                validate_publication(changed)

    def test_missing_or_placeholder_fields_cannot_be_approved(self):
        for replacement in (None, "TBC", "", "TODO: operator name"):
            files = candidate()
            notice = json.loads(files["privacy.json"])
            notice["operator"]["controllerName"] = replacement
            files["privacy.json"] = json.dumps(notice)
            with (
                self.subTest(replacement=replacement),
                self.assertRaises(PublicationError),
            ):
                validate_publication(files)

    def test_malformed_approval_is_rejected_without_printing_content(self):
        for value in ("secret private input", "null", '{"approvedOn":"invalid"}'):
            files = candidate()
            files["approval.json"] = value
            with self.assertRaises(PublicationError) as caught:
                validate_publication(files)
            self.assertNotIn("secret", str(caught.exception))

    def test_reads_only_candidate_git_blobs_and_refuses_symlink(self):
        files = candidate()
        prefix = "frontend/src/features/public-policy/"
        calls = []

        def git(*args):
            calls.append(args)
            if args[0] == "ls-tree":
                return "\n".join(
                    f"100644 blob {'a' * 40}\t{prefix}{name}" for name in files
                )
            self.assertTrue(args[1].startswith(f"{'b' * 40}:{prefix}"))
            return files[args[1].split(":", 1)[1].removeprefix(prefix)]

        require_publication("b" * 40, git)
        self.assertEqual(calls[0], ("ls-tree", "-r", "b" * 40, "--", prefix))
        with self.assertRaisesRegex(PublicationError, "regular files"):
            require_publication(
                "b" * 40, lambda *args: f"120000 blob {'a' * 40}\t{prefix}privacy.json"
            )

    def test_node_and_python_hash_the_same_content(self):
        script = DIRECTORY.parents[2] / "scripts/privacy-publication.js"
        result = subprocess.run(
            [
                "node",
                "--input-type=module",
                "-e",
                f"import {{policyHash}} from {json.dumps(script.as_uri())}; console.log(policyHash());",
            ],
            capture_output=True,
            text=True,
            check=True,
            timeout=15,
        )
        files = {
            path.name: path.read_text(encoding="utf-8")
            for path in DIRECTORY.iterdir()
            if path.is_file()
        }
        self.assertEqual(result.stdout.strip(), policy_hash(files))

    def test_invalid_dates_are_rejected(self):
        for value in (
            "2026-02-30",
            "0000-01-01",
            "2026-13-01",
            "2026-2-1",
            "not a date",
        ):
            files = candidate()
            approval = json.loads(files["approval.json"])
            approval["approvedOn"] = value
            files["approval.json"] = json.dumps(approval)
            with self.subTest(date=value), self.assertRaises(PublicationError):
                validate_publication(files)


class DeploymentPublicationTests(unittest.TestCase):
    def test_unapproved_release_stops_before_images_or_backup(self):
        with (
            patch.object(deploy_vps, "require_latest"),
            patch.object(deploy_vps, "require_clean"),
            patch.object(deploy_vps, "require_compatible"),
            patch.object(deploy_vps, "git", return_value="a" * 40),
            patch.object(
                deploy_vps,
                "require_publication",
                create=True,
                side_effect=RuntimeError("Public policy approval missing"),
            ) as gate,
            patch.object(deploy_vps, "current_images") as images,
            patch.object(deploy_vps, "backup") as backup,
            patch.object(deploy_vps, "build") as build,
        ):
            with self.assertRaisesRegex(RuntimeError, "Public policy approval missing"):
                deploy_vps.deploy("b" * 40, check_only=True)
            gate.assert_called_once()
            images.assert_not_called()
            backup.assert_not_called()
            build.assert_not_called()


if __name__ == "__main__":
    unittest.main()
