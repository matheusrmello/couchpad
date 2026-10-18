import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from shiftpad_linux import audio, discovery
from shiftpad_linux.config import Config


class DiscoveryTest(unittest.TestCase):
    def profile_card(self):
        return {"name": "card", "active_profile": "output:hdmi-stereo",
                "profiles": {"output:hdmi-stereo": {}, "output:hdmi-stereo-extra1": {}},
                "ports": {"tv": {"type": "HDMI", "availability": "available",
                    "properties": {"device.product.name": "SAMSUNG"},
                    "profiles": ["output:hdmi-stereo-extra1"]}}}

    def test_shared_hdmi_card_exposes_tv_profile(self):
        with patch.object(audio, "cards", return_value=[self.profile_card()]), patch.object(audio, "run") as run:
            self.assertTrue(audio.activate_tv_profile("SAMSUNG"))
            run.assert_called_once_with(["pactl", "set-card-profile", "card", "output:hdmi-stereo-extra1"])

    def test_tv_profile_refuses_ambiguous_or_unavailable_ports(self):
        card = self.profile_card()
        with patch.object(audio, "cards", return_value=[card, card]), patch.object(audio, "run") as run:
            self.assertFalse(audio.activate_tv_profile("SAMSUNG"))
            run.assert_not_called()
        card["ports"]["tv"]["availability"] = "not available"
        with patch.object(audio, "cards", return_value=[card]), patch.object(audio, "run") as run:
            self.assertFalse(audio.activate_tv_profile("SAMSUNG"))
            run.assert_not_called()

    def test_hdmi_profile_restored_after_session(self):
        card = self.profile_card()
        card["active_profile"] = "output:hdmi-stereo-extra1"
        with patch.object(audio, "cards", return_value=[card]), patch.object(audio, "run") as run:
            audio.restore_profiles({"card": "output:hdmi-stereo"})
            run.assert_called_once_with(["pactl", "set-card-profile", "card", "output:hdmi-stereo"])

    def test_choose_sink_exposes_tv_while_pc_monitor_remains_active(self):
        with patch.object(audio, "sinks", side_effect=[{"desktop"}, {"desktop", "tv.hdmi"}]), \
             patch.object(audio, "sink_details", return_value=[]), \
             patch.object(audio, "activate_tv_profile", return_value=True) as activate:
            self.assertEqual(audio.choose_sink("", {"desktop"}, "desktop", wait=0, tv_model="SAMSUNG"), "tv.hdmi")
            activate.assert_called_once_with("SAMSUNG")

    def test_edid_identifies_display_model_and_fingerprint(self):
        edid = bytearray(128)
        edid[:8] = b"\x00\xff\xff\xff\xff\xff\xff\x00"
        edid[8:10] = bytes.fromhex("4c2d")  # SAM
        edid[10:12] = (29031).to_bytes(2, "little")
        edid[54:72] = b"\x00\x00\x00\xfc\x00SAMSUNG\n     "
        result = discovery.parse_edid(bytes(edid), {"SAM": "Samsung"})
        self.assertEqual(result["manufacturer"], "Samsung")
        self.assertEqual(result["model"], "SAMSUNG")
        self.assertEqual(result["product_code"], 29031)
        self.assertEqual(result["edid_sha256"], hashlib.sha256(edid).hexdigest())

    def test_audio_matches_tv_model_instead_of_desktop_hdmi(self):
        details = [
            {"name": "alsa_output.desktop.hdmi", "description": "HDMI [27G2G4]", "monitor_name": "27G2G4"},
            {"name": "alsa_output.tv.hdmi", "description": "HDMI [SAMSUNG]", "monitor_name": "SAMSUNG"},
        ]
        self.assertEqual(audio.matching_model(details, "SAMSUNG"), [details[1]])
        with patch("shiftpad_linux.audio.sinks", return_value={x["name"] for x in details}), \
             patch("shiftpad_linux.audio.sink_details", return_value=details):
            self.assertEqual(audio.choose_sink("", {details[0]["name"]}, details[0]["name"],
                                               wait=0, tv_model="SAMSUNG"), details[1]["name"])
            self.assertEqual(audio.choose_sink("alsa_output.old_tv.hdmi", {details[0]["name"]},
                                               details[0]["name"], wait=0, tv_model="SAMSUNG"),
                             details[1]["name"])

    def test_active_session_identifies_sink_when_driver_uses_generic_name(self):
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3")
        tv = {"output": "HDMI-A-3", "connected": True, "enabled": True,
              "model": "SAMSUNG", "label": "SAMSUNG (HDMI-A-3)"}
        sink = {"name": "alsa_output.tv.hdmi", "description": "Digital Stereo (HDMI 2)",
                "monitor_name": "HDMI 1"}
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "session.json"
            path.write_text(json.dumps({"tv_output": "HDMI-A-3", "tv_audio_sink": sink["name"]}))
            with patch("shiftpad_linux.discovery.display_devices", return_value=[tv]), \
                 patch("shiftpad_linux.discovery.audio_devices", return_value=[sink]), \
                 patch("shiftpad_linux.discovery.gamepad_devices", return_value=[]), \
                 patch("shiftpad_linux.discovery.state_path", return_value=path):
                found = discovery.scan(config)
        self.assertEqual(found["tv_audio"], sink)
        self.assertEqual(found["tv_audio_method"], "active-session")

    def test_stale_configured_sink_uses_unique_new_hdmi(self):
        desktop = "alsa_output.desktop.hdmi"
        tv = "alsa_output.tv.hdmi"
        details = [{"name": tv, "description": "Digital Stereo (HDMI 2)",
                    "monitor_name": "HDMI 1"}]
        with patch("shiftpad_linux.audio.sinks", return_value={tv}), \
             patch("shiftpad_linux.audio.sink_details", return_value=details):
            self.assertEqual(audio.choose_sink("alsa_output.old_tv.hdmi", {desktop}, desktop,
                                               wait=0, tv_model="SAMSUNG"), tv)


if __name__ == "__main__":
    unittest.main()
