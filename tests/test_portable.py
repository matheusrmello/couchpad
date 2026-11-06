import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from shiftpad_linux import config, portable, system


class PortableConfigurationTest(unittest.TestCase):
    def test_first_run_detects_machine_and_starts_disabled(self):
        snapshot = {"outputs": [{"name": "DP-9", "connected": True, "enabled": True},
                                {"name": "HDMI-A-7", "connected": True, "enabled": False}]}
        with tempfile.TemporaryDirectory() as directory, \
             patch.dict(os.environ, {"XDG_CONFIG_HOME": directory}), \
             patch.object(portable.displays, "capture", return_value=snapshot), \
             patch.object(portable.displays, "edid_sha256", return_value="a"*64):
            self.assertTrue(portable.ensure_configuration())
            result = config.load()
            self.assertFalse(result.enabled)
            self.assertEqual((result.desktop_output,result.tv_output), ("DP-9","HDMI-A-7"))
            self.assertEqual(result.tv_edid_sha256, "a"*64)
            self.assertEqual(result.gamepad_name, "")
            self.assertEqual(result.launcher_start, ())
            self.assertEqual(config.config_path().stat().st_mode & 0o777, 0o600)

    def test_existing_configuration_is_untouched(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{"XDG_CONFIG_HOME":directory}):
            path=config.config_path(); path.parent.mkdir(); path.write_text('existing file')
            with patch.object(portable.displays,"capture") as capture:
                self.assertFalse(portable.ensure_configuration())
                capture.assert_not_called()
            self.assertEqual(path.read_text(),'existing file')

    def test_one_monitor_creates_editable_disconnected_tv_target(self):
        snapshot={"outputs":[{"name":"eDP-1","connected":True,"enabled":True}]}
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{"XDG_CONFIG_HOME":directory}), \
             patch.object(portable.displays,"capture",return_value=snapshot):
            portable.ensure_configuration()
            result=config.load()
            self.assertEqual(result.desktop_output,'eDP-1')
            self.assertNotEqual(result.desktop_output,result.tv_output)
            self.assertFalse(result.enabled)

    def test_missing_displays_do_not_write_partial_configuration(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{"XDG_CONFIG_HOME":directory}), \
             patch.object(portable.displays,"capture",return_value={"outputs":[]}):
            with self.assertRaises(RuntimeError): portable.ensure_configuration()
            self.assertFalse(config.config_path().exists())


class PortableMonitorTest(unittest.TestCase):
    def setUp(self):
        p=patch.object(portable,'_monitor',None); p.start(); self.addCleanup(p.stop)

    def test_reuses_existing_monitor_without_spawning(self):
        with patch.object(portable,'request',return_value={'ok':True}), patch.object(portable.subprocess,'Popen') as spawn:
            self.assertFalse(portable.ensure_monitor())
            spawn.assert_not_called()

    def test_starts_child_and_waits_for_socket(self):
        child=Mock(); child.poll.return_value=None
        with patch.object(portable,'request',side_effect=[OSError('no socket'),{'ok':True}]), \
             patch.object(portable.subprocess,'Popen',return_value=child), patch.dict(os.environ,{}):
            self.assertTrue(portable.ensure_monitor())
            self.assertIs(portable._monitor,child)
            self.assertEqual(os.environ['COUCHPAD_OWNS_MONITOR'],'1')

    def test_closes_only_owned_monitor(self):
        child=Mock(); child.poll.return_value=None; portable._monitor=child
        portable.stop_monitor()
        child.terminate.assert_called_once()
        child.wait.assert_called_once_with(timeout=60)
        self.assertIsNone(portable._monitor)

    def test_frozen_monitor_launch_uses_bundled_executable(self):
        with patch.object(portable.sys,'frozen',True,create=True), patch.object(portable.sys,'executable','/mounted/usr/bin/couchpad'):
            self.assertEqual(portable.monitor_command(),['/mounted/usr/bin/couchpad','run'])


class HostEnvironmentTest(unittest.TestCase):
    def test_explicit_qt_renderer_is_preserved_for_host_processes(self):
        with patch.dict(os.environ, {'QT_QUICK_BACKEND': 'custom'}, clear=True), \
             patch.object(system.sys, 'frozen', True, create=True), \
             patch.object(system.sys, '_MEIPASS', '/bundle', create=True):
            self.assertEqual(system.host_environment()['QT_QUICK_BACKEND'], 'custom')

    def test_host_process_does_not_inherit_bundled_libraries(self):
        env={'LD_LIBRARY_PATH':'/bundle:/original','LD_LIBRARY_PATH_ORIG':'/original',
             'GI_TYPELIB_PATH':'/bundle/gi_typelibs','XDG_DATA_DIRS':'/bundle/share:/usr/share',
             'GDK_PIXBUF_MODULE_FILE':'/bundle/loaders.cache','DISPLAY':':1',
             'FONTCONFIG_PATH':'/bundle/etc/fonts','FONTCONFIG_FILE':'/bundle/etc/fonts/fonts.conf',
             'QT_QUICK_BACKEND':'software', 'COUCHPAD_PRIVATE_QT_BACKEND':'1'}
        with patch.dict(os.environ,env,clear=True), patch.object(system.sys,'frozen',True,create=True), \
             patch.object(system.sys,'_MEIPASS','/bundle',create=True):
            result=system.host_environment()
            self.assertEqual(result['LD_LIBRARY_PATH'],'/original')
            self.assertEqual(result['XDG_DATA_DIRS'],'/usr/share')
            self.assertNotIn('FONTCONFIG_PATH', result)
            self.assertNotIn('FONTCONFIG_FILE', result)
            self.assertNotIn('QT_QUICK_BACKEND', result)
            self.assertEqual(result['DISPLAY'],':1')
            self.assertNotIn('GI_TYPELIB_PATH',result)
            self.assertNotIn('GDK_PIXBUF_MODULE_FILE',result)
            self.assertEqual(os.environ['LD_LIBRARY_PATH'],'/bundle:/original')

    def test_no_original_library_path_removes_bundle_path(self):
        with patch.dict(os.environ,{'LD_LIBRARY_PATH':'/bundle'},clear=True), \
             patch.object(system.sys,'frozen',True,create=True):
            self.assertNotIn('LD_LIBRARY_PATH',system.host_environment())
