import QtQuick
Rectangle { property string text; radius: 12; color: Theme.card; border.color: Theme.border; implicitWidth: 420; implicitHeight: label.implicitHeight + 32
 Rectangle { width: 4; height: parent.height - 16; anchors.left: parent.left; anchors.verticalCenter: parent.verticalCenter; color: Theme.green; radius: 2 }
 Text { id: label; anchors.fill: parent; anchors.margins: 16; text: parent.text; wrapMode: Text.WordWrap; color: Theme.white; font.family: Theme.family; font.pixelSize: 16 }
}
