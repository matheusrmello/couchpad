import tempfile
import unittest
import signal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from shiftpad_linux import cli, displays
from shiftpad_linux.config import Config, STEAM_START
from shiftpad_linux.session import Session, _stop_owned_launcher
from shiftpad_linux.system import CommandError


def screen(name, ident, enabled, connected=True, x=0, width=1920):
    return {
        "name": name, "id": ident, "enabled": enabled, "connected": connected,
        "currentModeId": "1", "modes": [{"id": "1"}],
        "pos": {"x": x, "y": 0}, "size": {"width": width, "height": 1080},
        "scale": 1.0, "replicationSource": 0,
    }


class DisplayPlansTest(unittest.TestCase):
    def setUp(self):
        self.config = Config(desktop_output="DP-2", tv_output="HDMI-A-3")
        self.before = {"outputs": [screen("DP-2", 1, True), screen("HDMI-A-3", 2, False, x=1920)]}

    def test_tv_only_enables_target_and_disables_desktop(self):
        plan = displays.switch_plan(self.config, self.before)
        self.assertIn("output.HDMI-A-3.enable", plan)
        self.assertIn("output.DP-2.disable", plan)
        self.assertIn("output.HDMI-A-3.mirror.none", plan)

    def test_extend_uses_desktop_right_edge(self):
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3", mode="extend")
        self.assertIn("output.HDMI-A-3.position.1920,0", displays.switch_plan(config, self.before))

    def test_4k_tv_uses_275_percent_in_all_video_modes(self):
        tv = self.before["outputs"][1]
        tv["modes"][0]["size"] = {"width": 3840, "height": 2160}
        for mode in ("tv-only", "extend", "mirror"):
            config = Config(desktop_output="DP-2", tv_output="HDMI-A-3", mode=mode)
            self.assertIn("output.HDMI-A-3.scale.2.75", displays.switch_plan(config, self.before))

    def test_fullhd_keeps_scale_even_when_4k_mode_is_available(self):
        tv = self.before["outputs"][1]
        tv["scale"] = 1.25
        tv["modes"] = [{"id": "1", "size": {"width": 1920, "height": 1080}},
                       {"id": "2", "size": {"width": 3840, "height": 2160}}]
        self.assertFalse(any(".scale." in arg for arg in displays.switch_plan(self.config, self.before)))

    def test_restore_scale_of_previously_disabled_tv(self):
        self.before["outputs"][1]["scale"] = 1.5
        plan = displays.restore_plan(self.before, self.before, "DP-2")
        self.assertIn("output.HDMI-A-3.scale.1.5", plan)
        self.assertIn("output.HDMI-A-3.disable", plan)

    def test_refuses_unplugged_target_before_mutation(self):
        self.before["outputs"][1]["connected"] = False
        with self.assertRaises(ValueError):
            displays.switch_plan(self.config, self.before)

    def test_refuses_different_panel_on_same_connector(self):
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3", tv_edid_sha256="a" * 64)
        with patch("shiftpad_linux.displays.edid_sha256", return_value="b" * 64):
            with self.assertRaises(ValueError):
                displays.switch_plan(config, self.before)

    def test_restore_skips_unplugged_tv_and_enables_desktop(self):
        current = {"outputs": [screen("DP-2", 1, False), screen("HDMI-A-3", 2, False, False)]}
        plan = displays.restore_plan(self.before, current, "DP-2")
        self.assertIn("output.DP-2.enable", plan)
        self.assertFalse(any("HDMI-A-3" in arg for arg in plan))

    def test_hdr_state_is_reapplied_only_for_capable_active_outputs(self):
        self.before["outputs"][0].update(hdrEnabled=True, wcgEnabled=True, sdrBrightness=240)
        self.before["outputs"][1].update(hdrEnabled=False, wcgEnabled=False)
        after = {"outputs": [screen("DP-2", 1, True), screen("HDMI-A-3", 2, False)]}
        self.assertEqual(displays.hdr_restore_plan(self.before, after), [
            "kscreen-doctor", "output.DP-2.hdr.enable", "output.DP-2.wcg.enable",
            "output.DP-2.sdr-brightness.240",
        ])
        self.assertEqual(displays.hdr_restore_plan(self.before, after, {"HDMI-A-3"}),
                         ["kscreen-doctor"])


