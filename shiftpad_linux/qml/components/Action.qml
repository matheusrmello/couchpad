import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
Button {
 id: control
 property string variant: "secondary"
 property url iconSource
 property int textSize: 20
 implicitHeight: 48; implicitWidth: Math.max(120, label.implicitWidth + 48)
 hoverEnabled: true; opacity: enabled ? 1 : 0.4
 scale: pressed ? 0.98 : 1
 Behavior on scale { NumberAnimation { duration: 120 } }
 Accessible.name: text
 contentItem: Item {
 Row { spacing: 14; anchors.centerIn: parent
  Icon { width: control.iconSource.toString() ? 28 : 0; height: 28; source: control.iconSource; anchors.verticalCenter: parent.verticalCenter; visible: width > 0 }
  Text { id: label; text: control.text; font.family: Theme.family; font.pixelSize: control.textSize; font.weight: Font.DemiBold; color: control.variant === "destructive" ? Theme.error : Theme.white; anchors.verticalCenter: parent.verticalCenter }
 }
 }
 background: Rectangle {
  radius: 14; border.color: control.activeFocus ? Theme.green : control.variant === "primary" ? Theme.green : Theme.strong
  border.width: control.activeFocus ? 2 : 1
  gradient: Gradient {
   GradientStop { position: 0; color: control.variant === "primary" ? control.hovered ? "#22E55F" : "#2BE06A" : control.variant === "destructive" ? "#1A1634" : control.hovered ? "#151D30" : "#111827" }
   GradientStop { position: 1; color: control.variant === "primary" ? "#14B84C" : "#0F1626" }
  }
 }
}
