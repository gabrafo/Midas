import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15

/**
 * Reusable panel with optional title and styled border.
 * Use as a container for logically grouped UI sections.
 */
Rectangle {
    id: root

    property string title: ""
    default property alias content: contentColumn.data

    color: Qt.rgba(1, 1, 1, 0.03)
    border.color: Material.frameColor
    border.width: Theme.borderWidth
    radius: Theme.radius.card

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        anchors.margins: Theme.spacing.md
        spacing: Theme.spacing.sm

        Text {
            visible: root.title !== ""
            text: root.title
            font.pointSize: Theme.fontSize.subtitle
            font.weight: Font.Bold
            color: Material.foreground
            Layout.fillWidth: true
        }
    }
}
