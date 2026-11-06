import QtQuick
import QtQuick.Controls
CheckBox { id: control; font.family: Theme.family; font.pixelSize: 18; palette.windowText: Theme.white; palette.highlight: Theme.green; opacity: enabled ? 1 : 0.4; indicator: Rectangle { implicitWidth: 24; implicitHeight: 24; x: 4; y: (parent.height-height)/2; radius: 6; color: control.checked ? Theme.green : Theme.cardEnd; border.color: control.activeFocus ? Theme.green : Theme.strong; Text { anchors.centerIn: parent; text: control.checked ? "✓" : ""; color: Theme.app; font.pixelSize: 18 } } }
