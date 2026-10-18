"""GTK integration checks with an isolated configuration and simulated daemon.

Run inside a graphical session: python3 tools/qa_tray.py
Real display and audio devices are only inspected; no desktop changes are made.
"""
import inspect, json, os, shutil, sys, tempfile, time, traceback
from pathlib import Path
from unittest.mock import patch, Mock
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib
from shiftpad_linux import tray, config, discovery
original_path = config.config_path()
original_bytes = original_path.read_bytes()
scan = discovery.scan(config.load())
scan['gamepads'] = [{'path':'/dev/input/qa-controller','model':'QA Gamepad','vendor_id':'1234','product_id':'5678','uniq':'qa-controller'}]
results = []
state = dict(ok=True, enabled=False, active=False, controller='', countdown_pending=False)
commands = []
def request(command, **kwargs):
 commands.append(command)
 if command in ('enable','disable'): state['enabled'] = command == 'enable'
 if command == 'activate': state['active'] = True
 if command == 'restore': state['active'] = False
 if command == 'cancel': state['countdown_pending'] = False
 return dict(state)
def pump(duration=.8):
 end=time.monotonic()+duration
 while time.monotonic()<end:
  while GLib.MainContext.default().pending(): GLib.MainContext.default().iteration(False)
  time.sleep(.01)
def check(name, condition):
 if not condition: raise AssertionError(name)
 results.append(name)
 print('PASS', name, flush=True)
def children(widget):
 yield widget
 if isinstance(widget, Gtk.Container):
  for child in widget.get_children(): yield from children(child)
def button(app, label):
 return next(w for w in children(app.window) if isinstance(w,Gtk.Button) and w.get_label()==label)
