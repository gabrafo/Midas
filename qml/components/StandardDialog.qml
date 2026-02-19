import QtQuick 2.15
import QtQuick.Controls 2.15
import QtQuick.Controls.Material 2.15
import QtQuick.Layouts 1.15

/** Reusable centered dialog component with primary/secondary action buttons. */
Dialog {
    id: root
    
    property string titleText: ""
    property string messageText: ""
    property string primaryButtonText: "OK"
    property string secondaryButtonText: ""
    property bool showCloseButton: false
    property int dialogWidth: 420
    
    signal primaryClicked()
    signal secondaryClicked()
    signal closeClicked()
    
    title: ""  // Using custom header instead
    modal: true
    closePolicy: Dialog.CloseOnEscape
    standardButtons: Dialog.NoButton
    
    anchors.centerIn: parent
    width: dialogWidth
    
    background: Rectangle {
        color: Qt.darker(Material.backgroundColor, 1.15)
        radius: Theme.radius.card
        border.color: Material.frameColor
        border.width: Theme.borderWidth
    }
    
    contentItem: ColumnLayout {
        spacing: 0
        width: root.dialogWidth - 40
        
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: root.titleText ? 48 : 0
            visible: root.titleText !== ""
            Layout.leftMargin: 20
            Layout.rightMargin: 20
            Layout.topMargin: 16
            
            Text {
                Layout.fillWidth: true
                text: root.titleText
                font.pointSize: 14
                font.weight: Font.Bold
                color: Material.foreground
                elide: Text.ElideRight
            }
            
            Rectangle {
                visible: root.showCloseButton
                width: 28
                height: 28
                radius: 14
                color: closeMouseArea.containsMouse ? Qt.rgba(1,1,1,0.1) : "transparent"
                
                Text {
                    anchors.centerIn: parent
                    text: "✕"
                    font.pointSize: 12
                    color: Material.foreground
                    opacity: 0.7
                }
                
                MouseArea {
                    id: closeMouseArea
                    anchors.fill: parent
                    hoverEnabled: true
                    cursorShape: Qt.PointingHandCursor
                    onClicked: {
                        root.closeClicked()
                        root.close()
                    }
                }
            }
        }
        
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            Layout.topMargin: root.titleText ? 8 : 0
            visible: root.titleText !== ""
            color: Material.frameColor
            opacity: 0.3
        }
        
        Text {
            Layout.fillWidth: true
            Layout.margins: 24
            Layout.minimumHeight: 60
            text: root.messageText
            font.pointSize: 11
            color: Material.foreground
            wrapMode: Text.Wrap
            horizontalAlignment: Text.AlignHCenter
            lineHeight: 1.4
        }
        
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 1
            color: Material.frameColor
            opacity: 0.3
        }
        
        RowLayout {
            Layout.fillWidth: true
            Layout.preferredHeight: 56
            Layout.margins: 16
            spacing: 12
            
            Item { Layout.fillWidth: true }
            
            Button {
                id: secondaryBtn
                visible: root.secondaryButtonText !== ""
                text: root.secondaryButtonText
                font.pointSize: 10
                Layout.preferredHeight: 36
                Layout.preferredWidth: Math.max(140, secondaryBtn.implicitWidth + 20)
                flat: true
                
                onClicked: {
                    root.close()
                    // Emit after close to avoid issues with stack pop()
                    Qt.callLater(function() { root.secondaryClicked() })
                }
            }
            
            Button {
                id: primaryBtn
                text: root.primaryButtonText
                font.pointSize: 10
                font.weight: Font.Bold
                Layout.preferredHeight: 36
                Layout.preferredWidth: Math.max(140, primaryBtn.implicitWidth + 20)
                Material.background: Material.accent
                Material.foreground: "#000000"
                
                onClicked: {
                    root.close()
                    // Emit after close to avoid issues with stack pop()
                    Qt.callLater(function() { root.primaryClicked() })
                }
            }
            
            Item { Layout.fillWidth: true }
        }
    }
}
