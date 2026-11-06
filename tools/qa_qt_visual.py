"""Render all Qt pages using isolated preferences and explicitly simulated hardware."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import sys, tempfile, time
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtCore import QUrl, qInstallMessageHandler
from PySide6.QtQuick import QQuickWindow
from shiboken6 import getCppPointer, wrapInstance
from shiftpad_linux.qt_frontend import Controller
from shiftpad_linux.config import STEAM_START, STEAM_STOP
import json
root=Path(__file__).resolve().parents[1]
out=root/'.build/qt-visual';out.mkdir(parents=True,exist_ok=True)
app=QApplication([]); messages=[]
previous=qInstallMessageHandler(lambda level,context,message: messages.append(message))
try:
 with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ,{'XDG_CONFIG_HOME':directory}):
  config=Path(directory)/'shiftpad-linux/config.toml';config.parent.mkdir();config.write_text('[display]\ndesktop_output="DP-2"\ntv_output="HDMI-A-3"\n[gamepad]\nconnect_delay=5\n[launcher]\nstart='+json.dumps(STEAM_START)+'\nstop='+json.dumps(STEAM_STOP)+'\n')
  displays=[{'output':'DP-2','label':'Monitor','enabled':True,'connected':True,'resolution':'1920 × 1080'}, {'output':'HDMI-A-3','label':'Samsung','manufacturer':'Samsung','model':'Samsung','connected':True,'resolution':'3840 × 2160'}]
  scan={'displays':displays,'tv':displays[1],'gamepads':[{'path':'/dev/input/qa','model':'8BitDo Pro 2 (Bluetooth)','vendor_id':'1234','product_id':'5678'}], 'tv_audio':{'description':'TV Samsung (HDMI)'},'audio':[{'name':'qa.hdmi','description':'TV Samsung (HDMI)'}]}
  with patch('shiftpad_linux.qt_frontend.request',return_value={'ok':True,'enabled':True,'active':False,'controller':'8BitDo conectado'}),patch('shiftpad_linux.qt_frontend.discovery.scan',return_value=scan):
   controller=Controller(app);engine=QQmlApplicationEngine();engine.rootContext().setContextProperty('backend',controller);engine.load(QUrl.fromLocalFile(str(root/'shiftpad_linux/qml/Main.qml')))
   assert engine.rootObjects(),'QML did not load'
   window=wrapInstance(getCppPointer(engine.rootObjects()[0])[0],QQuickWindow)
   for width,height in [(1672,941),(1320,760),(800,700)]:
    window.setWidth(width);window.setHeight(height)
    for page in range(4):
     window.setProperty('page',page)
     for _ in range(30): app.processEvents();time.sleep(.02)
     assert window.grabWindow().save(str(out/f'page-{page}-{width}.png'))
   failures=[m for m in messages if 'Cannot' in m or 'Error' in m or 'binding loop' in m.lower()]
   assert not failures,'\n'.join(failures)
   controller.shutdown();engine.deleteLater();app.processEvents()
finally:
 qInstallMessageHandler(previous)
print('12 renders passed:',out)