def run_ui():
 frame=inspect.currentframe().f_back
 while 'app' not in frame.f_locals: frame=frame.f_back
 app=frame.f_locals['app']
 pump(.4)
 def action(widget): widget.emit('clicked'); pump()
 app.busy=True
 with patch.object(tray,'request',side_effect=AssertionError('consulta de status durante operação')):
  app.refresh()
 app.busy=False
 check('janela não consulta serviço durante operação demorada', app.online)
 check('janela e 9 ícones carregados', app.window.get_visible() and sum(isinstance(w,Gtk.Image) and w.get_storage_type()==Gtk.ImageType.PIXBUF for w in children(app.window)) >= 9)
 action(app.service_button)
 check('botão Ativar CouchPad', state['enabled'] and app.service_button.get_label()=='Desativar CouchPad')
 action(app.activate_button)
 check('botão Ativar TV e bloqueio dos seletores', state['active'] and not app.tv_chooser.get_sensitive() and not app.audio_chooser.get_sensitive())
 action(app.restore_button)
 check('botão Restaurar e desbloqueio dos seletores', not state['active'] and app.tv_chooser.get_sensitive())
 action(app.service_button)
 check('botão Desativar CouchPad', not state['enabled'] and not app.activate_button.get_sensitive())
 for mode, widget in app.mode_buttons.items():
  action(widget)
  check('modo de vídeo + autosave: '+mode, config.load().mode==mode and sum(w.get_active() for w in app.mode_buttons.values())==1)
 app.connect_delay.set_value(3.5); app.disconnect_delay.set_value(4.5); pump()
 check('atrasos e autosave', (config.load().connect_delay,config.load().disconnect_delay)==(3.5,4.5))
 app.steam.set_active(False); pump()
 check('desligar Steam e autosave', not config.load().launcher_start)
 app.steam.set_active(True); pump()
 check('ligar Steam e autosave', config.load().launcher_start==config.STEAM_START)
 app.gamepad_chooser.set_active_id('/dev/input/qa-controller'); pump()
 check('seleção de controle e IDs', config.load().gamepad_vendor_id=='1234' and config.load().gamepad_uniq=='qa-controller')
 app.gamepad_chooser.set_active_id('__any__'); pump()
 check('qualquer controle', not config.load().gamepad_name)
 sink=scan['audio'][0]['name']
 app.audio_chooser.set_active_id(sink); pump()
 check('seleção da saída de áudio', config.load().tv_sink==sink)
 app.audio_chooser.set_active_id('__auto__'); pump()
 check('áudio automático', not config.load().tv_sink)
 app.audio_manual.set_text('qa.manual.sink'); pump()
 check('saída de áudio manual', config.load().tv_sink=='qa.manual.sink')
 action(button(app,'Detectar dispositivos'))
 check('detectar dispositivos e lista da TV', not app.scanning and app.tv_chooser.get_active_id()==config.load().tv_output)
 app.tv_chooser.emit('changed'); pump()
 check('seleção de TV e preservação do EDID', config.load().tv_edid_sha256==app.config.tv_edid_sha256)
 chooser=Mock(); chooser.run.return_value=Gtk.ResponseType.CANCEL
 with patch.object(Gtk.FileChooserNative,'new',return_value=chooser): action(app.choose_launcher)
 check('cancelar escolha de programa', chooser.destroy.called)
 chooser.reset_mock(); chooser.run.return_value=Gtk.ResponseType.ACCEPT; chooser.get_filename.return_value='/etc/hosts'
 with patch.object(Gtk.FileChooserNative,'new',return_value=chooser): action(app.choose_launcher)
 check('recusar arquivo não executável', 'Escolha um executável' in app.message.get_text())
 chooser.get_filename.return_value='/usr/bin/true'
 with patch.object(Gtk.FileChooserNative,'new',return_value=chooser): action(app.choose_launcher)
 check('escolher programa e autosave', config.load().custom_launcher_path=='/usr/bin/true' and config.load().custom_launcher_enabled)
 app.custom_launcher_args.set_text('--qa "two words"'); pump()
 check('argumentos preservam espaços', config.load().custom_launcher_args==('--qa','two words'))
 app.custom_close_switch.set_active(True); pump()
 check('fechar somente inicializador', config.load().custom_launcher_close)
 app.custom_launcher_switch.set_active(False); pump()
 check('desligar outro programa preserva Steam', not config.load().custom_launcher_enabled and config.load().launcher_start==config.STEAM_START)
 app.custom_launcher_args.set_text('"'); pump()
 check('erro de argumentos aparece na janela', 'Falha:' in app.message.get_text() and 'argumentos' in app.message.get_text())
 app.custom_launcher_args.set_text(''); pump()
 check('recuperação após erro', app.message.get_text()=='Preferências salvas e aplicadas')
 with patch.object(tray.subprocess,'Popen') as opener:
  action(button(app,'Editar combinação')); action(button(app,'Configuração completa'))
  check('Editar combinação e Configuração completa abrem TOML', opener.call_count==2 and opener.call_args.args[0][0]=='xdg-open')
 app.hide_window(); check('fechar janela oculta na bandeja', not app.window.get_visible())
 app.icon.emit('activate'); check('ícone da bandeja reabre janela', app.window.get_visible())
 for label in ('Ativar CouchPad','Ativar TV','Restaurar desktop','Desativar CouchPad','Abrir CouchPad'):
  item=next(w for w in app.menu.get_children() if isinstance(w,Gtk.MenuItem) and w.get_label()==label)
  item.emit('activate'); pump(); check('menu da bandeja: '+label, not app.busy and not app.message.get_text().startswith('Falha:'))
 state['enabled']=True; state['countdown_pending']=True; app.refresh()
 app.menu_cancel.emit('activate'); pump()
 check('menu Cancelar troca para TV', not state['countdown_pending'] and 'cancel' in commands)
 with patch.object(Gtk,'main_quit') as quit_fn:
  next(w for w in app.menu.get_children() if isinstance(w,Gtk.MenuItem) and w.get_label()=='Fechar interface').emit('activate')
  check('menu Fechar interface', quit_fn.called)
 with patch.object(tray,'request',side_effect=OSError('QA indisponível')):
  app.refresh()
  check('serviço indisponível: feedback e ações bloqueadas', not app.online and app.service_button.get_label()=='Iniciar serviço' and not app.activate_button.get_sensitive())
  with patch.object(tray.subprocess,'run',return_value=Mock(returncode=0)) as start:
   action(app.service_button)
   check('botão Iniciar serviço', start.called and start.call_args.args[0]==['systemctl','--user','start','shiftpad-linux.service'])
 app.icon.set_visible(False); app.window.destroy()
with tempfile.TemporaryDirectory(prefix='couchpad-ui-qa-') as directory:
 os.environ['XDG_CONFIG_HOME']=directory
 target=config.config_path(); target.parent.mkdir(); target.write_bytes(original_bytes)
 with patch.object(tray,'request',side_effect=request), patch.object(discovery,'scan',return_value=scan), patch.object(Gtk,'main',side_effect=run_ui):
  tray.main()
check('configuração original intacta', original_path.read_bytes()==original_bytes)
Path('/tmp/couchpad-ui-qa-results.json').write_text(json.dumps(results,ensure_ascii=False,indent=2))
print('TOTAL',len(results))
