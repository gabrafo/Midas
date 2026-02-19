import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15

/**
 * Clickable card with icon, title, and optional subtitle.
 * Used for hub action buttons (Visualize, Typify, Export, Merge).
 */
Rectangle {
    id: root

    property string icon: ""
    property string title: ""
    property string subtitle: ""
    property bool highlighted: false
    property bool enabled: true
    property string disabledHint: ""

    signal clicked()

    color: highlighted ? Material.accent : Qt.rgba(1, 1, 1, 0.03)
    border.color: highlighted ? Material.accent : Material.frameColor
    radius: Theme.radius.card
    opacity: enabled ? 1.0 : 0.6

    MouseArea {
        id: mouse
        anchors.fill: parent
        cursorShape: root.enabled ? Qt.PointingHandCursor : Qt.ArrowCursor
        hoverEnabled: root.enabled
        onEntered: if (!root.highlighted) parent.color = Qt.rgba(1, 1, 1, 0.06)
        onExited:  if (!root.highlighted) parent.color = Qt.rgba(1, 1, 1, 0.03)
        onClicked: if (root.enabled) root.clicked()
    }

    ColumnLayout {
        anchors.centerIn: parent
        spacing: Theme.spacing.sm

        RowLayout {
            Layout.alignment: Qt.AlignHCenter
            spacing: Theme.spacing.md

            Text {
                visible: root.icon !== ""
                text: root.icon
                font.pointSize: Theme.fontSize.h1
                color: highlighted ? "#000" : Material.foreground
                opacity: highlighted ? 1.0 : 0.8
            }

            ColumnLayout {
                spacing: Theme.spacing.xs

                Text {
                    text: root.title
                    font.pointSize: Theme.fontSize.h3
                    font.weight: Font.Medium
                    color: highlighted ? "#000" : Material.foreground
                }

                Text {
                    visible: root.subtitle !== ""
                    text: root.subtitle
                    font.pointSize: Theme.fontSize.label
                    color: highlighted ? "#000" : Material.foreground
                    opacity: highlighted ? 0.8 : 0.5
                }
            }
        }

        Text {
            visible: root.disabledHint !== "" && !root.enabled
            text: root.disabledHint
            font.pointSize: Theme.fontSize.caption
            color: highlighted ? "#000" : Material.foreground
            opacity: 0.5
            Layout.alignment: Qt.AlignHCenter
        }
    }
}
