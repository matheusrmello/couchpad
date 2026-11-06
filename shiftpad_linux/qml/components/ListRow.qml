import QtQuick
import QtQuick.Layouts
RowLayout { property string title; property string description; property url iconSource; property string status; spacing: 20
 Icon { source: parent.iconSource; Layout.preferredWidth: 56; Layout.preferredHeight: 56 }
 ColumnLayout { Layout.fillWidth: true; spacing: 8
  Text { text: parent.parent.title; color: Theme.white; font.family: Theme.family; font.pixelSize: 22; font.bold: true; Layout.fillWidth: true; elide: Text.ElideRight }
  Text { text: parent.parent.description; color: Theme.secondary; font.family: Theme.family; font.pixelSize: 18; Layout.fillWidth: true; elide: Text.ElideRight }
 }
 Pill { text: parent.status; visible: text.length > 0 }
}
