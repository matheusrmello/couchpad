import QtQuick
import QtQuick.Layouts
ColumnLayout { property string title; property string description; spacing: 12
 Text { text: parent.title; color: Theme.white; font.family: Theme.family; font.pixelSize: 24; font.bold: true }
 Text { text: parent.description; color: Theme.secondary; font.family: Theme.family; font.pixelSize: 18; wrapMode: Text.WordWrap; Layout.fillWidth: true }
}
