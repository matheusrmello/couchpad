import json
import unittest
from unittest.mock import patch

from shiftpad_linux import audio


class AudioVolumeTest(unittest.TestCase):
    def test_capture_and_restore_preserve_channel_balance(self):
        payload = [{"name": "tv", "volume": {
            "front-left": {"value": 20000}, "front-right": {"value": 40000}}}]
        with patch.object(audio, "run", return_value=json.dumps(payload)):
            saved = audio.capture_volumes()
        with patch.object(audio, "sinks", return_value={"tv"}), patch.object(audio, "run") as run:
            audio.restore_volumes(saved)
            run.assert_called_once_with(["pactl", "set-sink-volume", "tv", "20000", "40000"])

    def test_100_percent_targets_only_tv(self):
        with patch.object(audio, "run") as run:
            audio.set_volume("tv", "100%")
            run.assert_called_once_with(["pactl", "set-sink-volume", "tv", "100%"])

    def test_restore_skips_disconnected_sink(self):
        with patch.object(audio, "sinks", return_value={"desktop"}), patch.object(audio, "run") as run:
            audio.restore_volumes({"tv": [20000, 40000]})
            run.assert_not_called()
