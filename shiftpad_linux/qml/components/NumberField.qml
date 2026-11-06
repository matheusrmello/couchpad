import QtQuick
import QtQuick.Controls
SpinBox {
 id: control; implicitWidth: 170; implicitHeight: 48; font.family: Theme.family; font.pixelSize: 20
 palette.text: Theme.white; palette.base: Theme.cardEnd; palette.buttonText: Theme.white; opacity: enabled ? 1 : 0.4
 background: Rectangle { radius: 12; color: Theme.cardEnd; border.color: control.activeFocus ? Theme.green : Theme.strong }
 up.indicator: Rectangle { x: control.width - width; width: 30; height: control.height / 2; color: control.up.pressed ? Theme.hover : "transparent"; Text { anchors.centerIn: parent; text: "+"; color: Theme.white; font.pixelSize: 18 } }
 down.indicator: Rectangle { x: control.width - width; y: control.height / 2; width: 30; height: control.height / 2; color: control.down.pressed ? Theme.hover : "transparent"; Text { anchors.centerIn: parent; text: "−"; color: Theme.white; font.pixelSize: 18 } }
}
