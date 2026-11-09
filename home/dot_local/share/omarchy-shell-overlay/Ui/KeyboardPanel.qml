import QtQuick
import QtQuick.Shapes
import Quickshell
import Quickshell.Wayland
import qs.Commons
import qs.Commons as Commons

// Decent-angl overlay of Omarchy's KeyboardPanel. Packaged file is untouched;
// omarchy-shell-overlay copies this into the runtime tree.
//
// Visual: flush unstroked card that grows out of the bar. Bar-adjacent corners
// grow additive concave fillets (ears) outside the body, painted by a
// silhouette behind the card; a side flush with the screen drops its ear.
// Everything else (lazy content, morph between panels, live height) is
// Omarchy's: the grow reveal reuses the card's own crop.
// Layer-shell popup attached to a bar widget icon, designed for
// click-driven AND keyboard-driven panels (e.g. SUPER+CTRL+W summon).
//
// Built on PanelWindow with a brief WlrKeyboardFocus.Exclusive prime followed
// by OnDemand rather than PopupWindow (xdg-popup). The prime acquires focus
// both when the surface maps and when it reopens while still mapped for its
// fade-out. xdg-popups don't get that — they only receive keys after a
// click/hover routes focus through their parent surface — so keyboard-summoned
// popups fell flat without it.
//
// Exclusive would also grant map-time focus, but it makes Hyprland route
// *every* pointer event to the exclusive surface no matter which output
// the cursor is over, which leaves clicks on any other monitor unable to
// reach the dismissal surfaces below.
//
// API is a subset of Common.PopupCard: anchorItem, owner, bar, open,
// padding, margin, contentWidth/Height, centerOnBar, default contentItem.
// Missing on purpose (for now): triggerMode ("hover"), containsMouse.
//
// Positioning: full-screen layer-shell with the card placed inside at
// `cardOrigin`. We use the bar strip's thickness for the perpendicular
// axis (away-from-bar) because mapToItem on the anchor returns
// bar-content-relative coords with internal layout offsets baked in
// (e.g. ~13px from the bar's vertical centering of its widget row). The
// parallel axis (along-the-bar) uses the anchor's content x/y since the
// bar window spans the full screen on that axis.
//
// Outside-click dismissal: an overlay MouseArea catches clicks, with the
// QsWindow.mask subtracting the bar strip so clicks on the bar still
// reach the bar widgets (activePopout coordinator hands off to another
// popup if the user clicks a different bar icon).
PanelWindow {
  id: root

  required property Item anchorItem
  required property QtObject bar
  property var owner: null
  property int margin: 0
  property int padding: Style.spacing.popupPadding
  property int contentWidth: Style.space(280)
  property int contentHeight: Style.space(200)

  // The card's full height. What is on screen is `extent` below, which
  // follows this from wherever it is, so content that arrives after the panel
  // is up (a Wi-Fi scan, Bluetooth devices turning up) bends the motion rather
  // than snapping the card taller. It follows the content only while open,
  // and a tick late: panels empty their lists the moment they close (audio
  // clears its rows), in the same event as `open` turning false, and the card
  // must shrink from the size it was shown at, not collapse under it.
  property real drawnHeight: contentHeight
  onContentHeightChanged: Qt.callLater(root.followContentHeight)
  function followContentHeight() {
    if (root.open) root.drawnHeight = root.contentHeight
  }
  property var borderSpec: Border.none()
  property bool centerOnBar: false
  property bool open: false
  property int gap: 0  // flush with the bar strip
  property bool popoutSwitching: false
  property bool popoutSwitchClosing: false
  property bool focusPrimed: false

  // Item that should take keyboard focus once the panel maps. Typically a
  // PanelKeyCatcher inside the panel content. Layer-shell grants focus to the
  // surface during the Exclusive prime, but Qt still needs an active-focus
  // target inside the surface for Keys.onPressed handlers to fire. Schedule
  // the focus through Qt.callLater so it runs after the surface is fully
  // mapped and child items have completed layout.
  property Item focusTarget: null

  default property alias contentItem: contentHolder.children

  // Lazy content. A panel that sets `content` to a Component gets it built
  // the first time the panel opens instead of at shell startup, which is
  // where most of a bar's memory and load time went: every panel's tree was
  // built on every monitor whether or not it was ever opened. The content
  // stays loaded after that first open, so reopening is instant and any
  // state the content holds (scroll position, an edit in progress) survives
  // a close. Root-level panel code reaches into it through `loadedContent`,
  // which is null until then, so anything that must run while the panel is
  // closed (timers, data, IPC) belongs outside the content. Panels that
  // declare children directly keep the old eager behaviour.
  property Component content: null
  property bool contentRequested: false
  readonly property Item loadedContent: contentLoader.item
  readonly property real loadedContentHeight: contentLoader.item ? contentLoader.item.implicitHeight : 0

  // Build the content without opening the panel, for callers that need to
  // reach it first.
  function ensureContent() {
    if (content) contentRequested = true
    return contentLoader.item
  }

  readonly property var coordinatorKey: owner || root
  readonly property var anchorWindow: anchorItem ? anchorItem.QsWindow.window : null
  readonly property string barPos: bar ? bar.position : "top"
  // Overlap the bar strip by one logical pixel: at fractional scales (1.25)
  // the strip's edge lands mid-pixel and a flush card leaves a hairline seam.
  readonly property int barTuck: 1
  readonly property int barJoin: Math.max(Style.cornerRadius * 2, Style.space(10))
  readonly property int farRadius: Style.cornerRadius
  readonly property bool joinAlongX: barPos === "top" || barPos === "bottom"
  property bool joinStart: true
  property bool joinEnd: true
  readonly property int joinPadStart: joinStart ? barJoin : 0
  readonly property int joinPadEnd: joinEnd ? barJoin : 0

  // Grow-out-of-bar reveal. `extent` is the card's size away from the bar,
  // from a sliver at the bar (popoutMin) to the whole card, and always
  // animates from what is on screen: a reopen mid-close resumes, and content
  // that lands mid-grow retargets instead of jumping. The durations are fixed
  // because Style.duration is 0 while Hyprland animations are off, which keeps
  // windows instant; only this card, its content fade and the workspace marks
  // move. A switch between panels morphs instead, so it snaps there.
  // popoutMin leaves room for both ears at full size from the first frame.
  readonly property int openMs: 320
  readonly property int closeMs: 180
  readonly property int resizeMs: 180
  readonly property var openCurve: [0.22, 0, 0.25, 1, 1, 1]
  readonly property var closeCurve: [0.4, 0, 1, 1, 1, 1]
  readonly property real popoutMin: Math.max(Style.space(20), barJoin * 2 + 2)
  readonly property bool popoutMotionFrozen: popoutSwitching || popoutSwitchClosing || takingOver
  readonly property real fullExtent: Math.max(popoutMin, joinAlongX ? drawnHeight : contentWidth)
  readonly property real extentTarget: open || popoutSwitching ? fullExtent : popoutMin
  property real extent: popoutMin
  property bool opening: false
  property real contentReveal: 0

  function retarget() {
    extentAnim.stop()
    var to = extentTarget
    if (popoutMotionFrozen || Math.abs(extent - to) < 0.5) {
      extent = to
      return
    }
    var closing = !open && !popoutSwitching
    extentAnim.from = extent
    extentAnim.to = to
    extentAnim.duration = closing ? closeMs : (opening ? openMs : resizeMs)
    extentAnim.easing.bezierCurve = closing ? closeCurve : openCurve
    extentAnim.start()
  }

  function revealContent(show) {
    revealIn.stop()
    revealOut.stop()
    if (popoutMotionFrozen) contentReveal = show ? 1 : 0
    else if (show) revealIn.start()
    else revealOut.start()
  }

  onExtentTargetChanged: retarget()
  onPopoutMotionFrozenChanged: if (popoutMotionFrozen) retarget()

  NumberAnimation {
    id: extentAnim
    target: root
    property: "extent"
    easing.type: Easing.Bezier
  }

  Timer {
    id: openingWindow
    interval: root.openMs
    onTriggered: root.opening = false
  }

  // Content fades in once the card is under way. On close it goes at once:
  // panels clear their lists as they close, and a fade would show that.
  SequentialAnimation {
    id: revealIn
    PauseAnimation { duration: 40 }
    NumberAnimation { target: root; property: "contentReveal"; to: 1; duration: 120 }
  }
  NumberAnimation { id: revealOut; target: root; property: "contentReveal"; to: 0; duration: 0 }

  function close() {
    if (owner && "close" in owner) owner.close()
    else root.open = false
  }

  function beginFocusPrime() {
    if (open && backingWindowVisible) focusPrimeTimer.restart()
  }

  // --- screen + lifetime ---------------------------------------------------

  screen: anchorWindow ? anchorWindow.screen : null
  visible: open || card.opacity > 0 || popoutSwitching
  color: "transparent"
  exclusionMode: ExclusionMode.Ignore

  WlrLayershell.namespace: "omarchy-keyboard-panel"
  WlrLayershell.layer: WlrLayer.Overlay
  // Keyboard focus follows `open` (NOT `visible`). The window remains
  // mapped during the fade-out so the opacity animation has something to
  // animate, but keyboard/click ownership must release the moment the
  // logical close fires — otherwise the user is locked out until it ends.
  //
  // Prime with Exclusive on every open, then settle on OnDemand. Hyprland
  // focuses OnDemand when a surface first maps, but not when an already-mapped
  // fade-out surface changes from None back to OnDemand. Exclusive also takes
  // focus when the previously focused application has constrained the pointer.
  // The brief prime covers both cases; OnDemand then releases compositor-wide
  // pointer hit-testing so clicks can reach the dismissal windows below.
  WlrLayershell.keyboardFocus: open
    ? (focusPrimed ? WlrKeyboardFocus.OnDemand : WlrKeyboardFocus.Exclusive)
    : WlrKeyboardFocus.None

  onBackingWindowVisibleChanged: beginFocusPrime()

  // Full-screen layer-shell. The visible card is positioned inside via
  // `cardOrigin`. The `mask` below makes the bar area click-through (so
  // the user can click another bar icon while the panel is open and the
  // activePopout coordinator swaps to that popup); everywhere else, the
  // overlay catches the click and dismisses via the MouseArea below.
  anchors {
    top: true
    bottom: true
    left: true
    right: true
  }

  // Clickable region is the whole screen. Clicks in the bar strip are
  // forwarded to registered bar buttons so switching between panel icons
  // works in one click even when the overlay surface is above the bar.
  readonly property real _barStripSize: bar ? barThickness + gap : 0
  // Empty once logically closed, so the closing card never takes a click
  // meant for the windows behind it.
  mask: Region {
    width: root.open ? root.screenW : 0
    height: root.open ? root.screenH : 0
  }

  // Track every layout change between the bar's contentItem and the
  // anchor item. `transform` updates whenever any item in that chain
  // moves/resizes, which is what makes the position binding below
  // actually reactive — mapToItem on its own is a one-shot.
  TransformWatcher {
    id: anchorWatcher
    a: anchorWindow ? anchorWindow.contentItem : null
    b: anchorItem
  }

  // Anchor item's position within the bar's content surface. For a
  // full-width top bar, the content x maps directly to screen x; the y
  // returned here has the bar's internal padding baked in (e.g. ~13px
  // from vertical centering of the widget row), which is why `cardOrigin`
  // below uses `barThickness` for the perpendicular axis instead of this y.
  readonly property point anchorScreenPos: {
    anchorWatcher.transform  // reactive dependency
    if (!anchorItem || !anchorWindow) return Qt.point(0, 0)
    return anchorItem.mapToItem(anchorWindow.contentItem, 0, 0)
  }
  readonly property real anchorW: anchorItem ? anchorItem.width : 0
  readonly property real anchorH: anchorItem ? anchorItem.height : 0
  readonly property real screenW: screen ? screen.width : 0
  readonly property real screenH: screen ? screen.height : 0
  readonly property real availableCardWidth: screenW > 0
    ? Math.max(120, screenW - ((barPos === "left" || barPos === "right") ? barThickness + gap + margin : margin * 2))
    : 0
  readonly property real availableCardHeight: screenH > 0
    ? Math.max(120, screenH - ((barPos === "top" || barPos === "bottom") ? barThickness + gap + margin : margin * 2))
    : 0
  readonly property real verticalContentInset: padding * 2 + Border.top(borderSpec) + Border.bottom(borderSpec)

  function fittedContentWidth(width, cap) {
    var desired = Math.max(1, Number(width) || 1)
    var maxWidth = root.availableCardWidth > 0 ? root.availableCardWidth : desired
    if (cap !== undefined && Number(cap) > 0) maxWidth = Math.min(maxWidth, Number(cap))
    return Math.round(Math.min(desired, maxWidth))
  }

  function fittedContentHeight(implicitHeight, cap) {
    var desired = Math.max(root.verticalContentInset, (Number(implicitHeight) || 0) + root.verticalContentInset)
    var maxHeight = root.availableCardHeight > 0 ? root.availableCardHeight : desired
    if (cap !== undefined && Number(cap) > 0) maxHeight = Math.min(maxHeight, Number(cap))
    return Math.round(Math.min(desired, maxHeight))
  }

  function cappedContentHeight(height) {
    var desired = Math.max(root.padding * 2, Number(height) || root.padding * 2)
    var maxHeight = root.availableCardHeight > 0 ? root.availableCardHeight : desired
    return Math.round(Math.min(desired, maxHeight))
  }

  // Desired top-left of the card in screen coordinates. For the
  // perpendicular axis (away-from-bar) we anchor to the bar strip's edge
  // directly — not the anchor item's y/x — because mapToItem(barContent)
  // returns coordinates in the bar's content space, which can be offset
  // from the strip's screen-anchored corner by internal layout (centering
  // wrappers, padding). The bar window spans its whole screen, so its
  // dimensions say nothing about the strip; the painted strip hugs the
  // bar's anchored screen edge at the bar's thickness for this screen
  // (notch floor included), so `barThickness` gives the strip's inner edge
  // regardless of how the bar's internal widgets are positioned. For the
  // parallel axis (along the bar) the anchor item's reported position is
  // still consistent with the bar content origin, so it's accurate for
  // centering the card under the icon.
  readonly property real barThickness: !bar ? 0
    : (typeof bar.barSizeFor === "function" && screen ? bar.barSizeFor(screen.name) : bar.barSize)
  // Bar window dimensions, only for mapping overlay coordinates into
  // bar-window content coordinates in barPoint() below.
  readonly property real barW: anchorWindow ? anchorWindow.width : screenW
  readonly property real barH: anchorWindow ? anchorWindow.height : 0
  readonly property point cardOrigin: {
    if (!anchorItem || !bar) return Qt.point(margin, margin)
    var x = 0, y = 0
    if (centerOnBar && (barPos === "top" || barPos === "bottom")) {
      x = screenW / 2 - contentWidth / 2
      y = barPos === "bottom" ? screenH - barThickness - drawnHeight - gap : barThickness + gap
    } else if (centerOnBar) {
      x = barPos === "left" ? barThickness + gap : screenW - barThickness - contentWidth - gap
      y = screenH / 2 - drawnHeight / 2
    } else if (barPos === "bottom") {
      x = anchorScreenPos.x + anchorW / 2 - contentWidth / 2
      y = screenH - barThickness - drawnHeight - gap
    } else if (barPos === "left") {
      x = barThickness + gap
      y = anchorScreenPos.y + anchorH / 2 - drawnHeight / 2
    } else if (barPos === "right") {
      x = screenW - barThickness - contentWidth - gap
      y = anchorScreenPos.y + anchorH / 2 - drawnHeight / 2
    } else { // "top" (default)
      x = anchorScreenPos.x + anchorW / 2 - contentWidth / 2
      y = barThickness + gap
    }
    if (barPos === "bottom") y += barTuck
    else if (barPos === "left") x -= barTuck
    else if (barPos === "right") x += barTuck
    else y -= barTuck
    x = Math.max(margin, Math.min(x, screenW - contentWidth - margin))
    y = Math.max(margin, Math.min(y, screenH - drawnHeight - margin))
    if (joinAlongX) {
      root.joinStart = x > 0.5
      root.joinEnd = x + contentWidth < screenW - 0.5
    } else {
      root.joinStart = y > 0.5
      root.joinEnd = y + drawnHeight < screenH - 0.5
    }
    return Qt.point(Math.round(x), Math.round(y))
  }

  // Where the card grows from, in its own coordinates: the point on its
  // bar-facing edge nearest the icon it hangs from.
  readonly property point growOrigin: {
    var x = Math.max(0, Math.min(anchorScreenPos.x + anchorW / 2 - cardOrigin.x, contentWidth))
    var y = Math.max(0, Math.min(anchorScreenPos.y + anchorH / 2 - cardOrigin.y, drawnHeight))
    if (barPos === "bottom") return Qt.point(x, drawnHeight)
    if (barPos === "left") return Qt.point(0, y)
    if (barPos === "right") return Qt.point(contentWidth, y)
    return Qt.point(x, 0)
  }


  // --- popout coordination (same-bar single-popout model) -----------------

  // Coordinate on `open`, not `visible`. `visible` lags into the fade-out
  // animation, which made ownership transfer to a sibling popup race.
  onOpenChanged: {
    if (open) {
      drawnHeight = contentHeight
      if (content) contentRequested = true
      focusPrimed = false
      beginFocusPrime()
      if (focusTarget) Qt.callLater(function() {
        if (root.open && root.focusTarget) root.focusTarget.forceActiveFocus()
      })
    } else {
      focusPrimeTimer.stop()
      focusPrimed = false
    }
    if (!bar) {
      startMotion()
      return
    }
    if (open) {
      popoutSwitchClosing = false
      popoutSwitching = bar.activePopout && bar.activePopout !== coordinatorKey
      if (popoutSwitching) morphFromLastCard()
      bar.requestPopout(coordinatorKey)
      publishCard()
      if (popoutSwitching) popoutSwitchTimer.restart()
    } else {
      popoutSwitchClosing = !!(owner && owner.popoutSwitchClosing)
      popoutSwitching = false
      if (bar.activePopout === coordinatorKey) bar.releasePopout(coordinatorKey)
      if (popoutSwitchClosing) closeSwitchTimer.restart()
    }
    startMotion()
  }

  function startMotion() {
    opening = open
    if (open) openingWindow.restart()
    else openingWindow.stop()
    retarget()
    revealContent(open)
  }

  Timer {
    id: focusPrimeTimer
    // Leave enough time for multiple Qt/Wayland commit cycles after the
    // backing window becomes visible while keeping the compositor-wide
    // Exclusive phase imperceptibly short. This interval is covered by the
    // immediate hide/re-summon acceptance case.
    interval: 75
    onTriggered: if (root.open) root.focusPrimed = true
  }

  Timer {
    id: popoutSwitchTimer
    // Outlasts the morph, so the card stays shown until it has landed.
    interval: 250
    onTriggered: root.popoutSwitching = false
  }

  // --- switching between panels --------------------------------------------

  // One card, not two: a panel taking over from another in the same section of
  // the bar starts its card where the last one stood, at its size, and morphs
  // it into its own place while the new content fades in. Each panel tells the
  // bar where its card is, at the height it's drawn, so a switch while it's
  // still growing starts from what's on screen. Across sections the new panel
  // opens fresh.
  readonly property rect cardTarget: Qt.rect(cardOrigin.x, cardOrigin.y, contentWidth, drawnHeight)
  onCardTargetChanged: publishCard()

  function publishCard() {
    if (!open || !bar || !screen || typeof bar.notePopoutCard !== "function") return
    bar.notePopoutCard({ screen: screen.name, x: cardTarget.x, y: cardTarget.y,
                         width: cardTarget.width, height: cardTarget.height })
  }

  // Already true as `open` flips, before onOpenChanged marks the switch, so
  // the card never starts growing in on top of the morph. Only a takeover in
  // the same section morphs; across sections the card grows in as usual.
  readonly property bool takingOver: !!bar && !!bar.activePopout && bar.activePopout !== coordinatorKey
    && typeof bar.popoutCardFor === "function" && !!bar.popoutCardFor(coordinatorKey)

  property rect morphFrom: Qt.rect(0, 0, 0, 0)
  property real morph: 1

  function morphFromLastCard() {
    var last = bar && typeof bar.popoutCardFor === "function" ? bar.popoutCardFor(coordinatorKey) : null
    if (!last || !screen || last.screen !== screen.name) return
    morphFrom = Qt.rect(last.x, last.y, last.width, last.height)
    morphRun.restart()
  }

  NumberAnimation {
    id: morphRun
    target: root; property: "morph"; from: 0; to: 1
    duration: Style.duration(220)
    easing.type: Easing.Bezier
    easing.bezierCurve: Style.easeOut
  }

  function morphed(from, to) {
    return morph >= 1 ? to : from + (to - from) * morph
  }

  Timer {
    id: closeSwitchTimer
    interval: 1
    onTriggered: root.popoutSwitchClosing = false
  }

  // --- outside-click dismissal --------------------------------------------

  // Catches clicks anywhere in the clickable region (i.e. everywhere on
  // screen except the bar strip, which is masked out). The card has its
  // own MouseArea below so clicks on it don't bubble up here. Disabled
  // during the fade-out so the dying overlay doesn't swallow clicks that
  // were meant for the apps behind it.
  MouseArea {
    id: dismissArea
    anchors.fill: parent
    enabled: root.open
    acceptedButtons: Qt.AllButtons
    hoverEnabled: true
    property bool hoveringBar: false
    cursorShape: hoveringBar ? Qt.PointingHandCursor : Qt.ArrowCursor

    function inBarRegion(px, py) {
      if (root.barPos === "bottom") return py >= root.screenH - root._barStripSize
      if (root.barPos === "left") return px <= root._barStripSize
      if (root.barPos === "right") return px >= root.screenW - root._barStripSize
      return py <= root._barStripSize
    }

    function barPoint(px, py) {
      if (root.barPos === "bottom") return Qt.point(px, py - (root.screenH - root.barH))
      if (root.barPos === "right") return Qt.point(px - (root.screenW - root.barW), py)
      return Qt.point(px, py)
    }

    function pressTargetAt(px, py) {
      if (!root.anchorWindow || !root.anchorWindow.contentItem || !root.bar || !root.bar.clickTargets) return null
      var p = barPoint(px, py)
      var targets = root.bar.clickTargets
      for (var i = targets.length - 1; i >= 0; i--) {
        var target = targets[i]
        if (!target || !target.triggerPress || target.visible === false || target.opacity === 0 || !target.mapToItem) continue
        if (root.bar.targetBelongsToWindow && !root.bar.targetBelongsToWindow(target, root.anchorWindow)) continue
        if (Util.itemContainsPoint(target, root.anchorWindow.contentItem, p.x, p.y)) return target
      }
      return null
    }

    function forwardBarClick(px, py, button) {
      if (button !== Qt.LeftButton && button !== Qt.RightButton && button !== Qt.MiddleButton) return false
      var target = pressTargetAt(px, py)
      if (!target) return false
      target.triggerPress(button)
      return true
    }

    // This overlay takes presses on the bar strip too, so the bar button under
    // the pointer never sees itself held; it's told, for its press feedback,
    // the way the bar's own press handler tells it.
    property var heldTarget: null
    function hold(target, button) {
      if (heldTarget && heldTarget !== target && "heldButtons" in heldTarget) heldTarget.heldButtons = Qt.NoButton
      heldTarget = target && "heldButtons" in target ? target : null
      if (heldTarget) heldTarget.heldButtons = button
    }

    // Every button still down, so a second button pressed or let go mid-hold
    // leaves the first one's feedback alone.
    onPressed: function(mouse) {
      hold(root.focusPrimed && inBarRegion(mouse.x, mouse.y) ? pressTargetAt(mouse.x, mouse.y) : null, mouse.buttons)
    }
    onReleased: function(mouse) { hold(mouse.buttons ? heldTarget : null, mouse.buttons) }
    onCanceled: hold(null)
    onEnabledChanged: if (!enabled) hold(null)

    onPositionChanged: function(mouse) { hoveringBar = inBarRegion(mouse.x, mouse.y) }
    onExited: hoveringBar = false
    onClicked: function(mouse) {
      // While Exclusive is priming, Hyprland may route a click from another
      // output here with translated coordinates. Never interpret that as a
      // click on this output's bar.
      if (root.focusPrimed && inBarRegion(mouse.x, mouse.y) && forwardBarClick(mouse.x, mouse.y, mouse.button)) return
      root.close()
    }
  }

  // The panel surface only spans the anchor's screen, and the compositor
  // hit-tests pointer input per output, so `dismissArea` above can never see
  // a click on another monitor. Give every other output a transparent twin
  // whose only job is to catch that click. They exist only while the panel is
  // logically open (not during the fade-out, matching `dismissArea.enabled`).
  //
  // Keyboard focus is None: these must catch the pointer without taking focus
  // from the panel when the cursor merely crosses onto their output.
  Variants {
    model: root.open ? Quickshell.screens : []

    delegate: Component {
      PanelWindow {
        required property var modelData

        screen: modelData
        // Compare by output name: the anchor screen must be known before any
        // twin maps, or a twin would cover the panel's own output.
        visible: root.open && !!root.screen && modelData.name !== root.screen.name
        color: "transparent"
        exclusionMode: ExclusionMode.Ignore

        WlrLayershell.namespace: "omarchy-keyboard-panel-dismiss"
        WlrLayershell.layer: WlrLayer.Overlay
        WlrLayershell.keyboardFocus: WlrKeyboardFocus.None

        anchors {
          top: true
          bottom: true
          left: true
          right: true
        }

        MouseArea {
          anchors.fill: parent
          acceptedButtons: Qt.AllButtons
          onPressed: root.close()
        }
      }
    }
  }

  // --- card ----------------------------------------------------------------

  // Body plus ears, painted behind the card and following it exactly.
  Item {
    id: silhouette
    x: card.x - (root.joinAlongX ? root.joinPadStart : 0)
    y: card.y - (root.joinAlongX ? 0 : root.joinPadStart)
    width: card.width + (root.joinAlongX ? root.joinPadStart + root.joinPadEnd : 0)
    height: card.height + (root.joinAlongX ? 0 : root.joinPadStart + root.joinPadEnd)
    opacity: card.opacity
    visible: card.visible

    // Clicks on an ear belong to the card, not the dismissal overlay.
    MouseArea {
      anchors.fill: parent
      acceptedButtons: Qt.AllButtons
    }

    CardSilhouette {
      anchors.fill: parent
      edge: root.barPos
      join: root.barJoin
      far: root.farRadius
      startJoin: root.joinStart
      endJoin: root.joinEnd
      fill: Commons.Color.popups.background
    }
  }

  BorderSurface {
    id: card
    readonly property real fullW: root.morphed(root.morphFrom.width, root.contentWidth)
    readonly property real fullH: root.morphed(root.morphFrom.height, root.drawnHeight)
    x: root.morphed(root.morphFrom.x, root.cardOrigin.x) + (root.barPos === "right" ? fullW - width : 0)
    y: root.morphed(root.morphFrom.y, root.cardOrigin.y) + (root.barPos === "bottom" ? fullH - height : 0)
    width: root.joinAlongX ? fullW : Math.min(fullW, root.extent)
    height: !root.joinAlongX ? fullH : Math.min(fullH, root.extent)
    // While it morphs, grows or reveals, the content keeps its own size and
    // the card crops it.
    clip: root.morph < 1 || root.extent < root.fullExtent - 0.5 || root.drawnHeight < root.contentHeight - 0.5
    color: "transparent"
    borderSpec: root.borderSpec
    padding: root.padding
    radius: Style.cornerRadius

    // Solid while open. Closing, it fades over the last third of its way back
    // into the bar and reaches 0 as it lands, which unmaps the surface.
    opacity: root.open || root.popoutSwitching ? 1
      : Math.max(0, Math.min(1, (root.extent - root.popoutMin) / Math.max(1, 0.35 * (root.fullExtent - root.popoutMin))))

    // Swallow clicks on the card so they don't bubble to the dismissal
    // MouseArea behind us.
    MouseArea {
      anchors.fill: parent
      acceptedButtons: Qt.AllButtons
    }

    Item {
      id: contentHolder
      anchors.top: parent.top
      anchors.left: parent.left
      width: root.contentWidth - card.contentLeftInset - card.contentRightInset
      height: root.contentHeight - card.contentTopInset - card.contentBottomInset
      // Right-to-left languages read the card mirrored; the card itself
      // stays where the bar puts it.
      LayoutMirroring.enabled: Commons.I18n.rightToLeft
      LayoutMirroring.childrenInherit: true
      anchors.topMargin: card.contentTopInset + (root.barPos === "bottom" ? card.height - card.fullH : 0)
      anchors.leftMargin: card.contentLeftInset + (root.barPos === "right" ? card.width - card.fullW : 0)
      // Fades in with the morph, done by the time the card has mostly landed,
      // and with the reveal as the card grows.
      opacity: Math.min(1, root.morph * 1.6) * root.contentReveal

      Loader {
        id: contentLoader
        anchors.fill: parent
        focus: true
        active: !!root.content && (root.open || root.contentRequested)
        sourceComponent: root.content
      }

    }
  }

  component CardSilhouette: Item {
    id: sil
    required property string edge
    required property int join
    required property int far
    required property bool startJoin
    required property bool endJoin
    required property color fill

    readonly property int j: {
      if (width < 2 || height < 2) return 0
      return Math.max(0, Math.min(join, Math.floor(Math.min(width, height) / 2) - 1))
    }
    readonly property int f: {
      if (width < 2 || height < 2) return 0
      return Math.max(0, Math.min(far, Math.floor(Math.min(width, height) / 2) - 1))
    }
    readonly property bool js: startJoin && j > 0
    readonly property bool je: endJoin && j > 0
    readonly property int padS: js ? j : 0
    readonly property int padE: je ? j : 0
    readonly property bool alongX: edge !== "left" && edge !== "right"
    readonly property int bx: alongX ? padS : 0
    readonly property int by: alongX ? 0 : padS
    readonly property int bw: alongX ? width - padS - padE : width
    readonly property int bh: alongX ? height : height - padS - padE
    readonly property string bodyPath: {
      var tl = 0, tr = 0, br = 0, bl = 0
      if (edge === "bottom") { tl = f; tr = f }
      else if (edge === "left") { tr = f; br = f }
      else if (edge === "right") { tl = f; bl = f }
      else { br = f; bl = f }
      var p = "M " + (bx + tl) + "," + by
        + " L " + (bx + bw - tr) + "," + by
      if (tr) p += " A " + tr + "," + tr + " 0 0 1 " + (bx + bw) + "," + (by + tr)
      p += " L " + (bx + bw) + "," + (by + bh - br)
      if (br) p += " A " + br + "," + br + " 0 0 1 " + (bx + bw - br) + "," + (by + bh)
      p += " L " + (bx + bl) + "," + (by + bh)
      if (bl) p += " A " + bl + "," + bl + " 0 0 1 " + bx + "," + (by + bh - bl)
      p += " L " + bx + "," + (by + tl)
      if (tl) p += " A " + tl + "," + tl + " 0 0 1 " + (bx + tl) + "," + by
      return p + " Z"
    }
    readonly property string startEarPath: {
      var n = j
      if (n <= 0) return ""
      if (edge === "bottom") return "M 0," + n + " L " + n + "," + n + " L " + n + ",0 A " + n + "," + n + " 0 0 1 0," + n + " Z"
      if (edge === "left") return "M 0,0 L 0," + n + " L " + n + "," + n + " A " + n + "," + n + " 0 0 1 0,0 Z"
      if (edge === "right") return "M " + n + ",0 L " + n + "," + n + " L 0," + n + " A " + n + "," + n + " 0 0 0 " + n + ",0 Z"
      return "M 0,0 L " + n + ",0 L " + n + "," + n + " A " + n + "," + n + " 0 0 0 0,0 Z"
    }
    readonly property string endEarPath: {
      var n = j
      if (n <= 0) return ""
      if (edge === "bottom") return "M " + n + "," + n + " L 0," + n + " L 0,0 A " + n + "," + n + " 0 0 0 " + n + "," + n + " Z"
      if (edge === "left") return "M 0," + n + " L 0,0 L " + n + ",0 A " + n + "," + n + " 0 0 0 0," + n + " Z"
      if (edge === "right") return "M " + n + "," + n + " L " + n + ",0 L 0,0 A " + n + "," + n + " 0 0 1 " + n + "," + n + " Z"
      return "M " + n + ",0 L 0,0 L 0," + n + " A " + n + "," + n + " 0 0 1 " + n + ",0 Z"
    }

    Shape {
      anchors.fill: parent
      preferredRendererType: Shape.CurveRenderer
      ShapePath {
        fillColor: sil.fill
        strokeWidth: 0
        PathSvg { path: sil.bodyPath }
      }
    }

    Shape {
      visible: sil.js
      x: sil.edge === "bottom" ? sil.bx - sil.j
         : sil.edge === "left" ? sil.bx
         : sil.edge === "right" ? sil.bx + sil.bw - sil.j
         : sil.bx - sil.j
      y: sil.edge === "bottom" ? sil.by + sil.bh - sil.j
         : sil.edge === "left" || sil.edge === "right" ? sil.by - sil.j
         : sil.by
      width: sil.j
      height: sil.j
      preferredRendererType: Shape.CurveRenderer
      ShapePath {
        fillColor: sil.fill
        strokeWidth: 0
        PathSvg { path: sil.startEarPath }
      }
    }

    Shape {
      visible: sil.je
      x: sil.edge === "bottom" ? sil.bx + sil.bw
         : sil.edge === "left" ? sil.bx
         : sil.edge === "right" ? sil.bx + sil.bw - sil.j
         : sil.bx + sil.bw
      y: sil.edge === "bottom" ? sil.by + sil.bh - sil.j
         : sil.edge === "left" || sil.edge === "right" ? sil.by + sil.bh
         : sil.by
      width: sil.j
      height: sil.j
      preferredRendererType: Shape.CurveRenderer
      ShapePath {
        fillColor: sil.fill
        strokeWidth: 0
        PathSvg { path: sil.endEarPath }
      }
    }
  }
}
