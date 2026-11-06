import QtQuick
import QtQuick.Controls
RadioButton { id: control; font.family: Theme.family; font.pixelSize: 18; palette.windowText: Theme.white; opacity: enabled ? 1 : 0.4; indicator: Rectangle { width: 24; height: 24; x: 4; y: (parent.height-height)/2; radius: 12; color: Theme.cardEnd; border.color: control.activeFocus || control.checked ? Theme.green : Theme.strong; Rectangle { anchors.centerIn: parent; width: 12; height: 12; radius: 6; color: Theme.green; visible: control.checked } } }