class RollbackTest(unittest.TestCase):
    def setUp(self):
        capture = patch("shiftpad_linux.session.audio.capture_profiles", return_value={"card": "desktop"})
        restore = patch("shiftpad_linux.session.audio.restore_profiles")
        capture.start()
        self.restore_profiles = restore.start()
        self.addCleanup(capture.stop)
        self.addCleanup(restore.stop)
        volumes = patch("shiftpad_linux.session.audio.capture_volumes", return_value={})
        restore_volumes = patch("shiftpad_linux.session.audio.restore_volumes")
        volumes.start()
        self.restore_volumes = restore_volumes.start()
        self.addCleanup(volumes.stop)
        self.addCleanup(restore_volumes.stop)

    def test_tv_volume_is_saved_before_setting_100_and_restored_before_hdmi_disables(self):
        before = {"outputs": [screen("DP-2", 1, True), screen("HDMI-A-3", 2, False)]}
        after = {"outputs": [screen("DP-2", 1, False), screen("HDMI-A-3", 2, True)]}
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3")
        with tempfile.TemporaryDirectory() as directory:
            session = Session(Path(directory) / "session.json")
            def set_volume(name, level):
                self.assertEqual((name, level), ("tv", "100%"))
                self.assertEqual(session._load()["audio_volumes"], {"desk": [30000, 30000], "tv": [20000, 25000]})
            with patch("shiftpad_linux.session.displays.capture", side_effect=[before, after, after, before]), \
                 patch("shiftpad_linux.session.displays.apply") as apply, \
                 patch("shiftpad_linux.session.audio.default_sink", return_value="desk"), \
                 patch("shiftpad_linux.session.audio.sinks", return_value={"desk"}), \
                 patch("shiftpad_linux.session.audio.choose_sink", return_value="tv"), \
                 patch("shiftpad_linux.session.audio.capture_volumes", side_effect=[{"desk": [30000, 30000]}, {"tv": [20000, 25000]}]), \
                 patch("shiftpad_linux.session.audio.set_default"), \
                 patch("shiftpad_linux.session.audio.set_volume", side_effect=set_volume) as volume, \
                 patch("shiftpad_linux.session.discovery.read_edid", return_value=None):
                session.activate(config)
                volume.assert_called_once()
                def restore_levels(saved):
                    self.assertEqual(saved["tv"], [20000, 25000])
                    if self.restore_volumes.call_count == 1:
                        self.assertEqual(apply.call_count, 1)
                self.restore_volumes.side_effect = restore_levels
                session.restore()
                self.assertEqual(self.restore_volumes.call_count, 2)

    def test_failed_switch_restores_and_removes_journal(self):
        before = {"outputs": [screen("DP-2", 1, True), screen("HDMI-A-3", 2, False)]}
        current = {"outputs": [screen("DP-2", 1, True), screen("HDMI-A-3", 2, False)]}
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3")
        with tempfile.TemporaryDirectory() as tmp:
            session = Session(Path(tmp) / "session.json")
            with patch("shiftpad_linux.session.displays.capture", side_effect=[before, current, current]), \
                 patch("shiftpad_linux.session.displays.apply", side_effect=[CommandError("falhou"), None]) as apply, \
                 patch("shiftpad_linux.session.audio.default_sink", return_value="old"), \
                 patch("shiftpad_linux.session.audio.sinks", return_value={"old"}), \
                 patch("shiftpad_linux.session.audio.set_default"):
                with self.assertRaises(CommandError):
                    session.activate(config)
                self.assertEqual(apply.call_count, 2)
                self.assertFalse(session.pending())

    def test_incomplete_restore_keeps_journal_for_retry(self):
        before = {"outputs": [screen("DP-2", 1, True), screen("HDMI-A-3", 2, False)]}
        switched = {"outputs": [screen("DP-2", 1, False), screen("HDMI-A-3", 2, True)]}
        with tempfile.TemporaryDirectory() as tmp:
            session = Session(Path(tmp) / "session.json")
            session._save({"display": before, "desktop_output": "DP-2", "audio_sink": ""})
            with patch("shiftpad_linux.session.displays.capture", side_effect=[switched, switched]), \
                 patch("shiftpad_linux.session.displays.apply"):
                with self.assertRaises(RuntimeError):
                    session.restore()
            self.assertTrue(session.pending())

    def test_custom_launcher_opens_alongside_steam(self):
        before = {"outputs": [screen("DP-2", 1, True), screen("HDMI-A-3", 2, False)]}
        after = {"outputs": [screen("DP-2", 1, False), screen("HDMI-A-3", 2, True)]}
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3",
                        launcher_start=STEAM_START, custom_launcher_enabled=True,
                        custom_launcher_path="/tmp/My Launcher.AppImage")
        with tempfile.TemporaryDirectory() as directory:
            session = Session(Path(directory) / "session.json")
            with patch("shiftpad_linux.session.displays.capture", side_effect=[before, after]), \
                 patch("shiftpad_linux.session.displays.apply"), \
                 patch("shiftpad_linux.session.audio.default_sink", return_value="desk"), \
                 patch("shiftpad_linux.session.audio.sinks", return_value={"desk"}), \
                 patch("shiftpad_linux.session.audio.choose_sink", return_value=None), \
                 patch("shiftpad_linux.session.discovery.read_edid", return_value=None), \
                 patch("shiftpad_linux.session.subprocess.Popen") as launch:
                session.activate(config)
            commands = [call.args[0] for call in launch.call_args_list]
            self.assertEqual(commands, [STEAM_START, ("/tmp/My Launcher.AppImage",)])
            self.assertTrue(session.pending())

    def test_disabled_other_launcher_is_not_opened_with_steam(self):
        before = {"outputs": [screen("DP-2", 1, True), screen("HDMI-A-3", 2, False)]}
        after = {"outputs": [screen("DP-2", 1, False), screen("HDMI-A-3", 2, True)]}
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3",
                        launcher_start=STEAM_START, custom_launcher_enabled=False,
                        custom_launcher_path="/tmp/hydra.AppImage")
        with tempfile.TemporaryDirectory() as directory:
            session = Session(Path(directory) / "session.json")
            with patch("shiftpad_linux.session.displays.capture", side_effect=[before, after]), \
                 patch("shiftpad_linux.session.displays.apply"), \
                 patch("shiftpad_linux.session.audio.default_sink", return_value="desk"), \
                 patch("shiftpad_linux.session.audio.sinks", return_value={"desk"}), \
                 patch("shiftpad_linux.session.audio.choose_sink", return_value=None), \
                 patch("shiftpad_linux.session.discovery.read_edid", return_value=None), \
                 patch("shiftpad_linux.session.subprocess.Popen") as launch:
                session.activate(config)
            self.assertEqual([call.args[0] for call in launch.call_args_list], [STEAM_START])

    def test_restore_signals_only_the_recorded_custom_launcher(self):
        before = {"outputs": [screen("DP-2", 1, True), screen("HDMI-A-3", 2, False)]}
        switched = {"outputs": [screen("DP-2", 1, False), screen("HDMI-A-3", 2, True)]}
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3",
                        custom_launcher_enabled=True, custom_launcher_close=True,
                        custom_launcher_path="/tmp/Hydra.AppImage")
        identity = {"pid": 321, "boot_id": "boot-1", "start_time": "12345"}
        with tempfile.TemporaryDirectory() as directory:
            session = Session(Path(directory) / "session.json")
            with patch("shiftpad_linux.session.displays.capture", side_effect=[before, switched, switched, before]), \
                 patch("shiftpad_linux.session.displays.apply"), \
                 patch("shiftpad_linux.session.audio.default_sink", return_value="desk"), \
                 patch("shiftpad_linux.session.audio.sinks", return_value={"desk"}), \
                 patch("shiftpad_linux.session.audio.choose_sink", return_value=None), \
                 patch("shiftpad_linux.session.audio.set_default"), \
                 patch("shiftpad_linux.session.discovery.read_edid", return_value=None), \
                 patch("shiftpad_linux.session.subprocess.Popen") as launch, \
                 patch("shiftpad_linux.session._process_identity", return_value=identity), \
                 patch("shiftpad_linux.session.os.kill") as kill:
                launch.return_value.pid = 321
                session.activate(config)
                self.assertEqual(session._load()["custom_launcher_process"], identity)
                self.assertEqual(session._load()["audio_profiles"], {"card": "desktop"})
                session.restore()
                self.restore_profiles.assert_called_once_with({"card": "desktop"})
            kill.assert_called_once_with(321, signal.SIGTERM)
            self.assertFalse(session.pending())

    def test_stale_launcher_pid_is_not_signalled(self):
        identity = {"pid": 321, "boot_id": "old-boot", "start_time": "12345"}
        with patch("shiftpad_linux.session._process_identity", return_value=None), \
             patch("shiftpad_linux.session.os.kill") as kill:
            _stop_owned_launcher(identity)
        kill.assert_not_called()

    def test_session_reapplies_hdr_on_tv_and_restores_desktop_hdr(self):
        before = {"outputs": [screen("DP-2", 1, True), screen("HDMI-A-3", 2, False)]}
        before["outputs"][0].update(hdrEnabled=True, wcgEnabled=True, sdrBrightness=230)
        before["outputs"][1].update(hdrEnabled=True, wcgEnabled=True, sdrBrightness=240)
        switched = {"outputs": [screen("DP-2", 1, False), screen("HDMI-A-3", 2, True)]}
        switched["outputs"][1].update(hdrEnabled=False, wcgEnabled=False, sdrBrightness=200)
        restored = {"outputs": [screen("DP-2", 1, True), screen("HDMI-A-3", 2, False)]}
        restored["outputs"][0].update(hdrEnabled=False, wcgEnabled=False, sdrBrightness=200)
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3")
        with tempfile.TemporaryDirectory() as directory:
            session = Session(Path(directory) / "session.json")
            with patch("shiftpad_linux.session.displays.capture", side_effect=[before, switched, switched, restored]), \
                 patch("shiftpad_linux.session.displays.apply") as apply, \
                 patch("shiftpad_linux.session.audio.default_sink", return_value="desk"), \
                 patch("shiftpad_linux.session.audio.sinks", return_value={"desk"}), \
                 patch("shiftpad_linux.session.audio.choose_sink", return_value=None), \
                 patch("shiftpad_linux.session.audio.set_default"), \
                 patch("shiftpad_linux.session.discovery.read_edid", return_value=None):
                session.activate(config)
                session.restore()
        commands = [call.args[0] for call in apply.call_args_list]
        self.assertIn("output.HDMI-A-3.hdr.enable", commands[1])
        self.assertIn("output.HDMI-A-3.wcg.enable", commands[1])
        self.assertIn("output.HDMI-A-3.sdr-brightness.240", commands[1])
        self.assertIn("output.DP-2.hdr.enable", commands[3])
        self.assertIn("output.DP-2.wcg.enable", commands[3])
        self.assertIn("output.DP-2.sdr-brightness.230", commands[3])


