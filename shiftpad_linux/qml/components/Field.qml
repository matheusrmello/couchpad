import QtQuick
import QtQuick.Controls
TextField { id: control; implicitHeight: 48; font.family: Theme.family; font.pixelSize: 18; color: Theme.white; placeholderTextColor: Theme.muted; selectByMouse: true; background: Rectangle { color: Theme.cardEnd; radius: 12; border.color: control.activeFocus ? Theme.green : Theme.strong } }
