import QtQuick
import QtQuick.Controls
Switch {
 id: control
 implicitWidth: 90; implicitHeight: 48; padding: 0; opacity: enabled ? 1 : 0.4
 indicator: Rectangle { width: 90; height: 48; radius: 24; color: control.checked ? Theme.green : Theme.border; border.color: control.activeFocus ? Theme.white : "transparent"
  Rectangle { width: 38; height: 38; y: 5; x: control.checked ? 47 : 5; radius: 19; color: control.checked ? Theme.white : Theme.secondary; Behavior on x { NumberAnimation { duration: 150; easing.type: Easing.OutCubic } } }
  Behavior on color { ColorAnimation { duration: 150 } }
 }
}