class CountdownControlTest(unittest.TestCase):
    def test_restore_rearms_button_activated_receiver(self):
        class StopLoop(Exception):
            pass

        class FakeControl:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def poll(self, handler):
                self.before = handler("status")
                self.restored = handler("restore")
                self.after = handler("status")
                raise StopLoop

        control = FakeControl()
        watcher = Mock()
        watcher.poll.side_effect = [(True, False), (True, True)]
        watcher.device = SimpleNamespace(name="GameSir")
        session = Mock()
        session.pending.side_effect = [False, True, False]
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3", connect_delay=0)
        with patch("shiftpad_linux.cli.load", return_value=config), \
             patch("shiftpad_linux.cli.gamepad.Watcher", return_value=watcher), \
             patch("shiftpad_linux.cli.CountdownNotification"), \
             patch("shiftpad_linux.cli.ControlServer", return_value=control), \
             patch("shiftpad_linux.cli.signal.signal"), \
             patch("shiftpad_linux.cli.time.monotonic", return_value=0.0), \
             patch("shiftpad_linux.cli.displays.capture", return_value={}), \
             patch("shiftpad_linux.cli.displays.output", return_value={"connected": True}):
            with self.assertRaises(StopLoop):
                cli.daemon(None, session)
        self.assertTrue(control.before["active"])
        self.assertFalse(control.restored["active"])
        self.assertTrue(control.after["awaiting_input"])
        session.restore.assert_called_once()

    def test_present_receiver_waits_for_button_before_countdown(self):
        class StopLoop(Exception):
            pass

        class FakeControl:
            calls = 0

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def poll(self, handler):
                self.calls += 1
                if self.calls == 1:
                    self.before = handler("status")
                else:
                    self.after = handler("status")
                    raise StopLoop

        control = FakeControl()
        watcher = Mock()
        watcher.poll.side_effect = [(True, False), (True, False), (True, True)]
        watcher.device = SimpleNamespace(name="GameSir")
        session = Mock()
        session.pending.return_value = False
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3", connect_delay=2)
        with patch("shiftpad_linux.cli.load", return_value=config), \
             patch("shiftpad_linux.cli.gamepad.Watcher", return_value=watcher), \
             patch("shiftpad_linux.cli.CountdownNotification"), \
             patch("shiftpad_linux.cli.ControlServer", return_value=control), \
             patch("shiftpad_linux.cli.signal.signal"), \
             patch("shiftpad_linux.cli.time.monotonic", side_effect=[0.0, 1.0]):
            with self.assertRaises(StopLoop):
                cli.daemon(None, session)
        self.assertTrue(control.before["awaiting_input"])
        self.assertFalse(control.before["countdown_pending"])
        self.assertFalse(control.after["awaiting_input"])
        self.assertTrue(control.after["countdown_pending"])
        session.activate.assert_not_called()

    def test_changing_tv_cancels_pending_automatic_switch(self):
        class StopLoop(Exception):
            pass

        class FakeControl:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def poll(self, handler):
                if not hasattr(self, "before"):
                    self.before = handler("status")
                    self.reload = handler("reload")
                    self.after = handler("status")
                else:
                    raise StopLoop

        control = FakeControl()
        watcher = Mock()
        watcher.poll.side_effect = [(False, False), (True, False), (True, False)]
        watcher.device = SimpleNamespace(name="8BitDo")
        session = Mock()
        session.pending.return_value = False
        before = Config(desktop_output="DP-2", tv_output="HDMI-A-3", connect_delay=5)
        updated = Config(desktop_output="DP-2", tv_output="HDMI-A-4", connect_delay=5)
        with patch("shiftpad_linux.cli.load", side_effect=[before, updated]), \
             patch("shiftpad_linux.cli.gamepad.Watcher", return_value=watcher), \
             patch("shiftpad_linux.cli.CountdownNotification") as notification, \
             patch("shiftpad_linux.cli.ControlServer", return_value=control), \
             patch("shiftpad_linux.cli.signal.signal"), \
             patch("shiftpad_linux.cli.time.monotonic", side_effect=[0.0, 10.0]):
            with self.assertRaises(StopLoop):
                cli.daemon(None, session)
        self.assertTrue(control.before["countdown_pending"])
        self.assertTrue(control.reload["ok"])
        self.assertFalse(control.after["countdown_pending"])
        notification.return_value.cancel.assert_called()
        session.activate.assert_not_called()

    def test_cancel_blocks_current_connection_before_tv_switch(self):
        class StopLoop(Exception):
            pass

        class FakeControl:
            def __init__(self):
                self.calls = 0
                self.before = None
                self.after = None

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def poll(self, handler):
                self.calls += 1
                if self.calls == 1:
                    self.before = handler("status")
                    self.assert_cancelled = handler("cancel")
                    self.after = handler("status")
                else:
                    raise StopLoop

        control = FakeControl()
        watcher = Mock()
        watcher.poll.side_effect = [(False, False), (True, False), (True, False)]
        watcher.device = SimpleNamespace(name="8BitDo")
        session = Mock()
        session.pending.return_value = False
        config = Config(desktop_output="DP-2", tv_output="HDMI-A-3", connect_delay=5)
        with patch("shiftpad_linux.cli.load", return_value=config), \
             patch("shiftpad_linux.cli.gamepad.Watcher", return_value=watcher), \
             patch("shiftpad_linux.cli.CountdownNotification") as notification, \
             patch("shiftpad_linux.cli.ControlServer", return_value=control), \
             patch("shiftpad_linux.cli.signal.signal"), \
             patch("shiftpad_linux.cli.time.monotonic", side_effect=[0.0, 10.0]):
            with self.assertRaises(StopLoop):
                cli.daemon(None, session)
        self.assertTrue(control.before["countdown_pending"])
        self.assertTrue(control.assert_cancelled["ok"])
        self.assertFalse(control.after["countdown_pending"])
        notification.return_value.cancel.assert_called()
        session.activate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
