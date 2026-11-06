"""Qt Quick interface for the existing CouchPad monitor."""
from __future__ import annotations

import logging
import os
import shlex
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

# The bundled Qt/OpenGL libraries cannot reliably use the host graphics stack.
# Allow explicit overrides while keeping the portable package usable by default.
if getattr(sys, 'frozen', False):
    if 'QT_QUICK_BACKEND' not in os.environ:
        os.environ['QT_QUICK_BACKEND'] = 'software'
        os.environ['COUCHPAD_PRIVATE_QT_BACKEND'] = '1'

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from . import discovery
from .config import load, save_basic_settings, STEAM_START
from .control import request

LOG = logging.getLogger(__name__)


class Controller(QObject):
    changed = Signal()
    completed = Signal(object, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pool = ThreadPoolExecutor(max_workers=1)
        self.closing = False
        self.state = {}
        self.devices = {}
        self.message = 'Conectando ao monitor…'
        self.busy = False
        self.config = load()
        self.completed.connect(self._complete)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(3000)
        self.refresh()

    def _submit(self, fn):
        if self.busy:
            return
        self.busy = True
        self.changed.emit()
        future = self.pool.submit(fn)
        def done(f):
            if self.closing:
                return
            try:
                self.completed.emit(f.result(), None)
            except Exception as exc:
                self.completed.emit(None, exc)
        future.add_done_callback(done)

    @Slot(object, object)
    def _complete(self, result, error):
        if self.closing:
            return
        self.busy = False
        if error:
            self.message = 'Falha: ' + str(error)
            if isinstance(error, (OSError, TimeoutError)):
                self.state = {}
        elif result:
            self.state = result.get('status', self.state)
            self.devices = result.get('devices', self.devices)
            self.config = load()
            self.message = result.get('message', '')
        self.changed.emit()

    def shutdown(self):
        self.closing = True
        self.timer.stop()
        self.pool.shutdown(wait=True, cancel_futures=True)

    @Slot()
    def refresh(self):
        def work():
            status = request('status', timeout=2)
            if not status.get('ok'):
                raise RuntimeError(status.get('error', 'monitor indisponível'))
            return {'status': status, 'devices': discovery.scan(load())}
        self._submit(work)

    @Slot(str)
    def command(self, command):
        if command not in ('enable', 'disable', 'activate', 'restore', 'cancel'):
            return
        def work():
            response = request(command, timeout=45)
            if not response.get('ok'):
                raise RuntimeError(response.get('error', 'comando recusado'))
            return {'status': request('status', timeout=3), 'message': 'Comando concluído'}
        self._submit(work)

    @Slot(str, float, float, bool)
    def saveSettings(self, mode, connect, disconnect, steam):
        def work():
            current = load()
            steam_option = steam if current.launcher_start in ((), STEAM_START) else None
            save_basic_settings(mode, connect, disconnect, steam_option)
            response = request('reload', timeout=3)
            if not response.get('ok'):
                raise RuntimeError(response.get('error', 'falha ao recarregar'))
            return {'status': request('status', timeout=3), 'message': 'Preferências salvas e aplicadas'}
        self._submit(work)

    @Slot(bool)
    def saveSteam(self, enabled):
        current = self.config
        self.saveSettings(current.mode, current.connect_delay, current.disconnect_delay, enabled)

    def _save_changes(self, changes, hardware=False):
        def work():
            current = load()
            if hardware:
                status = request('status', timeout=3)
                if not status.get('ok') or status.get('active'):
                    raise ValueError('Restaure o desktop antes de trocar dispositivos')
                if 'tv_output' in changes and changes['tv_output'] != current.tv_output:
                    fresh = next((d for d in discovery.display_devices()
                                  if d.get('output') == changes['tv_output'] and d.get('connected')), None)
                    if not fresh or not changes.get('tv_edid_sha256') or fresh.get('edid_sha256') != changes['tv_edid_sha256']:
                        raise ValueError('TV desconectada ou identidade alterada; atualize os dispositivos')
            save_basic_settings(current.mode, current.connect_delay, current.disconnect_delay, None, **changes)
            response = request('reload', timeout=3)
            if not response.get('ok'):
                raise RuntimeError(response.get('error', 'falha ao recarregar'))
            return {'status': request('status', timeout=3), 'message': 'Preferências salvas e aplicadas'}
        self._submit(work)

    @Slot(str)
    def selectTv(self, output):
        item = next((x for x in self.devices.get('displays', []) if x.get('output') == output), None)
        if item:
            digest = self.config.tv_edid_sha256 if output == self.config.tv_output else item.get('edid_sha256', '')
            self._save_changes({'tv_output': output, 'tv_edid_sha256': digest}, True)

    @Slot(str)
    def selectGamepad(self, path):
        item = ({} if not path else next((x for x in self.devices.get('gamepads', []) if x.get('path') == path), None))
        if item is not None:
            self._save_changes({'gamepad_name': item.get('model', ''),
                                'gamepad_vendor_id': item.get('vendor_id', ''),
                                'gamepad_product_id': item.get('product_id', ''),
                                'gamepad_uniq': item.get('uniq', '')}, True)

    @Slot(str)
    def selectAudio(self, name):
        self._save_changes({'tv_sink': name}, True)

    @Slot(str, str, bool, bool)
    def saveLauncher(self, path, args, enabled, close):
        try:
            arguments = tuple(shlex.split(args))
        except ValueError as exc:
            self.message = f'Argumentos inválidos: {exc}'
            self.changed.emit()
            return
        self._save_changes({'custom_launcher_path': path, 'custom_launcher_args': arguments,
                            'custom_launcher_enabled': enabled, 'custom_launcher_close': close})

    @Slot()
    def openSettings(self):
        from .config import config_path
        from .system import host_environment
        subprocess.Popen(['xdg-open', str(config_path())], env=host_environment())

    @Slot(QUrl, result=str)
    def localPath(self, url):
        return url.toLocalFile()

    @Slot()
    def startService(self):
        from .system import host_environment
        def work():
            result = subprocess.run(['systemctl', '--user', 'start', 'shiftpad-linux.service'],
                                    capture_output=True, text=True, timeout=20, env=host_environment())
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or 'Não foi possível iniciar o serviço')
            return {'status': request('status', timeout=3), 'message': 'Monitor iniciado'}
        self._submit(work)

    @Property('QVariantMap', notify=changed)
    def data(self):
        tv = self.devices.get('tv') or {}
        desktop = next((d for d in self.devices.get('displays', []) if d.get('output') == self.config.desktop_output), {})
        gamepad = self.state.get('controller') or 'Nenhum controle detectado'
        audio = self.devices.get('tv_audio') or self.devices.get('configured_audio') or {}
        tv_choices = [dict(label=x.get('label', x.get('output', '')), value=x['output'])
                      for x in self.devices.get('displays', [])
                      if x.get('connected') and x.get('output') != self.config.desktop_output]
        if not any(x['value'] == self.config.tv_output for x in tv_choices):
            tv_choices.insert(0, dict(label=self.config.tv_output + ' (indisponível)', value=self.config.tv_output))
        pads = [dict(label='Qualquer controle', value='')]
        if self.config.gamepad_name:
            pads.append(dict(label=self.config.gamepad_name + ' (salvo)', value='__saved__'))
        pads += [dict(label=x.get('model', x['path']), value=x['path']) for x in self.devices.get('gamepads', []) if x.get('path')]
        audios = [dict(label='Automático', value='')] + [dict(label=x.get('description') or x['name'], value=x['name']) for x in self.devices.get('audio', []) if x.get('name')]
        if self.config.tv_sink and not any(x['value'] == self.config.tv_sink for x in audios):
            audios.append(dict(label=self.config.tv_sink + ' (indisponível)', value=self.config.tv_sink))
        return dict(online=bool(self.state.get('ok')), enabled=bool(self.state.get('enabled')),
                    active=bool(self.state.get('active')), pending=bool(self.state.get('countdown_pending')),
                    busy=self.busy, message=self.message, tv=tv.get('label', self.config.tv_output),
                    tvConnected=bool(tv.get('connected')), desktop=self.config.desktop_output,
                    tvTitle='TV ' + str(tv.get('manufacturer') or tv.get('model') or '').strip(),
                    tvResolution=tv.get('resolution', ''), desktopResolution=desktop.get('resolution', ''),
                    deviceRows=[dict(title=x.get('model') or x.get('label') or x.get('name') or '',
                                     description=x.get('path') or x.get('output') or x.get('description') or '',
                                     status='Conectado', kind=kind)
                                for kind, key in [('devices','gamepads'),('monitor','displays'),('audio','audio')]
                                for x in self.devices.get(key, []) if key != 'displays' or x.get('connected')],
                    controller=gamepad, audio=audio.get('description') or audio.get('name') or 'Detecção automática',
                    mode=self.config.mode, connect=self.config.connect_delay,
                    disconnect=self.config.disconnect_delay, steam=self.config.launcher_start == STEAM_START,
                    steamEditable=self.config.launcher_start in ((), STEAM_START),
                    tvChoices=tv_choices, tvValue=self.config.tv_output, gamepadChoices=pads,
                    gamepadValue='__saved__' if self.config.gamepad_name else '',
                    audioChoices=audios, audioValue=self.config.tv_sink,
                    launcherPath=self.config.custom_launcher_path,
                    launcherArgs=shlex.join(self.config.custom_launcher_args),
                    launcherEnabled=self.config.custom_launcher_enabled,
                    launcherClose=self.config.custom_launcher_close)


