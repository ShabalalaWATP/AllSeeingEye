"""Offline protocol checks: no runtime downloads or benchmark execution."""

import json
import sys
import tempfile
import unittest
from pathlib import Path, PurePosixPath
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kan81_inputs as inputs
import kan81_observe as observer
from kan81_process import clean_env


def result_text():
    row = {
        "totalMedianMs": 20,
        "totalMaxMs": 49.99,
        "mergeMedianMs": 12,
        "reactMedianMs": 8,
        "profilerMedianMs": 7,
        "commitsPerBatch": 1,
    }
    result = {"kan81": {name: dict(row) for name in ("newIds", "existingIds", "mixed")}}
    result["kan81"]["controlLatency"] = {"medianMs": 20, "maxMs": 49.99}
    return (
        json.dumps(result, separators=(",", ":"))
        + "\nTest Files 1 passed (1)\nTests 1 passed (1)\n"
    )


class ObservationTests(unittest.TestCase):
    def test_workflow_binds_the_new_candidate_and_original_baseline(self):
        workflow = (
            Path(__file__).resolve().parents[2]
            / ".github/workflows/kan81-reference.yml"
        )
        refs = [
            line.strip().removeprefix("ref: ")
            for line in workflow.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("ref: ")
        ]
        self.assertEqual(inputs.CANDIDATE, "38c487c93c79464dd0bbd9ed00c491b779a9a437")
        self.assertEqual(inputs.BASELINE, "88164eb99150d5d94367f8257569100684f9e619")
        self.assertEqual(refs[-2:], [inputs.BASELINE, inputs.CANDIDATE])

    def test_candidate_identity_witnesses_actual_files_and_rejects_mutation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "frontend/conflict.ts"
            source.parent.mkdir()
            source.write_text("reviewed", encoding="utf-8")
            pins = {"conflict.ts": inputs.sha(source)}
            with (
                patch.object(inputs, "CANDIDATE_PINS", pins),
                patch.object(
                    inputs, "git", return_value=inputs.CANDIDATE_FRONTEND_TREE
                ),
            ):
                identity = inputs.verify_candidate(root)
                self.assertEqual(
                    identity,
                    {
                        "revision": inputs.CANDIDATE,
                        "frontendTree": inputs.CANDIDATE_FRONTEND_TREE,
                        "files": pins,
                    },
                )
                source.write_text("unreviewed", encoding="utf-8")
                with self.assertRaisesRegex(
                    RuntimeError, "conflict derivation differs"
                ):
                    inputs.verify_candidate(root)

    def test_candidate_tree_mismatch_fails_before_file_read(self):
        with (
            patch.object(inputs, "git", return_value="wrong tree"),
            patch.object(inputs, "sha") as read,
            self.assertRaisesRegex(RuntimeError, "frontend tree differs"),
        ):
            inputs.verify_candidate(Path("/candidate"))
        read.assert_not_called()

    def test_historical_candidate_cannot_be_relabelled_as_the_new_observation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.object(
                    inputs,
                    "git",
                    side_effect=[
                        inputs.BASELINE,
                        "",
                        "435cbdf6aa4e709584046a1eacd128c05ee08408",
                    ],
                ),
                patch.object(inputs, "verify_pins") as pins,
                self.assertRaisesRegex(RuntimeError, "fresh immutable checkout"),
            ):
                inputs.prepare_sources(root / "baseline", root / "candidate")
            pins.assert_not_called()

    def test_candidate_gate_precedes_baseline_overlay(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            baseline, candidate = root / "baseline", root / "candidate"
            manifest = baseline / "frontend/package.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text("historical", encoding="utf-8")
            with (
                patch.object(
                    inputs,
                    "git",
                    side_effect=[inputs.BASELINE, "", inputs.CANDIDATE, ""],
                ),
                patch.object(inputs, "verify_pins"),
                patch.object(
                    inputs,
                    "verify_candidate",
                    side_effect=RuntimeError("input differs"),
                ),
                patch.object(inputs, "sources") as sources,
                self.assertRaisesRegex(RuntimeError, "input differs"),
            ):
                inputs.prepare_sources(baseline, candidate)
            self.assertEqual(manifest.read_text(encoding="utf-8"), "historical")
            sources.assert_not_called()

    def test_retained_v4_negative_console_result_is_not_acceptance(self):
        # Verbatim metric/footer lines from canonical-priority-pair-881-v4/candidate-root.log.
        text = """{"kan81":{"newIds":{"totalMedianMs":43.06,"totalMaxMs":63.78,"mergeMedianMs":19.47,"reactMedianMs":24.49,"profilerMedianMs":23.23,"commitsPerBatch":1},"existingIds":{"totalMedianMs":28.12,"totalMaxMs":32.83,"mergeMedianMs":6.05,"reactMedianMs":21.95,"profilerMedianMs":20.32,"commitsPerBatch":1},"mixed":{"totalMedianMs":41.31,"totalMaxMs":51.3,"mergeMedianMs":17.65,"reactMedianMs":23.43,"profilerMedianMs":22.06,"commitsPerBatch":1},"controlLatency":{"medianMs":29.26,"maxMs":47.15}}}
 Test Files  1 passed (1)
      Tests  1 passed (1)
"""
        observed = observer.metrics(text)
        self.assertEqual(observed["newIds"]["totalMedianMs"], 43.06)
        self.assertEqual(observed["controlLatency"]["maxMs"], 47.15)
        self.assertFalse(observer.targets(observed))

    def test_exact_original_command_has_one_worker_and_no_coverage(self):
        self.assertEqual(
            observer.benchmark_command(PurePosixPath("/runtime/node")),
            [
                "/runtime/node",
                "node_modules/vitest/vitest.mjs",
                "run",
                "src/features/globe/GlobePage.streamBenchmark.test.tsx",
                "--maxWorkers=1",
                "--no-coverage",
            ],
        )

    def test_metrics_and_original_strict_targets(self):
        metrics = observer.metrics(result_text())
        self.assertTrue(observer.targets(metrics))
        metrics["mixed"]["totalMaxMs"] = 50
        self.assertFalse(observer.targets(metrics))
        metrics["mixed"]["totalMaxMs"] = 49
        metrics["controlLatency"]["medianMs"] = 20.01
        self.assertFalse(observer.targets(metrics))

    def test_reject_incomplete_duplicate_and_bad_metric_records(self):
        valid = result_text()
        cases = [
            "RUN v5",
            valid + valid,
            valid.replace("Tests 1 passed (1)", "Tests 1 failed (1)"),
            valid.replace('"mixed":', '"missing":'),
            valid.replace('"maxMs":49.99', '"maxMs":NaN'),
            valid.replace('"medianMs":20', '"medianMs":50'),
            valid.replace('"medianMs":20', '"medianMs":true'),
        ]
        for text in cases:
            with self.subTest(text=text), self.assertRaises(ValueError):
                observer.metrics(text)

    def test_baseline_failure_stops_candidate_and_retains_existing_log(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "baseline.log").write_text("original partial output")
            with (
                patch.object(observer, "run_owned", side_effect=TimeoutError) as run,
                self.assertRaises(TimeoutError),
            ):
                observer.observe(
                    {"baseline": root, "candidate": root},
                    Path("/node"),
                    {"baseline": {}, "candidate": {}},
                    root,
                )
            self.assertEqual(run.call_count, 1)
            self.assertFalse((root / "candidate-metrics.json").exists())
            self.assertEqual(
                (root / "baseline.log").read_text(), "original partial output"
            )

    def test_bad_baseline_metrics_stops_candidate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "baseline.log").write_text("RUN v5")
            with (
                patch.object(observer, "run_owned") as run,
                self.assertRaises(ValueError),
            ):
                observer.observe(
                    {"baseline": root, "candidate": root},
                    Path("/node"),
                    {"baseline": {}, "candidate": {}},
                    root,
                )
            self.assertEqual(run.call_count, 1)

    def test_two_arms_in_fixed_order_retain_metrics_even_when_targets_unmet(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ("baseline", "candidate"):
                (root / f"{name}.log").write_text(
                    result_text().replace('"totalMedianMs":20', '"totalMedianMs":30')
                )
            with patch.object(observer, "run_owned") as run:
                result = observer.observe(
                    {"baseline": root, "candidate": root},
                    Path("/node"),
                    {"baseline": {}, "candidate": {}},
                    root,
                )
            self.assertEqual(
                [call.args[-2:] for call in run.call_args_list],
                [("baseline", 180), ("candidate", 180)],
            )
            self.assertFalse(observer.targets(result["candidate"]))
            self.assertTrue((root / "candidate-metrics.json").exists())

    def test_environment_excludes_credentials_proxies_and_instrumentation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with patch.dict(
                "os.environ",
                {
                    "GH_TOKEN": "secret",
                    "ASE_URL": "private",
                    "NODE_OPTIONS": "--inspect",
                    "CI": "true",
                },
            ):
                env = clean_env(root / "home", root / "tmp", Path("/node/bin/node"))
            self.assertEqual(
                set(env), {"PATH", "HOME", "TMPDIR", "LANG", "TZ", "NO_COLOR"}
            )
            self.assertEqual(env["HOME"], str(root / "home"))

    def test_source_pin_rejects_changed_fixture(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "fixture").write_text("original")
            with patch.object(
                inputs, "PINS", {"fixture": inputs.sha(root / "fixture")}
            ):
                inputs.verify_pins(root)
                (root / "fixture").write_text("changed")
                with self.assertRaises(RuntimeError):
                    inputs.verify_pins(root)

    def test_inventory_detects_version_and_resolution_changes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            packages = root / "node_modules/.pnpm"
            manifest = packages / "test@1/node_modules/test/package.json"
            manifest.parent.mkdir(parents=True)
            manifest.write_text('{"name":"test","version":"1"}')
            (packages / "lock.yaml").write_text("original")
            original = inputs.installed(root)
            manifest.write_text('{"name":"test","version":"2"}')
            self.assertNotEqual(inputs.installed(root), original)
            manifest.write_text('{"name":"test","version":"1"}')
            (packages / "lock.yaml").write_text("changed")
            self.assertNotEqual(inputs.installed(root), original)

    def test_readback_attempts_remaining_checks_after_failure(self):
        with (
            patch.object(observer, "sources", side_effect=OSError),
            patch.object(observer, "installed", return_value={"same": 1}) as read,
            patch.object(observer, "sha", return_value="same"),
        ):
            result = observer.readback(
                {"baseline": Path("/baseline")},
                {"baseline": {"old": "source"}},
                {"baseline": {"same": 1}},
                Path("/node"),
                Path("/pnpm"),
                {"node": "same", "pnpm": "same"},
                {"/control": "same"},
            )
        self.assertEqual(result["baseline-source"]["errorClass"], "OSError")
        self.assertTrue(result["baseline-dependencies"]["verified"])
        self.assertTrue(result["runtime"]["verified"])
        read.assert_called_once()

    def test_readback_reports_unprepared_inputs_explicitly(self):
        with patch.object(observer, "sha", side_effect=FileNotFoundError):
            result = observer.readback(
                {"baseline": Path("/baseline")},
                {},
                {},
                Path("/node"),
                Path("/pnpm"),
                {},
                {},
            )
        self.assertEqual(result["baseline-source"]["unavailable"], "not prepared")
        self.assertFalse(result["runtime"]["verified"])


if __name__ == "__main__":
    unittest.main()
