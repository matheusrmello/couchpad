import subprocess
import unittest
from unittest.mock import patch

from shiftpad_linux.notifications import CountdownNotification


class CountdownNotificationTest(unittest.TestCase):
    def test_countdown_replaces_one_notification_and_cancels_it(self):
        notifier = CountdownNotification()
        with patch("shiftpad_linux.notifications.subprocess.run") as run:
            run.side_effect = [
                subprocess.CompletedProcess([], 0, "42\n", ""),
                subprocess.CompletedProcess([], 0, "42\n", ""),
                subprocess.CompletedProcess([], 0, "", ""),
            ]
            notifier.show(1.8, "HDMI-A-3")
            notifier.show(1.2, "HDMI-A-3")
            notifier.show(0.8, "HDMI-A-3")
            notifier.cancel()

        self.assertEqual(run.call_count, 3)
        self.assertIn("TV em 2 segundos", run.call_args_list[0].args[0])
        self.assertIn("--replace-id=42", run.call_args_list[1].args[0])
        self.assertIn("TV em 1 segundo", run.call_args_list[1].args[0])
        self.assertEqual(run.call_args_list[2].args[0][-1], "42")
        self.assertIsNone(notifier.notification_id)

    def test_success_replaces_countdown_with_completion(self):
        notifier = CountdownNotification()
        with patch("shiftpad_linux.notifications.subprocess.run") as run:
            run.side_effect = [
                subprocess.CompletedProcess([], 0, "7\n", ""),
                subprocess.CompletedProcess([], 0, "7\n", ""),
            ]
            notifier.show(2, "HDMI-A-3")
            notifier.activated()

        self.assertIn("--replace-id=7", run.call_args_list[1].args[0])
        self.assertIn("TV ativada", run.call_args_list[1].args[0])
        self.assertIsNone(notifier.notification_id)


if __name__ == "__main__":
    unittest.main()
