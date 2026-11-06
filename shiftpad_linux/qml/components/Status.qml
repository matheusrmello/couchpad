import QtQuick
import QtQuick.Layouts
RowLayout { property string text; property color tint: Theme.green; property int textSize: 20; spacing: 12
 Rectangle { width: 14; height: 14; radius: 7; color: parent.tint }
 Text { text: parent.text; color: parent.tint; font.family: Theme.family; font.pixelSize: parent.textSize; elide: Text.ElideRight; Layout.fillWidth: true }
}
