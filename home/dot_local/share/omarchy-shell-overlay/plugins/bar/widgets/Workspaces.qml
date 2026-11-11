import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import qs.Commons
import qs.Ui

// Decent-angl overlay of Omarchy's Workspaces widget. Packaged file is
// untouched; omarchy-shell-overlay copies this into the runtime tree. Each
// workspace is a drawn dot, not a glyph: font metrics put a dot glyph off
// the bar's centre. Shown (this monitor's active workspace) is a 16x8 pill at
// 1, occupied an 8x8 circle at 0.55, empty the same circle at 0.3, and a
// switch morphs between them over 160 ms. Rest sizes are multiples of 4
// logical px so edges land on whole pixels at scale 1.25.
// Numbers move to tooltips.
BarWidget {
  id: root
  moduleName: "omarchy.workspaces"

  // Every monitor has workspaces 1-10 of its own, which Hyprland numbers in a
  // block of ten per monitor: 1-10, 11-20, and so on (see
  // default/hypr/monitor-workspaces.lua). Each bar shows its own monitor's block,
  // numbered 1-10, and the one that monitor shows, whichever monitor has focus.
  readonly property int slots: 10

  readonly property var monitor: {
    var window = root.QsWindow.window
    var screen = window ? window.screen : null
    return screen ? Hyprland.monitorFor(screen) : Hyprland.focusedMonitor
  }
  readonly property string monitorName: root.monitor ? root.monitor.name : ""
  // Device pixels per logical pixel, so marks can land on whole pixels.
  readonly property real monitorScale: {
    var scale = root.monitor && root.monitor.lastIpcObject ? Number(root.monitor.lastIpcObject.scale) : 1
    return scale > 0 ? scale : 1
  }

  // Connector -> block, from the file Hyprland keeps them in.
  property var blocks: ({})

  function readBlocks(text) {
    var next = {}
    var lines = String(text || "").split("\n")
    for (var i = 0; i < lines.length; i++) {
      var fields = lines[i].split("\t")
      if (fields.length >= 3 && fields[1] !== "") next[fields[1]] = parseInt(fields[0], 10)
    }
    root.blocks = next
  }

  FileView {
    path: (Quickshell.env("XDG_STATE_HOME") || Quickshell.env("HOME") + "/.local/state") + "/omarchy/monitor-workspaces"
    watchChanges: true
    printErrors: false
    onFileChanged: reload()
    onLoaded: root.readBlocks(text())
    onLoadFailed: root.readBlocks("")
  }

  function blockOf(id) {
    return Math.floor((id - 1) / root.slots)
  }

  function slotOf(id) {
    return (id - 1) % root.slots + 1
  }

  function activeWorkspaceId() {
    return root.monitor && root.monitor.activeWorkspace ? root.monitor.activeWorkspace.id : -1
  }

  // Until Hyprland has written the file, the workspace a monitor shows is in
  // its own block.
  readonly property int block: {
    var block = root.blocks[root.monitorName]
    if (block !== undefined) return block
    var active = root.activeWorkspaceId()
    return active > 0 ? root.blockOf(active) : 0
  }

  function workspaceById(id) {
    var values = Hyprland.workspaces.values
    for (var i = 0; i < values.length; i++) {
      if (values[i].id === id) return values[i]
    }

    return null
  }

  // The first five of the monitor's own, and any of the rest that exist. After
  // them come workspaces that are only visiting: those of a monitor that is
  // unplugged, which had no room to join this one's.
  function workspaceIds() {
    var base = root.block * root.slots
    var ids = [base + 1, base + 2, base + 3, base + 4, base + 5]
    var guests = []
    var values = Hyprland.workspaces.values

    for (var i = 0; i < values.length; i++) {
      var id = values[i].id
      if (id <= 0) continue
      if (root.blockOf(id) === root.block) {
        if (ids.indexOf(id) === -1) ids.push(id)
      } else if (values[i].monitor && values[i].monitor.name === root.monitorName) {
        guests.push(id)
      }
    }

    ids.sort(function(left, right) { return left - right })
    guests.sort(function(left, right) { return left - right })
    return ids.concat(guests)
  }

  // The list the marks are built from, replaced only when it really changes:
  // Hyprland's workspace model refreshes on every switch, and a new array
  // would rebuild every mark instead of letting the two that change animate.
  property var ids: []
  readonly property var liveIds: root.workspaceIds()
  onLiveIdsChanged: if (liveIds.join() !== ids.join()) ids = liveIds

  // Straight to Hyprland's socket: going through bar.run would start a login
  // shell first, which takes longer than the switch itself.
  function dispatch(expression) {
    Hyprland.dispatch(expression)
  }

  function focusWorkspace(id) {
    if (root.blockOf(id) === root.block) {
      root.dispatch("o.workspaces.focus(" + root.slotOf(id) + ", \"" + root.monitorName + "\")")
    } else {
      root.dispatch("hl.dsp.focus({ workspace = \"" + id + "\" })")
    }
  }

  // A wheel notch moves one entry along the row, and a touchpad adds up its
  // smaller deltas until they make a notch's worth.
  property real wheelAccumulator: 0

  function scrollWorkspaces(delta) {
    var wheel = Util.wheelSteps(root.wheelAccumulator, delta)
    root.wheelAccumulator = wheel.remainder
    if (wheel.steps === 0) return

    // Holds at either end rather than wrapping, so a touchpad swipe that runs
    // long stops on the last workspace.
    var ids = root.workspaceIds()
    var index = ids.indexOf(root.activeWorkspaceId())
    if (index === -1) return
    var target = ids[Util.clamp(index - wheel.steps, 0, ids.length - 1)]
    if (target !== ids[index]) root.focusWorkspace(target)
  }

  // The layout commands act on the focused workspace, so a click on another
  // monitor's bar focuses that monitor first.
  function cycleLayout() {
    if (!root.bar) return
    var command = "omarchy-hyprland-workspace-layout-toggle"
    if (root.monitor && !root.monitor.focused) {
      command = "hyprctl dispatch " + Util.shellQuote("hl.dsp.focus({ monitor = \"" + root.monitorName + "\" })") + " >/dev/null && " + command
    }
    root.bar.run(command)
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) {
      var name = event ? String(event.name) : ""
      // Quickshell credits every workspace switch to the focused monitor, as
      // the event doesn't say which one switched, and misses the workspace a
      // monitor falls back to when its own is moved away. Moving workspaces
      // between monitors switches the others, so ask Hyprland for the truth.
      // A workspace that changes number is only learned by asking too. Every
      // bar shares what Hyprland answers, so one asks after a plain switch.
      var switched = name === "workspacev2" && root.monitor !== null && root.monitor.focused
      if (switched || name === "moveworkspacev2" || name === "changeworkspaceid") {
        Hyprland.refreshMonitors()
        Hyprland.refreshWorkspaces()
      }
    }
  }

  // Omarchy's layout scripts still call this after Super + L. The marks no
  // longer show the layout, so there is nothing to read; the target stays so
  // those calls keep succeeding.
  ShellIpc {
    target: "omarchy.workspaces"

    function refresh(): void {}
  }

  readonly property real trailingGap: 0

  implicitWidth: grid.implicitWidth + trailingGap
  implicitHeight: grid.implicitHeight

  GridLayout {
    id: grid
    anchors.fill: parent
    anchors.rightMargin: root.trailingGap
    columns: root.vertical ? 1 : root.ids.length
    columnSpacing: 0
    rowSpacing: root.vertical ? Style.space(2) : 0

    Repeater {
      model: root.ids

      WidgetButton {
        required property int modelData

        readonly property var workspace: root.workspaceById(modelData)
        readonly property bool occupied: workspace !== null && workspace.toplevels.values.length > 0
        readonly property bool shown: root.monitor !== null && root.monitor.activeWorkspace !== null && root.monitor.activeWorkspace.id === modelData
        readonly property int slot: root.slotOf(modelData)
        readonly property bool firstGuest: root.blockOf(modelData) !== root.block && index > 0 && root.blockOf(root.ids[index - 1]) === root.block
        required property int index

        // A gap sets visiting workspaces apart from the monitor's own.
        Layout.leftMargin: firstGuest && !root.vertical ? 8 : 0
        Layout.topMargin: firstGuest && root.vertical ? 8 : 0

        bar: root.bar
        text: ""
        labelVisible: false
        hasVisualContent: true
        tooltipText: "Workspace " + (slot === root.slots ? "0" : String(slot))
        fixedWidth: root.vertical ? root.barSize : 24
        fixedHeight: root.vertical ? 24 : root.barSize
        onPressed: function() {
          if (shown) root.cycleLayout()
          else root.focusWorkspace(modelData)
        }
        onWheelMoved: function(delta) { root.scrollWorkspaces(delta) }

        // The mark morphs in place: on a switch the old pill shrinks to a
        // circle as the new circle stretches into the pill, each from what is
        // on screen, so quick switches retarget instead of queueing. Its
        // length snaps to an even number of device pixels and its corner to a
        // whole one, so it stays centred at every frame. The corner radius is
        // half the short side, so any thickness or length stays fully round.
        Rectangle {
          readonly property real dpr: root.monitorScale
          property real active: shown ? 1 : 0
          Behavior on active {
            NumberAnimation { duration: 160; easing.type: Easing.Bezier; easing.bezierCurve: [0.2, 0, 0.2, 1, 1, 1] }
          }
          readonly property real span: 2 * Math.round((8 + 8 * active) * dpr / 2) / dpr
          width: root.vertical ? 8 : span
          height: root.vertical ? span : 8
          x: Math.round((parent.width - width) / 2 * dpr) / dpr
          y: Math.round((parent.height - height) / 2 * dpr) / dpr
          radius: Math.min(width, height) / 2
          antialiasing: true
          color: parent.foreground
          opacity: shown ? 1 : (occupied ? 0.55 : 0.3)
          Behavior on opacity {
            NumberAnimation { duration: 160; easing.type: Easing.Bezier; easing.bezierCurve: [0.2, 0, 0.2, 1, 1, 1] }
          }
        }
      }
    }
  }
}
