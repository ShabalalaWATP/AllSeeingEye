"""Selection weights and exact manifest refusal, without collecting the app."""

import copy
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native_shard_manifest as manifest


def inputs():
    return {
        "source": {"head": "a" * 40, "files": {"backend/tests/test_a.py": "b" * 64}},
        "runtime": {
            "implementation": "CPython",
            "python": "3.13 example",
            "executable_sha256": "c" * 64,
            "packages": [["pytest", "9.0.0"]],
        },
    }


def lanes():
    return {
        "parallel": [
            "tests/test_a.py::test_a[one]",
            "tests/test_a.py::test_a[two]",
            "tests/test_b.py::test_b",
            "tests/test_mixed.py::test_ordinary",
        ],
        "serial": ["tests/test_mixed.py::test_race", "tests/test_migration.py::test_upgrade"],
    }


class ManifestTests(unittest.TestCase):
    def test_missing_git_refuses_before_starting_a_source_read_process(self):
        with (
            patch.object(manifest.shutil, "which", return_value=None),
            patch.object(manifest.subprocess, "run") as run,
            self.assertRaisesRegex(ValueError, "Git is required"),
        ):
            manifest._git(Path("unused"), "rev-parse", "HEAD")
        run.assert_not_called()

    def test_complete_disjoint_stable_partition_keeps_files_and_parameters(self):
        plan = manifest.make_plan(lanes(), 2, inputs())
        self.assertEqual(manifest.validate_plan(plan), plan)
        for lane, values in lanes().items():
            shards = plan["lanes"][lane]["shards"]
            flat = [item for shard in shards for item in shard]
            self.assertEqual(sorted(flat), sorted(values))
            self.assertEqual(len(flat), len(set(flat)))
            owners = {}
            for index, shard in enumerate(shards):
                for nodeid in shard:
                    owners.setdefault(manifest.node_file(nodeid), set()).add(index)
            self.assertTrue(all(len(owner) == 1 for owner in owners.values()))
            self.assertEqual(shards, manifest.partition(list(reversed(values)), 2))
        self.assertNotEqual(
            manifest.node_file(lanes()["serial"][0]),
            manifest.node_file(lanes()["serial"][1]),
        )

    def test_db_free_source_addition_cannot_reassign_selected_cases(self):
        before = manifest.make_plan(lanes(), 2, inputs())
        changed = inputs()
        changed["source"]["files"]["backend/tests/test_new_pure_guard.py"] = "d" * 64
        after = manifest.make_plan(lanes(), 2, changed)
        self.assertEqual(before["lanes"], after["lanes"])
        self.assertNotEqual(before["identity"], after["identity"])

    def test_new_selected_parameter_is_retained_and_counts_as_positive_weight(self):
        values = lanes()
        values["parallel"].append("tests/test_b.py::test_new[skipped-on-platform]")
        plan = manifest.make_plan(values, 2, inputs())
        self.assertEqual(plan["weight"], "selected-case-count")
        self.assertEqual([len(shard) for shard in plan["lanes"]["parallel"]["shards"]], [3, 2])
        self.assertIn(values["parallel"][-1], plan["lanes"]["parallel"]["ids"])

    def test_invalid_counts_ids_and_overlapping_lanes_fail(self):
        for count in (0, -1, True, 65, 1.5, 3):
            with self.subTest(count=count), self.assertRaises(ValueError):
                manifest.make_plan(lanes(), count, inputs())
        for value in (
            [],
            ["../test_a.py::test_a"],
            ["tests/a.py\n--pdb::x"],
            ["tests/a.py"],
            ["tests\\a.py::x"],
            [None],
            ["tests/a.py::x"] * 2,
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                manifest.partition(value, 1)
        overlapping = lanes()
        overlapping["serial"].append(overlapping["parallel"][0])
        with self.assertRaisesRegex(ValueError, "disjoint"):
            manifest.make_plan(overlapping, 2, inputs())

    def test_corrupt_partitions_missing_extra_duplicate_and_expression_are_refused(self):
        original = manifest.make_plan(lanes(), 2, inputs())
        changes = [
            lambda plan: plan["lanes"]["parallel"]["shards"][0].pop(),
            lambda plan: plan["lanes"]["parallel"]["shards"][0].append("tests/new.py::x"),
            lambda plan: plan["lanes"]["parallel"]["shards"][0].append(lanes()["parallel"][0]),
            lambda plan: plan["lanes"]["serial"].update(expression="db"),
            lambda plan: plan.update(weight="full-suite-durations"),
            lambda plan: plan.update(version=True),
            lambda plan: plan["identity"]["runtime"].update(executable_sha256="unknown"),
            lambda plan: plan["identity"]["source"].update(head="unknown"),
        ]
        for change in changes:
            plan = copy.deepcopy(original)
            change(plan)
            with self.subTest(change=change), self.assertRaises(ValueError):
                manifest.validate_plan(plan)

    def test_json_digest_rejects_even_internally_consistent_omission(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "manifest.json"
            original = manifest.make_plan(lanes(), 1, inputs())
            target.write_text(json.dumps(original), encoding="utf-8")
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            self.assertEqual(manifest.read_plan(target, digest), original)
            fewer = lanes()
            fewer["parallel"].pop()
            target.write_text(json.dumps(manifest.make_plan(fewer, 1, inputs())), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "upstream digest"):
                manifest.read_plan(target, digest)
            target.write_text('{"version":1,"version":1}', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                manifest.read_plan(target, hashlib.sha256(target.read_bytes()).hexdigest())

    def test_source_and_installed_runtime_drift_is_refused(self):
        plan = manifest.make_plan(lanes(), 2, inputs())
        for boundary in ("head", "files", "packages", "python", "executable_sha256"):
            current = inputs()
            branch = "source" if boundary in {"head", "files"} else "runtime"
            current[branch][boundary] = "changed"
            with (
                patch.object(manifest, "identity", return_value=current),
                self.assertRaises(ValueError),
            ):
                manifest.require_identity(plan, Path("unused"))
        for actual in (
            [],
            lanes()["parallel"][:-1],
            [*lanes()["parallel"], "tests/new.py::x"],
            [*lanes()["parallel"], lanes()["parallel"][0]],
        ):
            with self.subTest(actual=actual), self.assertRaises(ValueError):
                manifest.require_ids(sorted(lanes()["parallel"]), actual)

    def test_source_witness_includes_ignored_python_but_not_runtime_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tests = root / "backend/tests"
            tests.mkdir(parents=True)
            source = tests / "test_a.py"
            source.write_text("original", encoding="utf-8")
            (root / "backend/.test-phases.jsonl").write_text("runtime", encoding="utf-8")

            def git(_root, *arguments):
                return b"a" * 40 if arguments[0] == "rev-parse" else b""

            with patch.object(manifest, "_git", side_effect=git):
                before = manifest.source_identity(root)
                self.assertEqual(list(before["files"]), ["backend/tests/test_a.py"])
                source.write_text("changed", encoding="utf-8")
                self.assertNotEqual(manifest.source_identity(root), before)
                (tests / "test_extra.py").write_text("extra", encoding="utf-8")
                self.assertEqual(len(manifest.source_identity(root)["files"]), 2)


if __name__ == "__main__":
    unittest.main()
