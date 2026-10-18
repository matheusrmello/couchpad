import os
import stat
import tempfile
import threading
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from shiftpad_linux.config import Config, STEAM_START, custom_launcher_command, load, save_basic_settings, set_enabled
from shiftpad_linux.gamepad import Watcher, matches_identity
from shiftpad_linux.control import ControlServer, request


class SettingsTest(unittest.TestCase):
    def test_button_press_wakes_already_present_receiver(self):
        import evdev

        watcher = Watcher(Config(desktop_output="DP-2", tv_output="HDMI-A-3"))
        device = Mock()
        device.fd = 42
        device.read.return_value = [SimpleNamespace(
            type=evdev.ecodes.EV_KEY, code=evdev.ecodes.BTN_SOUTH, value=1)]
        watcher.device = device
        watcher.path = "/dev/input/event5"
        watcher.next_scan = float("inf")
        with patch("shiftpad_linux.gamepad.select.select", return_value=([42], [], [])):
            self.assertEqual(watcher.poll(0), (True, True))

    def test_save_preserves_hardware_identity_and_other_commands(self):
        source = Path(__file__).resolve().parent.parent / "config.example.toml"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source.read_text() + "\n# keep this comment\n")
            original = load(path)
            save_basic_settings("extend", 3.5, 4.0, True, path)
            changed = load(path)
            self.assertEqual(changed.mode, "extend")
            self.assertEqual(changed.connect_delay, 3.5)
            self.assertEqual(changed.disconnect_delay, 4.0)
            self.assertEqual(changed.launcher_start, STEAM_START)
            self.assertEqual(changed.tv_edid_sha256, original.tv_edid_sha256)
            self.assertEqual(changed.cec_on, original.cec_on)
            self.assertIn("# keep this comment", path.read_text())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_toggle_is_persistent_and_preserves_other_settings(self):
        source = Path(__file__).resolve().parent.parent / "config.example.toml"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source.read_text())
            original = load(path)
            set_enabled(False, path)
            disabled = load(path)
            self.assertFalse(disabled.enabled)
            self.assertEqual(disabled.tv_edid_sha256, original.tv_edid_sha256)
            self.assertEqual(disabled.launcher_start, original.launcher_start)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            set_enabled(True, path)
            self.assertTrue(load(path).enabled)

    def test_other_launcher_can_be_saved_alongside_steam(self):
        source = Path(__file__).resolve().parent.parent / "config.example.toml"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source.read_text())
            executable = Path(directory) / "My Launcher.AppImage"
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o700)
            save_basic_settings("tv-only", 2, 2, True, path,
                                custom_launcher_path=str(executable),
                                custom_launcher_enabled=True)
            changed = load(path)
            self.assertEqual(changed.launcher_start, STEAM_START)
            self.assertEqual(changed.custom_launcher_path, str(executable))
            self.assertTrue(changed.custom_launcher_enabled)
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            save_basic_settings("tv-only", 2, 2, False, path,
                                custom_launcher_path=str(executable),
                                custom_launcher_enabled=True)
            self.assertEqual(load(path).launcher_start, ())
            self.assertTrue(load(path).custom_launcher_enabled)

    def test_switch_from_other_launcher_to_steam_preserves_saved_program(self):
        source = Path(__file__).resolve().parent.parent / "config.example.toml"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source.read_text())
            executable = Path(directory) / "hydra.AppImage"
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o700)
            save_basic_settings("tv-only", 2, 2, False, path,
                                custom_launcher_path=str(executable),
                                custom_launcher_enabled=True,
                                custom_launcher_args=("--big-picture",))
            save_basic_settings("tv-only", 2, 2, True, path,
                                custom_launcher_path=str(executable),
                                custom_launcher_enabled=False,
                                custom_launcher_args=("--big-picture",))
            changed = load(path)
            self.assertEqual(changed.launcher_start, STEAM_START)
            self.assertFalse(changed.custom_launcher_enabled)
            self.assertEqual(changed.custom_launcher_path, str(executable))

    def test_other_launcher_requires_executable_file_when_enabled(self):
        source = Path(__file__).resolve().parent.parent / "config.example.toml"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source.read_text())
            with self.assertRaisesRegex(ValueError, "executável"):
                save_basic_settings("tv-only", 2, 2, True, path,
                                    custom_launcher_path=str(Path(directory) / "missing"),
                                    custom_launcher_enabled=True)
            self.assertFalse(load(path).custom_launcher_enabled)

    def test_desktop_entry_uses_gio_and_does_not_need_executable_bit(self):
        source = Path(__file__).resolve().parent.parent / "config.example.toml"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source.read_text())
            shortcut = Path(directory) / "My Launcher.desktop"
            shortcut.write_text("[Desktop Entry]\nType=Application\nName=Example\nExec=/usr/bin/true\n")
            save_basic_settings("tv-only", 2, 2, False, path,
                                custom_launcher_path=str(shortcut),
                                custom_launcher_enabled=True)
            self.assertEqual(custom_launcher_command(load(path).custom_launcher_path),
                             ("gio", "launch", str(shortcut)))

    def test_other_launcher_arguments_are_saved_without_shell(self):
        source = Path(__file__).resolve().parent.parent / "config.example.toml"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source.read_text())
            executable = Path(directory) / "hydra.AppImage"
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o700)
            save_basic_settings("tv-only", 2, 2, False, path,
                                custom_launcher_path=str(executable),
                                custom_launcher_enabled=True,
                                custom_launcher_args=("--big-picture",))
            config = load(path)
            self.assertEqual(config.custom_launcher_args, ("--big-picture",))
            self.assertEqual(custom_launcher_command(config.custom_launcher_path,
                                                     config.custom_launcher_args),
                             (str(executable), "--big-picture"))

    def test_custom_launcher_close_setting_requires_direct_executable(self):
        source = Path(__file__).resolve().parent.parent / "config.example.toml"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source.read_text())
            executable = Path(directory) / "hydra.AppImage"
            executable.write_text("#!/bin/sh\nexit 0\n")
            executable.chmod(0o700)
            save_basic_settings("tv-only", 2, 2, False, path,
                                custom_launcher_path=str(executable),
                                custom_launcher_enabled=True,
                                custom_launcher_close=True)
            self.assertTrue(load(path).custom_launcher_close)
            shortcut = Path(directory) / "Hydra.desktop"
            shortcut.write_text("[Desktop Entry]\nType=Application\nExec=/usr/bin/true\n")
            with self.assertRaisesRegex(ValueError, "executável ou AppImage"):
                save_basic_settings("tv-only", 2, 2, False, path,
                                    custom_launcher_path=str(shortcut),
                                    custom_launcher_enabled=True,
                                    custom_launcher_close=True)

    def test_device_selection_persists_without_changing_automation_or_launcher(self):
        source = Path(__file__).resolve().parent.parent / "config.example.toml"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source.read_text())
            original = load(path)
            fingerprint = "a" * 64
            save_basic_settings(original.mode, original.connect_delay,
                                original.disconnect_delay, True, path,
                                tv_output="HDMI-A-1", tv_edid_sha256=fingerprint,
                                tv_sink="alsa_output.card.hdmi-stereo",
                                gamepad_name="8BitDo Ultimate 2",
                                gamepad_vendor_id="2DC8", gamepad_product_id="3106",
                                gamepad_uniq="AA:BB:CC")
            chosen = load(path)
            self.assertEqual((chosen.tv_output, chosen.tv_edid_sha256),
                             ("HDMI-A-1", fingerprint))
            self.assertEqual(chosen.tv_sink, "alsa_output.card.hdmi-stereo")
            self.assertEqual((chosen.gamepad_vendor_id, chosen.gamepad_product_id,
                              chosen.gamepad_uniq), ("2dc8", "3106", "AA:BB:CC"))
            self.assertEqual(chosen.enabled, original.enabled)
            self.assertEqual(chosen.launcher_start, STEAM_START)
            self.assertTrue(matches_identity("8BitDo Ultimate 2 Wireless", "2dc8", "3106",
                                             "AA:BB:CC", chosen))
            self.assertFalse(matches_identity("8BitDo Ultimate 2 Wireless", "2dc8", "3106",
                                              "other", chosen))

    def test_device_selection_rejects_desktop_as_tv_and_partial_controller_ids(self):
        source = Path(__file__).resolve().parent.parent / "config.example.toml"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(source.read_text())
            with self.assertRaisesRegex(ValueError, "TV"):
                save_basic_settings("tv-only", 2, 2, True, path, tv_output="DP-2")
            with self.assertRaisesRegex(ValueError, "controle"):
                save_basic_settings("tv-only", 2, 2, True, path,
                                    gamepad_vendor_id="2dc8", gamepad_product_id="")


class ControlTest(unittest.TestCase):
    def test_same_user_socket_request_and_invalid_command(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "control.sock"
            with ControlServer(path) as server:
                def serve() -> None:
                    deadline = time.monotonic() + 2
                    while time.monotonic() < deadline and len(results) < 5:
                        server.poll(lambda command: {"ok": True, "command": command})
                        time.sleep(0.005)

                results = []
                thread = threading.Thread(target=serve)
                thread.start()
                results.append(request("status", path))
                results.append(request("disable", path))
                results.append(request("enable", path))
                results.append(request("cancel", path))
                results.append(request("invalid", path))
                thread.join(timeout=2)
                self.assertFalse(thread.is_alive())
                self.assertEqual(results[0], {"ok": True, "command": "status"})
                self.assertEqual(results[1]["command"], "disable")
                self.assertEqual(results[2]["command"], "enable")
                self.assertEqual(results[3]["command"], "cancel")
                self.assertFalse(results[4]["ok"])
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
