import QtQuick
Rectangle { property string text; property color tint: Theme.green; implicitHeight: 28; implicitWidth: label.implicitWidth + 24; radius: 14; color: Qt.rgba(tint.r,tint.g,tint.b,0.12); Text { id: label; anchors.centerIn: parent; text: parent.text; color: parent.tint; font.family: Theme.family; font.pixelSize: 13 } }
