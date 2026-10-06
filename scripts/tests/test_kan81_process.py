"""Mock Linux acknowledgement/cleanup, without starting child workloads."""

import json
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import kan81_process as owned


class Clock:
    def __init__(self):
        self.now = 0.0

    def read(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class ProcessTests(unittest.TestCase):
    def assert_creation_interruption(self, interrupted_signal):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            previous = signal.getsignal(interrupted_signal)
            process = SimpleNamespace(pid=789, wait=lambda timeout: 0)

            def spawn(*_args, **_kwargs):
                signal.getsignal(interrupted_signal)(interrupted_signal, None)
                return process

            with (
                patch.object(owned.signal, "SIGKILL", 9, create=True),
                patch.object(owned.subprocess, "Popen", side_effect=spawn),
                patch.object(owned, "exited_without_reaping", return_value=True),
                patch.object(owned, "group_present", return_value=False),
                patch.object(owned, "signal_group") as send,
                self.assertRaises(InterruptedError),
            ):
                owned.run_owned(["/node"], root, {}, root, "arm", 1)
            self.assertEqual(
                [call.args for call in send.call_args_list],
                [(789, signal.SIGTERM), (789, 9)],
            )
            self.assertEqual(signal.getsignal(interrupted_signal), previous)
            receipt = json.loads((root / "arm-receipt.json").read_text())
            self.assertEqual(receipt["pid"], 789)
            self.assertFalse(receipt["completed"])
            self.assertTrue(receipt["groupAbsent"])
            self.assertEqual(receipt["failureClass"], "InterruptedError")
            self.assertEqual(receipt["deferredSignals"], [interrupted_signal])

    def test_sigterm_inside_successful_creation_cleans_registered_group(self):
        self.assert_creation_interruption(signal.SIGTERM)

    def test_sigint_inside_successful_creation_cleans_registered_group(self):
        self.assert_creation_interruption(signal.SIGINT)

    def test_signal_and_creation_failure_restore_handlers_without_claiming_a_pid(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            previous = signal.getsignal(signal.SIGTERM)

            def fail(*_args, **_kwargs):
                signal.getsignal(signal.SIGTERM)(signal.SIGTERM, None)
                raise OSError("creation failed")

            with (
                patch.object(owned.subprocess, "Popen", side_effect=fail),
                patch.object(owned, "signal_group") as send,
                self.assertRaises(OSError),
            ):
                owned.run_owned(["/node"], root, {}, root, "arm", 1)
            send.assert_not_called()
            self.assertEqual(signal.getsignal(signal.SIGTERM), previous)
            receipt = json.loads((root / "arm-receipt.json").read_text())
            self.assertNotIn("pid", receipt)
            self.assertFalse(receipt["completed"])
            self.assertEqual(receipt["deferredSignals"], [signal.SIGTERM])

    def exercise(self, root, *, timeout=False, remains=False, interrupted=False):
        clock = Clock()
        stopped = {"value": not timeout}
        signals = []

        def send(pid, kind):
            signals.append((pid, kind))
            stopped["value"] = True

        def wait(timeout):
            self.assertGreater(timeout, 0)
            self.assertLessEqual(timeout, 15)
            return 0

        process = SimpleNamespace(pid=456, wait=wait)
        with (
            patch.object(owned.signal, "SIGKILL", 9, create=True),
            patch.object(owned.subprocess, "Popen", return_value=process) as spawn,
            patch.object(
                owned,
                "exited_without_reaping",
                side_effect=(
                    [InterruptedError(), True]
                    if interrupted
                    else lambda _: stopped["value"]
                ),
            ),
            patch.object(owned, "signal_group", side_effect=send),
            patch.object(owned, "group_present", return_value=remains),
            patch.object(owned.time, "monotonic", side_effect=clock.read),
            patch.object(owned.time, "sleep", side_effect=clock.sleep),
        ):
            try:
                receipt = owned.run_owned(
                    ["/node", "test"], root, {"HOME": str(root)}, root, "arm", 1
                )
            finally:
                self.assertEqual(
                    signals, [(456, signal.SIGTERM), (456, signal.SIGKILL)]
                )
                self.assertTrue(spawn.call_args.kwargs["start_new_session"])
                self.assertNotIn("shell", spawn.call_args.kwargs)
        return receipt

    def test_normal_exit_acknowledges_and_reaps_owned_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = self.exercise(Path(temporary))
            self.assertTrue(receipt["completed"])
            self.assertTrue(receipt["groupAbsent"])
            self.assertEqual(receipt["exit"], 0)

    def test_timeout_retained_even_when_cleanup_exits_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(TimeoutError):
                self.exercise(root, timeout=True)
            receipt = json.loads((root / "arm-receipt.json").read_text())
            self.assertFalse(receipt["completed"])
            self.assertEqual(receipt["failureClass"], "TimeoutError")
            self.assertTrue(receipt["groupAbsent"])

    def test_interruption_still_cleans_group_and_preserves_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(InterruptedError):
                self.exercise(root, interrupted=True)
            self.assertEqual(
                json.loads((root / "arm-receipt.json").read_text())["failureClass"],
                "InterruptedError",
            )

    def test_remaining_group_prevents_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(RuntimeError):
                self.exercise(root, remains=True)
            receipt = json.loads((root / "arm-receipt.json").read_text())
            self.assertFalse(receipt["completed"])
            self.assertFalse(receipt["groupAbsent"])
            self.assertEqual(receipt["cleanupFailureClass"], "RuntimeError")

    def test_spawn_failure_retains_receipt_without_group_signals(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with (
                patch.object(owned.subprocess, "Popen", side_effect=OSError),
                patch.object(owned, "signal_group") as send,
                self.assertRaises(OSError),
            ):
                owned.run_owned(["/node"], root, {}, root, "arm", 1)
            send.assert_not_called()
            self.assertEqual(
                json.loads((root / "arm-receipt.json").read_text())["failureClass"],
                "OSError",
            )

    def test_existing_log_is_never_overwritten_or_relaunched(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "arm.log").write_text("original")
            with (
                patch.object(owned.subprocess, "Popen") as spawn,
                self.assertRaises(FileExistsError),
            ):
                owned.run_owned(["/node"], root, {}, root, "arm", 1)
            spawn.assert_not_called()
            self.assertEqual((root / "arm.log").read_text(), "original")


if __name__ == "__main__":
    unittest.main()
