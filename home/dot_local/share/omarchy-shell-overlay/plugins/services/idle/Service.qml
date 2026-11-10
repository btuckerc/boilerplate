import QtQuick
import Quickshell
import Quickshell.Hyprland
import Quickshell.Io
import Quickshell.Services.UPower
import Quickshell.Wayland
import "IdleModel.js" as IdleModel
import qs.Commons

// Decent-angl overlay of Omarchy's idle service. Packaged file is untouched;
// omarchy-shell-overlay copies this into the runtime tree.
//
// On battery the screensaver stage uses idle.batteryScreensaver (seconds,
// default 0 = off), so an idle laptop goes straight to lock + blank. The
// 120 fps screensaver costs ~3 W on this panel, and a screensaver that exits
// on its own (a bar dropdown holding keyboard focus) cancels the pending lock,
// leaving the display lit indefinitely.
//
// On battery the idle laptop also suspends (suspend-then-hibernate, so logind's
// HibernateDelaySec applies) idle.batterySuspend seconds after the last input
// (default 360: one minute after lock + blank; 0 disables; with a lock it is at
// least lock + 10 s, since only a locked session is suspended). Any input cancels
// it, also on the lock screen. A wake without input re-suspends after
// batterySuspendRetry seconds (default 300). battery-idle-suspend declines while
// audio plays or a logind idle/sleep block inhibitor is held (protect a long job
// with `systemd-inhibit --what=idle <cmd>`); the retry tries again later.
Item {
  id: root

  // Injected by omarchy-shell (the first-party service loader).
  property var shell: null

  readonly property string home: Quickshell.env("HOME")
  readonly property string stayAwakeStateDir: home + "/.local/state/omarchy/indicators"
  readonly property string stayAwakeStatePath: stayAwakeStateDir + "/stay-awake"
  readonly property int defaultScreensaverSeconds: 150
  readonly property int defaultLockSeconds: 300
  readonly property var idleConfig: shell && shell.shellConfig && shell.shellConfig.idle
    ? shell.shellConfig.idle : (shell && shell.idleConfig ? shell.idleConfig : ({}))
  readonly property bool onBattery: UPower.onBattery
  readonly property int defaultBatteryScreensaverSeconds: 0
  readonly property int acScreensaverSeconds: secondsFromConfig(idleConfig.screensaver, defaultScreensaverSeconds)
  readonly property int batteryScreensaverSeconds: secondsFromConfig(idleConfig.batteryScreensaver, defaultBatteryScreensaverSeconds)
  readonly property int screensaverTimeoutSeconds: onBattery ? batteryScreensaverSeconds : acScreensaverSeconds
  readonly property int lockTimeoutSeconds: secondsFromConfig(idleConfig.lock, defaultLockSeconds)
  // With a lock configured the helper only suspends a locked session, so the
  // effective deadline is at least 10 s past the lock.
  readonly property int batterySuspendConfigSeconds: secondsFromConfig(idleConfig.batterySuspend, 360)
  readonly property int batterySuspendSeconds: batterySuspendConfigSeconds > 0 && lockEnabled
    ? Math.max(batterySuspendConfigSeconds, lockTimeoutSeconds + 10) : batterySuspendConfigSeconds
  readonly property int batterySuspendRetrySeconds: Math.max(60, secondsFromConfig(idleConfig.batterySuspendRetry, 300))
  readonly property bool batterySuspendEnabled: batterySuspendSeconds > 0
  readonly property bool screensaverEnabled: screensaverTimeoutSeconds > 0
  readonly property bool lockEnabled: lockTimeoutSeconds > 0
  readonly property bool idleTimersEnabled: acScreensaverSeconds > 0 || batteryScreensaverSeconds > 0 || lockEnabled
    || batterySuspendEnabled
  // The first idle point ignores the power source: changing IdleMonitor.timeout
  // recreates the compositor's idle notification and restarts the countdown, so
  // unplugging 100 s into idle would push the lock past its deadline. Each
  // cycle measures its screensaver and lock delays from this fixed point.
  readonly property int firstIdleTimeoutSeconds: IdleModel.firstIdleTimeout(IdleModel.firstIdleTimeout(
    IdleModel.firstIdleTimeout(acScreensaverSeconds, batteryScreensaverSeconds), lockTimeoutSeconds),
    batterySuspendSeconds)
  readonly property int screensaverDelaySeconds: IdleModel.delayAfterFirstIdle(screensaverTimeoutSeconds, firstIdleTimeoutSeconds)
  readonly property int lockDelaySeconds: IdleModel.delayAfterFirstIdle(lockTimeoutSeconds, firstIdleTimeoutSeconds)
  readonly property bool idleEnabled: stayAwakeStateLoaded && !stayAwake
  readonly property string screensaverClass: "org.omarchy.screensaver"

  property bool stayAwake: false
  property bool stayAwakeStateLoaded: false
  property bool hasPendingStayAwakePersist: false
  property bool pendingStayAwakePersist: false
  property bool idledThisCycle: false
  property bool screensaverStartedThisCycle: false
  property string lastEvent: "starting"
  property string lastEventAt: ""
  property var screensaverWindows: ({})
  property int screensaverWindowCount: 0
  property int lastSuspendExit: -1

  function secondsFromConfig(value, fallback) {
    return IdleModel.secondsFromConfig(value, fallback)
  }

  function nowIso() {
    return new Date().toISOString()
  }

  function logEvent(event, details) {
    var suffix = details === undefined || details === null || details === "" ? "" : ": " + String(details)
    root.lastEventAt = nowIso()
    root.lastEvent = event + suffix
    console.log("omarchy idle " + root.lastEventAt + " " + root.lastEvent)
  }

  function runProcess(process, label, command) {
    if (process.running) {
      logEvent("process-skip", label + " already running")
      return false
    }
    logEvent("process-start", label + " " + command)
    process.command = ["bash", "-lc", command]
    process.running = true
    return true
  }

  function launchScreensaver() {
    root.screensaverStartedThisCycle = true
    screensaverLaunchGraceTimer.restart()
    runProcess(screensaverProcess, "screensaver", "[[ $(omarchy-shell lock isLocked 2>/dev/null) == \"true\" ]] || omarchy-launch-screensaver")
  }

  function lockSystem(reason) {
    logEvent("lock-system", reason || "requested")
    screensaverTimer.stop()
    lockTimer.stop()
    screensaverLaunchGraceTimer.stop()
    root.idledThisCycle = false
    root.screensaverStartedThisCycle = false
    resetScreensaverWindows()
    runProcess(lockProcess, "lock", "omarchy-system-lock")
  }

  function startIdleCycle() {
    if (root.idledThisCycle) {
      logEvent("idle-cycle-already-running")
      return
    }
    // The first idle point is shared by both power sources, so on this source
    // there may be nothing to arm (e.g. battery with lock=0).
    if (!root.screensaverEnabled && !root.lockEnabled && !(root.onBattery && root.batterySuspendEnabled)) {
      logEvent("idle-cycle-skip", "no stage enabled on this power source")
      return
    }

    logEvent("idle-cycle-start", "screensaver=" + root.screensaverTimeoutSeconds + " lock=" + root.lockTimeoutSeconds)
    root.idledThisCycle = true
    root.screensaverStartedThisCycle = false
    resetScreensaverWindows()

    // Armed on either source and checked when it fires, so unplugging mid-idle
    // still suspends. lockSystem leaves it running; only input or a cancel stops
    // it, so one still running here means no input since: keep its deadline.
    if (root.batterySuspendEnabled && !suspendTimer.running)
      armSuspend(Math.max(0, root.batterySuspendSeconds - root.firstIdleTimeoutSeconds))

    // Set this cycle's deadlines once: a bound interval would restart a pending
    // timer from the moment shell.json changes, locking early or late.
    if (root.screensaverEnabled) {
      if (root.screensaverDelaySeconds === 0) launchScreensaver()
      else {
        screensaverTimer.interval = root.screensaverDelaySeconds * 1000
        screensaverTimer.restart()
      }
    }

    if (root.lockEnabled) {
      if (root.lockDelaySeconds === 0) lockSystem("lock-timeout-immediate")
      else {
        lockTimer.interval = root.lockDelaySeconds * 1000
        lockTimer.restart()
      }
    }
  }

  function armSuspend(seconds) {
    suspendTimer.interval = seconds * 1000
    suspendTimer.restart()
  }

  function stopSuspend(reason) {
    if (!suspendTimer.running && !suspendProcess.running) return
    suspendTimer.stop()
    // A helper still running its checks must not go on to suspend.
    if (suspendProcess.running) suspendProcess.running = false
    logEvent("suspend-cancel", reason)
  }

  function suspendIfStillIdle() {
    if (!root.idleEnabled || !root.batterySuspendEnabled || !root.onBattery || !idleMonitor.isIdle) {
      logEvent("suspend-skip", "enabled=" + root.idleEnabled + " battery=" + root.onBattery + " idle=" + idleMonitor.isIdle)
      return
    }
    logEvent("suspend", "battery idle")
    // battery-idle-suspend (boilerplate ~/.local/bin) declines while a logind
    // idle/sleep block inhibitor is held or audio is playing, and never asks for
    // a password. With a lock configured it only suspends a locked session, so a
    // retry after a wake the user answered without compositor input (lid open +
    // fingerprint unlock) cannot suspend a session in use.
    // exec: the helper replaces the shell, so stopSuspend's SIGTERM reaches it.
    runProcess(suspendProcess, "suspend", "exec battery-idle-suspend" + (root.lockEnabled ? " --require-locked" : ""))
    // Timers do not count suspended time. If the laptop wakes and nobody
    // touches it, try again after the retry interval.
    armSuspend(root.batterySuspendRetrySeconds)
  }

  function cancelIdleCycle(reason) {
    logEvent("idle-cycle-cancel", reason || "requested")
    stopSuspend(reason || "requested")
    screensaverTimer.stop()
    lockTimer.stop()
    screensaverLaunchGraceTimer.stop()

    if (root.idledThisCycle) runProcess(wakeProcess, "wake", "omarchy-system-wake")

    root.idledThisCycle = false
    root.screensaverStartedThisCycle = false
    resetScreensaverWindows()
  }

  function resetScreensaverWindows() {
    root.screensaverWindows = ({})
    root.screensaverWindowCount = 0
  }

  function setScreensaverWindow(address, visible) {
    var next = IdleModel.screensaverWindowsAfter(root.screensaverWindows, address, visible)
    root.screensaverWindows = next.windows
    root.screensaverWindowCount = next.count
  }

  function handleScreensaverWindowOpened(address) {
    setScreensaverWindow(address, true)
    screensaverLaunchGraceTimer.stop()
  }

  function handleScreensaverWindowClosed(address) {
    setScreensaverWindow(address, false)

    if (!root.idleEnabled || !root.idledThisCycle || !root.screensaverStartedThisCycle) return
    if (root.screensaverWindowCount > 0) return

    // The user dismissed the screensaver before the lock deadline. Treat that
    // as activity and cancel the pending lock; the lock timer is only allowed
    // to fire while the screensaver remains up.
    root.cancelIdleCycle("screensaver-dismissed")
  }

  function eventParts(event, count) {
    return IdleModel.eventParts(event, count)
  }

  function handleHyprlandEvent(event) {
    var name = String(event && event.name ? event.name : "")
    if (name === "openwindow") {
      var open = eventParts(event, 4)
      if (String(open[2] || "") === root.screensaverClass) root.handleScreensaverWindowOpened(open[0])
    } else if (name === "closewindow") {
      var close = eventParts(event, 1)
      var address = String(close[0] || "")
      if (root.screensaverWindows[address]) root.handleScreensaverWindowClosed(address)
    }
  }

  function screensaverLaunchBlip() {
    return root.idledThisCycle && root.screensaverStartedThisCycle
      && (root.screensaverWindowCount > 0 || screensaverLaunchGraceTimer.running)
  }

  function handleActiveSignal() {
    if (!root.idledThisCycle) return

    // Starting the screensaver can make the compositor report activity. Keep
    // the lock timer running once the screensaver exists (or during its short
    // launch grace); Hyprland window events cancel the cycle if it exits before
    // the normal lock deadline.
    if (root.screensaverStartedThisCycle && (root.screensaverWindowCount > 0 || screensaverLaunchGraceTimer.running)) {
      logEvent("idle-monitor-active", "screensaver cycle remains armed")
      return
    }

    cancelIdleCycle("activity")
  }

  function handleIdleChanged() {
    logEvent("idle-monitor", idleMonitor.isIdle ? "idle" : "active")
    // After the lock the cycle is over, but input on the lock screen must
    // still stop a pending suspend. The screensaver's own launch blip is not
    // input (the same exception handleActiveSignal makes).
    if (!idleMonitor.isIdle && !screensaverLaunchBlip()) stopSuspend("activity")
    if (!root.idleEnabled || !root.idleTimersEnabled) return

    if (idleMonitor.isIdle) startIdleCycle()
    else handleActiveSignal()
  }

  function statusJson() {
    return JSON.stringify({
      enabled: root.idleEnabled,
      stayAwake: root.stayAwake,
      stayAwakeStateLoaded: root.stayAwakeStateLoaded,
      stayAwakeStatePath: root.stayAwakeStatePath,
      onBattery: root.onBattery,
      idle: idleMonitor.isIdle,
      inIdleCycle: root.idledThisCycle,
      screensaverStarted: root.screensaverStartedThisCycle,
      screensaver: root.screensaverTimeoutSeconds,
      lock: root.lockTimeoutSeconds,
      screensaverDelay: root.screensaverDelaySeconds,
      lockDelay: root.lockDelaySeconds,
      batterySuspend: root.batterySuspendSeconds,
      batterySuspendRetry: root.batterySuspendRetrySeconds,
      lastSuspendExit: root.lastSuspendExit,
      screensaverWindows: root.screensaverWindowCount,
      timers: {
        screensaver: screensaverTimer.running,
        lock: lockTimer.running,
        suspend: suspendTimer.running,
        screensaverLaunchGrace: screensaverLaunchGraceTimer.running
      },
      processes: {
        screensaver: screensaverProcess.running,
        lock: lockProcess.running,
        suspend: suspendProcess.running,
        wake: wakeProcess.running
      },
      lastEvent: root.lastEvent,
      lastEventAt: root.lastEventAt
    })
  }

  function persistStayAwake(value) {
    var command = value
      ? "mkdir -p \"$HOME/.local/state/omarchy/indicators\" && touch \"$HOME/.local/state/omarchy/indicators/stay-awake\""
      : "rm -f \"$HOME/.local/state/omarchy/indicators/stay-awake\""

    if (stayAwakeStateWriter.running) {
      root.pendingStayAwakePersist = !!value
      root.hasPendingStayAwakePersist = true
      return
    }

    stayAwakeStateWriter.command = ["bash", "-lc", command]
    stayAwakeStateWriter.running = true
  }

  function refreshStayAwakeState() {
    if (!stayAwakeStateProbe.running) stayAwakeStateProbe.running = true
  }

  function applyStayAwake(value, persist, reason) {
    var enabled = !!value
    var changed = !root.stayAwakeStateLoaded || root.stayAwake !== enabled

    if (persist) persistStayAwake(enabled)

    root.stayAwake = enabled
    root.stayAwakeStateLoaded = true

    if (!changed) return enabled ? "disabled" : "enabled"

    logEvent("stay-awake", (enabled ? "enabled" : "disabled") + (reason ? " " + reason : ""))
    if (enabled) cancelIdleCycle("stay-awake")
    else Qt.callLater(root.handleIdleChanged)

    return enabled ? "disabled" : "enabled"
  }

  function setIdleEnabled(value) {
    return applyStayAwake(!value, true, "ipc")
  }

  // With both timeouts at 0 the monitor stops reporting, so nothing else would end a running cycle.
  onIdleTimersEnabledChanged: if (!idleTimersEnabled) cancelIdleCycle("idle-timers-disabled")
  onBatterySuspendEnabledChanged: if (!batterySuspendEnabled) stopSuspend("battery-suspend-disabled")

  // Unplugged while an AC screensaver is up and battery has no screensaver:
  // lock now instead of animating until the lock deadline, and so its closing
  // cannot cancel the lock.
  onOnBatteryChanged: {
    // Unplugged while already idle (no new idle transition will come): arm the
    // suspend from now.
    if (root.onBattery && root.idleEnabled && root.batterySuspendEnabled && idleMonitor.isIdle && !suspendTimer.running)
      armSuspend(root.batterySuspendSeconds)
    if (root.onBattery && root.batteryScreensaverSeconds <= 0 && root.idleEnabled && root.idledThisCycle
        && root.screensaverStartedThisCycle && root.lockEnabled)
      root.lockSystem("on-battery-during-screensaver")
  }

  IdleMonitor {
    id: idleMonitor
    enabled: root.idleEnabled && root.idleTimersEnabled
    timeout: Math.max(1, root.firstIdleTimeoutSeconds)
    respectInhibitors: true
    onIsIdleChanged: root.handleIdleChanged()
  }

  Timer {
    id: screensaverTimer
    repeat: false
    onTriggered: if (root.screensaverEnabled) root.launchScreensaver()
  }

  Timer {
    id: lockTimer
    repeat: false
    onTriggered: if (root.idleEnabled && root.idledThisCycle && root.lockEnabled) root.lockSystem("lock-timeout")
  }

  Timer {
    id: screensaverLaunchGraceTimer
    interval: 3000
    repeat: false
    onTriggered: {
      if (root.idleEnabled && root.idledThisCycle && root.screensaverStartedThisCycle && root.screensaverWindowCount === 0 && !idleMonitor.isIdle) {
        root.cancelIdleCycle("screensaver-not-running")
      }
    }
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) { root.handleHyprlandEvent(event) }
  }

  Process {
    id: screensaverProcess
    onExited: function(exitCode, exitStatus) { root.logEvent("process-exit", "screensaver exitCode=" + exitCode + " status=" + exitStatus) }
  }
  Process {
    id: lockProcess
    onExited: function(exitCode, exitStatus) { root.logEvent("process-exit", "lock exitCode=" + exitCode + " status=" + exitStatus) }
  }
  Timer {
    id: suspendTimer
    repeat: false
    onTriggered: root.suspendIfStillIdle()
  }

  Process {
    id: suspendProcess
    onExited: function(exitCode, exitStatus) {
      root.lastSuspendExit = exitCode
      root.logEvent("process-exit", "suspend exitCode=" + exitCode + " status=" + exitStatus)
      // 10 = not locked. Still idle on battery (e.g. a fingerprint unlock after a
      // wake, then nobody touched anything): lock now; the retry suspends later.
      if (exitCode === 10 && root.idleEnabled && root.onBattery && root.lockEnabled && idleMonitor.isIdle) {
        // Count the retry from now, so the next attempt cannot land seconds
        // after an unlock that preceded this refusal.
        root.armSuspend(root.batterySuspendRetrySeconds)
        root.lockSystem("suspend-needs-lock")
      }
    }
  }

  Process {
    id: wakeProcess
    onExited: function(exitCode, exitStatus) { root.logEvent("process-exit", "wake exitCode=" + exitCode + " status=" + exitStatus) }
  }

  Process {
    id: stayAwakeStateProbe
    command: ["bash", "-c", "mkdir -p \"$HOME/.local/state/omarchy/indicators\"; if [[ -f $HOME/.local/state/omarchy/indicators/stay-awake ]]; then echo yes; else echo no; fi"]
    stdout: SplitParser {
      onRead: function(line) { root.applyStayAwake(String(line).trim() === "yes", false, "state-file") }
    }
    onExited: function() { stayAwakeStateDirWatcher.reload() }
  }

  Process {
    id: stayAwakeStateWriter
    onExited: function() {
      if (root.hasPendingStayAwakePersist) {
        var pending = root.pendingStayAwakePersist
        root.hasPendingStayAwakePersist = false
        root.persistStayAwake(pending)
        return
      }

      root.refreshStayAwakeState()
    }
  }

  FileView {
    id: stayAwakeStateDirWatcher
    path: root.stayAwakeStateDir
    watchChanges: true
    printErrors: false
    onFileChanged: root.refreshStayAwakeState()
  }

  Component.onCompleted: {
    logEvent("service-ready")
    refreshStayAwakeState()
  }

  ShellIpc {
    target: "idle"

    function status(): string {
      return root.statusJson()
    }

    function debug(): string {
      return root.statusJson()
    }

    function enable(): string {
      return root.setIdleEnabled(true)
    }

    function disable(): string {
      return root.setIdleEnabled(false)
    }

    function toggle(): string {
      return root.setIdleEnabled(!root.idleEnabled)
    }
  }
}
