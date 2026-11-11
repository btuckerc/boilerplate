import QtQuick
import QtQuick.Controls
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui

Panel {
  id: root
  moduleName: "tux.speaker-tune"
  manageIpc: false

  readonly property var service: bar && bar.shell ? bar.shell.serviceFor("tux.speaker-tune") : null
  readonly property bool active: service ? !!service.active : false
  readonly property color foreground: bar ? bar.foreground : Color.foreground
  readonly property color dim: Qt.darker(foreground, 1.55)
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property var status: service && service.status ? service.status : null
  readonly property string portLabel: {
    var port = status && status.port ? String(status.port) : ""
    if (port === "analog-output-speaker") return "speakers"
    if (port === "analog-output-headphones") return "headphones"
    return port || "none"
  }
  readonly property string errorText: status && status.error ? String(status.error) : ""

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  onOpenedChanged: if (opened) {
    if (service) service.refresh()
    Qt.callLater(function() { keyCatcher.forceActiveFocus() })
  }

  IpcHandler {
    target: "tux.speaker-tune.panel"

    function open(): void { root.open() }
    function close(): void { root.close() }
    function toggle(): void { root.toggle() }
    function show(): void { root.open() }
    function hide(): void { root.close() }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: ""
    iconComponent: Component {
      TuneIcon {
        iconSize: Style.bar.iconCanvas
        color: button.foreground
      }
    }
    active: root.active
    tooltipText: "Speaker tune"
    onPressed: function(b) {
      if (b === Qt.LeftButton || b === Qt.RightButton)
        root.toggle()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(380))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onActivateRequested: if (root.service) root.service.refresh()
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }
      onTextKey: function(t) {
        if ((t === "r" || t === "R") && root.service) root.service.refresh()
      }

      Flickable {
        id: panelFlick
        anchors.fill: parent
        contentWidth: width
        contentHeight: column.implicitHeight
        clip: true
        boundsBehavior: Flickable.StopAtBounds
        flickableDirection: Flickable.VerticalFlick
        interactive: contentHeight > height
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        Column {
          id: column
          width: panelFlick.width
          spacing: Style.space(12)

          Item {
            id: header
            width: parent.width
            implicitHeight: hero.implicitHeight

            PanelHero {
              id: hero
              width: parent.width
              title: "Speaker tune"
              meta: root.active ? "ON" : "OFF"
              foreground: root.foreground
              fontFamily: root.fontFamily
              iconComponent: Component {
                TuneIcon {
                  iconSize: Style.font.display
                  color: root.foreground
                }
              }
              trailingControl: Component {
                ToggleSwitch {
                  checked: root.active
                  foreground: hero.foreground
                  onToggled: {
                    if (!root.service) return
                    if (root.active) root.service.off()
                    else root.service.on()
                  }
                }
              }
            }
          }

          PanelSeparator {
            foreground: root.foreground
          }

          Column {
            width: parent.width
            spacing: Style.space(8)

            PanelSectionHeader {
              width: parent.width
              text: "STATUS"
              foreground: root.foreground
              fontFamily: root.fontFamily
            }

            Column {
              width: parent.width
              spacing: Style.space(2)

              Text {
                width: parent.width
                text: "Port"
                color: root.dim
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
              }

              Text {
                width: parent.width
                text: root.portLabel
                color: root.foreground
                font.family: root.fontFamily
                font.pixelSize: Style.font.body
                elide: Text.ElideRight
              }
            }

            Text {
              visible: root.errorText !== ""
              width: parent.width
              text: root.errorText
              color: root.dim
              font.family: root.fontFamily
              font.pixelSize: Style.font.body
              wrapMode: Text.Wrap
            }
          }

          PanelSeparator {
            foreground: root.foreground
          }

          Column {
            width: parent.width
            spacing: Style.space(8)

            PanelSectionHeader {
              width: parent.width
              text: "TUNING"
              foreground: root.foreground
              fontFamily: root.fontFamily
            }

            PanelActionButton {
              iconText: "󰑐"
              tooltipText: "Refresh"
              foreground: root.foreground
              fontFamily: root.fontFamily
              onClicked: if (root.service) root.service.refresh()
            }
          }
        }
      }
    }
  }
}
