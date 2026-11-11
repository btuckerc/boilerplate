import QtQuick
import Quickshell.Io

Item {
  id: root

  property var shell: null
  property var manifest: null

  readonly property string scriptPath: {
    var dir = (manifest && manifest.__sourceDir) ? String(manifest.__sourceDir).replace(/\/$/, "") : ""
    if (dir)
      return dir + "/scripts/tune.sh"
    var s = String(Qt.resolvedUrl("../scripts/tune.sh"))
    if (s.indexOf("file://") === 0) {
      s = s.slice(7)
      if (s.indexOf("localhost/") === 0)
        s = s.substring(9)
      try { s = decodeURIComponent(s) } catch (e) {}
    }
    return s
  }
  property var status: blankStatus("not checked")
  readonly property bool active: !!(status && status.active)
  readonly property string stateLabel: active ? "on" : "off"
  property string pendingAction: ""
  property string currentAction: ""

  function blankStatus(error) {
    return {
      installed: false,
      active: false,
      sink: "",
      default: "",
      port: "",
      error: error || ""
    }
  }

  function statusJson() {
    var s = root.status || {}
    return JSON.stringify({
      installed: !!s.installed,
      active: !!s.active,
      sink: s.sink || "",
      default: s.default || "",
      port: s.port || "",
      error: s.error || ""
    })
  }

  function applyStatusText(text, fallbackError) {
    var raw = String(text || "").trim()
    if (!raw) {
      root.status = blankStatus(fallbackError || "empty status")
      return
    }
    try {
      var parsed = JSON.parse(raw)
      root.status = {
        installed: !!parsed.installed,
        active: !!parsed.active,
        sink: parsed.sink || "",
        default: parsed.default || "",
        port: parsed.port || "",
        error: parsed.error || ""
      }
    } catch (e) {
      root.status = blankStatus(fallbackError || "invalid status")
    }
  }

  function runTune(action) {
    if (tuneProcess.running) {
      pendingAction = action
      return
    }
    pendingAction = ""
    currentAction = action
    tuneProcess.command = [scriptPath, action]
    tuneProcess.running = true
  }

  function on() {
    runTune("on")
  }

  function off() {
    runTune("off")
  }

  function refresh() {
    runTune("status")
  }

  Process {
    id: existsProcess
    command: ["test", "-f", root.scriptPath]
    onExited: function(exitCode) {
      if (exitCode !== 0) {
        root.status = root.blankStatus("tune.sh is missing")
        return
      }
      root.refresh()
    }
  }

  Process {
    id: tuneProcess
    running: false
    command: []
    stdout: StdioCollector {
      id: tuneStdout
      waitForEnd: true
    }
    stderr: StdioCollector {
      id: tuneStderr
      waitForEnd: true
    }
    onExited: function(exitCode) {
      var out = String(tuneStdout.text || "")
      var err = String(tuneStderr.text || "").trim()
      var looksJson = out.trim().indexOf("{") === 0
      if (root.currentAction === "status" || looksJson) {
        root.applyStatusText(out, err || (exitCode !== 0 ? "tune.sh failed" : "empty status"))
      } else if (exitCode !== 0) {
        root.status = root.blankStatus(err || "tune.sh failed")
      } else {
        root.refresh()
        return
      }
      if (root.pendingAction) {
        var next = root.pendingAction
        root.pendingAction = ""
        root.runTune(next)
      }
    }
  }

  Component.onCompleted: existsProcess.running = true

  IpcHandler {
    target: "tux.speaker-tune"

    function on(): string {
      root.on()
      return root.statusJson()
    }

    function off(): string {
      root.off()
      return root.statusJson()
    }

    function status(): string {
      return root.statusJson()
    }

    function ping(): string {
      return "ok"
    }
  }
}
