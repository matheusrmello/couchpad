import QtQuick
import QtQuick.Controls
ComboBox {
 id: control; implicitHeight: 48; implicitWidth: 260; font.family: Theme.family; font.pixelSize: 18; opacity: enabled ? 1 : 0.4
 palette.text: Theme.white; palette.buttonText: Theme.white; palette.base: Theme.cardEnd; palette.highlight: "#0F2E27"; palette.highlightedText: Theme.green
 background: Rectangle { radius: 12; color: control.hovered ? Theme.hover : Theme.cardEnd; border.color: control.activeFocus ? Theme.green : Theme.strong }
}
