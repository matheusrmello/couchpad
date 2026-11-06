import QtQuick
Rectangle {
 property string variant: "default"
 property bool selected: false
 radius: Theme.radius
 color: variant === "success" ? "#0F2A25" : variant === "accent" ? "#1A1634" : Theme.card
 border.color: selected ? Theme.green : variant === "accent" ? "#3B2F6B" : Theme.border
 border.width: selected ? 2 : 1
 Behavior on border.color { ColorAnimation { duration: 150 } }
 Rectangle { anchors.fill: parent; anchors.margins: -3; radius: parent.radius + 3; color: "transparent"; border.width: 3; border.color: Theme.green; opacity: parent.selected ? 0.12 : 0; z: -1 }
}
