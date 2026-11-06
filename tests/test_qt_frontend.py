"""Qt QML smoke and IPC action tests, isolated from actual desktop hardware."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    from PySide6.QtCore import QObject, QUrl
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtWidgets import QApplication
    from shiftpad_linux.qt_frontend import Controller
    HAVE_QT = True
except ImportError:
    HAVE_QT = False


@unittest.skipUnless(HAVE_QT, 'PySide6 opcional não instalado')
class QtFrontendTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def wait_for(self, predicate):
        deadline = time.monotonic() + 4
        while time.monotonic() < deadline:
            self.app.processEvents()
            if predicate():
                return
            time.sleep(.01)
        self.fail('Operação Qt não terminou')

    def test_qml_actions_and_offline_state(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'shiftpad-linux'
            config.mkdir()
            (config / 'config.toml').write_text('[general]\nenabled = false\n[display]\ndesktop_output = "DP-1"\ntv_output = "HDMI-1"\n')
            state = {'ok': True, 'enabled': True, 'active': False}
            calls = []
            def daemon(command, **kwargs):
                calls.append(command)
                if command == 'activate': state['active'] = True
                return dict(state)
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': directory}), \
                 patch('shiftpad_linux.qt_frontend.request', side_effect=daemon), \
                 patch('shiftpad_linux.qt_frontend.discovery.scan', return_value={'tv': {'label': 'TV teste', 'connected': True}}):
                controller = Controller()
                self.wait_for(lambda: not controller.busy)
                engine = QQmlApplicationEngine()
                engine.rootContext().setContextProperty('backend', controller)
                engine.load(QUrl.fromLocalFile(str(Path(__file__).resolve().parents[1] / 'shiftpad_linux/qml/Main.qml')))
                self.assertTrue(engine.rootObjects())
                root = engine.rootObjects()[0]
                icon = root.findChild(QObject, 'brandIcon')
                self.wait_for(lambda: icon.property('loaded'))
                from PySide6.QtGui import QImage
                for name in ('home', 'devices', 'layers', 'settings', 'monitor', 'tv'):
                    path = Path(__file__).resolve().parents[1] / 'shiftpad_linux/assets/ui' / (name + '.svg')
                    self.assertFalse(QImage(str(path)).isNull(), name)
                grid = root.findChild(QObject, 'displayGrid')
                cards = root.findChild(QObject, 'summaryGrid')
                root.setProperty('width', 800)
                self.app.processEvents()
                self.assertEqual(grid.property('columns'), 1)
                self.assertEqual(cards.property('columns'), 1)
                root.setProperty('width', 1400)
                self.app.processEvents()
                self.assertEqual(grid.property('columns'), 3)
                self.assertEqual(cards.property('columns'), 3)
                activate = root.findChild(QObject, 'activateTv')
                restore = root.findChild(QObject, 'restoreDesktop')
                self.assertTrue(activate.property('enabled'))
                activate.clicked.emit()
                self.wait_for(lambda: not controller.busy)
                self.app.processEvents()
                self.assertIn('activate', calls)
                self.assertTrue(controller.data['active'])
                self.assertTrue(restore.property('enabled'))
                with patch('shiftpad_linux.qt_frontend.request', side_effect=OSError('indisponível')):
                    controller.refresh()
                    self.wait_for(lambda: not controller.busy)
                    self.app.processEvents()
                    self.assertFalse(controller.data['online'])
                    self.assertFalse(restore.property('enabled'))
                root.close()
                controller.timer.stop()
                controller.pool.shutdown(wait=True)

    def test_save_device_identity_and_launcher_preserves_other_settings(self):
        from shiftpad_linux.config import load
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'shiftpad-linux'
            config.mkdir()
            (config / 'config.toml').write_text('[general]\nenabled = false\n[display]\ndesktop_output = "DP-1"\ntv_output = "HDMI-1"\n[gamepad]\nconnect_delay = 2.5\n')
            tv = {'output': 'HDMI-2', 'label': 'TV', 'connected': True, 'edid_sha256': 'a' * 64}
            pad = {'path': '/dev/input/test', 'model': 'Pad', 'vendor_id': '1234', 'product_id': '5678', 'uniq': 'id'}
            def daemon(command, **kwargs):
                return {'ok': True, 'enabled': False, 'active': False}
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': directory}), \
                 patch('shiftpad_linux.qt_frontend.request', side_effect=daemon), \
                 patch('shiftpad_linux.qt_frontend.discovery.scan', return_value={'tv': tv, 'displays': [tv], 'gamepads': [pad], 'audio': []}), \
                 patch('shiftpad_linux.qt_frontend.discovery.display_devices', return_value=[tv]):
                controller = Controller()
                self.wait_for(lambda: not controller.busy)
                controller.selectTv('HDMI-2')
                self.wait_for(lambda: not controller.busy)
                self.assertEqual(load().tv_edid_sha256, 'a' * 64)
                controller.selectGamepad('/dev/input/test')
                self.wait_for(lambda: not controller.busy)
                self.assertEqual((load().gamepad_name, load().gamepad_vendor_id), ('Pad', '1234'))
                controller.selectAudio('alsa_output.test')
                self.wait_for(lambda: not controller.busy)
                controller.saveLauncher('/usr/bin/true', '--name "two words"', True, True)
                self.wait_for(lambda: not controller.busy)
                saved = load()
                self.assertEqual(saved.custom_launcher_args, ('--name', 'two words'))
                self.assertEqual(saved.tv_sink, 'alsa_output.test')
                self.assertEqual(saved.connect_delay, 2.5)
                controller.timer.stop()
                controller.pool.shutdown(wait=True)

    def test_rejects_changed_tv_and_retains_online_status(self):
        from shiftpad_linux.config import load
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'shiftpad-linux'
            config.mkdir()
            (config / 'config.toml').write_text('[general]\nenabled = false\n[display]\ndesktop_output = "DP-1"\ntv_output = "HDMI-1"\n')
            tv = {'output': 'HDMI-2', 'connected': True, 'edid_sha256': 'a' * 64}
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': directory}), \
                 patch('shiftpad_linux.qt_frontend.request', return_value={'ok': True, 'active': False}), \
                 patch('shiftpad_linux.qt_frontend.discovery.scan', return_value={'displays': [tv]}), \
                 patch('shiftpad_linux.qt_frontend.discovery.display_devices', return_value=[]):
                controller = Controller()
                self.wait_for(lambda: not controller.busy)
                controller.selectTv('HDMI-2')
                self.wait_for(lambda: not controller.busy)
                self.assertEqual(load().tv_output, 'HDMI-1')
                self.assertTrue(controller.data['online'])
                self.assertIn('TV desconectada', controller.data['message'])
                controller.timer.stop()
                controller.pool.shutdown(wait=True)

    def test_shutdown_ignores_late_worker_results(self):
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / 'shiftpad-linux'
            config.mkdir()
            (config / 'config.toml').write_text('[display]\ndesktop_output="DP-1"\ntv_output="HDMI-1"\n')
            with patch.dict(os.environ, {'XDG_CONFIG_HOME': directory}), \
                 patch('shiftpad_linux.qt_frontend.request', return_value={'ok': True}), \
                 patch('shiftpad_linux.qt_frontend.discovery.scan', return_value={}):
                controller = Controller()
                self.wait_for(lambda: not controller.busy)
                controller.shutdown()
                with patch('shiftpad_linux.qt_frontend.load', side_effect=FileNotFoundError('preferences removed')):
                    controller._complete({'status': {'ok': False}}, None)
                self.assertFalse(controller.timer.isActive())
                self.assertTrue(controller.data['online'])