def main():
    app = QApplication.instance() or QApplication([])
    app.setApplicationName('CouchPad')
    app.setQuitOnLastWindowClosed(False)
    icon = QIcon(str(Path(__file__).parent / 'assets/couchpad.svg'))
    app.setWindowIcon(icon)
    controller = Controller(app)
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty('backend', controller)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).parent / 'qml/Main.qml')))
    if not engine.rootObjects():
        raise RuntimeError('Não foi possível carregar a interface QML')
    window = engine.rootObjects()[0]
    tray = QSystemTrayIcon(icon, app)
    menu = QMenu()
    menu.addAction('Abrir CouchPad', window.show)
    toggle = menu.addAction('Ativar CouchPad', lambda: controller.command('disable' if controller.data['enabled'] else 'enable'))
    activate = menu.addAction('Ativar TV', lambda: controller.command('activate'))
    restore = menu.addAction('Restaurar desktop', lambda: controller.command('restore'))
    cancel = menu.addAction('Cancelar troca para TV', lambda: controller.command('cancel'))
    def update_menu():
        data = controller.data
        ready = data['online'] and not data['busy']
        toggle.setText('Desativar CouchPad' if data['enabled'] else 'Ativar CouchPad')
        toggle.setEnabled(ready)
        activate.setEnabled(ready and data['enabled'] and not data['active'])
        restore.setEnabled(ready and data['active'])
        cancel.setEnabled(ready and data['pending'])
    controller.changed.connect(update_menu)
    update_menu()
    menu.addSeparator()
    menu.addAction('Encerrar CouchPad' if os.environ.get('COUCHPAD_OWNS_MONITOR') == '1' else 'Fechar interface', app.quit)
    tray.setContextMenu(menu)
    tray.activated.connect(lambda reason: window.show() if reason == QSystemTrayIcon.Trigger else None)
    if QSystemTrayIcon.isSystemTrayAvailable():
        tray.show()
    else:
        app.setQuitOnLastWindowClosed(True)
    app.aboutToQuit.connect(controller.shutdown)
    return app.exec()
