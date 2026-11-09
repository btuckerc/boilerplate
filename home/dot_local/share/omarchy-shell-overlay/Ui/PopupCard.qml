import QtQuick
import QtQuick.Shapes
import Quickshell
import Quickshell.Hyprland
import qs.Commons
import qs.Commons as Commons

// Decent-angl overlay of Omarchy's PopupCard. Packaged file is untouched;
// omarchy-launch-shell copies this into the runtime tree when enabled.
//
// Flush unstroked card. Bar-adjacent corners grow additive concave
// fillets outside the body so the popup reads as one blob with the bar.
// A side flush with the screen drops that ear and sits on the display edge.
// Since Omarchy 4.5 the bar window spans its whole screen, so placement is
// measured from the painted strip (barThickness), not the window's size.
PopupWindow {
  id: root

  required property Item anchorItem
  required property QtObject bar
  property var owner: null
  property int margin: 0
  property int padding: Style.spacing.popupPadding
  property int contentWidth: Style.space(280)
  property int contentHeight: Style.space(200)
  property color borderColor: Commons.Color.popups.border
  property var borderSpec: Border.none()
  property bool open: false
  property bool centerOnBar: false
  // "click" — uses HyprlandFocusGrab so clicking outside dismisses the popup.
  // "hover" — passive overlay; the owning widget controls open via hover.
  property string triggerMode: "click"

  readonly property var coordinatorKey: owner || root
  readonly property var anchorWindow: anchorItem ? anchorItem.QsWindow.window : null
  readonly property var popupScreen: anchorWindow ? anchorWindow.screen : null
  readonly property bool containsMouse: cardHover.hovered
  readonly property real screenW: popupScreen ? popupScreen.width : 0
  readonly property real screenH: popupScreen ? popupScreen.height : 0
  // Thickness of the painted bar strip on this screen, notch floor
  // included. The bar window spans its whole screen (only the strip inside
  // it is painted and takes input), so the window's dimensions say nothing
  // about the bar.
  readonly property real barThickness: !bar ? 0
    : (typeof bar.barSizeFor === "function" && popupScreen ? bar.barSizeFor(popupScreen.name) : bar.barSize)
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
  readonly property real availableCardWidth: screenW > 0
    ? Math.max(120, screenW - ((bar && (bar.position === "left" || bar.position === "right")) ? barThickness : 0) - root.margin * 2)
    : 0
  readonly property real availableCardHeight: screenH > 0
    ? Math.max(120, screenH - ((bar && (bar.position === "top" || bar.position === "bottom")) ? barThickness : 0) - root.margin * 2)
    : 0
  readonly property real verticalContentInset: padding * 2 + Border.top(borderSpec) + Border.bottom(borderSpec)
  // Grow-out-of-bar reveal, as in KeyboardPanel: `extent` is the card's size
  // away from the bar and always animates from what is on screen. Fixed
  // durations, since Style.duration is 0 while Hyprland animations are off.
  readonly property int openMs: 320
  readonly property int closeMs: 180
  readonly property int resizeMs: 180
  readonly property var openCurve: [0.22, 0, 0.25, 1, 1, 1]
  readonly property var closeCurve: [0.4, 0, 1, 1, 1, 1]
  readonly property real popoutMin: Math.max(Style.space(20), barJoin * 2 + 2)
  readonly property real popoutFullW: implicitWidth
  readonly property real popoutFullH: implicitHeight
  readonly property real fullExtent: Math.max(popoutMin, joinAlongX ? popoutFullH : popoutFullW)
  readonly property real extentTarget: open ? fullExtent : popoutMin
  property real extent: popoutMin
  property bool opening: false
  property real contentReveal: 0
  readonly property real popoutGrownW: joinAlongX ? popoutFullW : Math.min(popoutFullW, extent)
  readonly property real popoutGrownH: joinAlongX ? Math.min(popoutFullH, extent) : popoutFullH

  function retarget() {
    extentAnim.stop()
    var to = extentTarget
    if (Math.abs(extent - to) < 0.5) {
      extent = to
      return
    }
    extentAnim.from = extent
    extentAnim.to = to
    extentAnim.duration = !open ? closeMs : (opening ? openMs : resizeMs)
    extentAnim.easing.bezierCurve = !open ? closeCurve : openCurve
    extentAnim.start()
  }

  function startMotion() {
    opening = open
    if (open) openingWindow.restart()
    else openingWindow.stop()
    retarget()
    revealIn.stop()
    revealOut.stop()
    if (open) revealIn.start()
    else revealOut.start()
  }

  onExtentTargetChanged: retarget()

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

  function close() {
    if (owner && "close" in owner) owner.close()
    else root.open = false
  }

  function clampAlongBar(pos, span, limit) {
    return Math.max(0, Math.min(pos, limit - span))
  }

  default property alias contentItem: contentHolder.children

  visible: open || popoutClip.opacity > 0
  color: "transparent"
  // A closing card stays mapped until its fade ends; it must not take clicks
  // meant for the bar underneath while it does.
  mask: Region { item: root.open ? popoutClip : null }
  implicitWidth: contentWidth + (joinAlongX ? joinPadStart + joinPadEnd : 0)
  implicitHeight: contentHeight + (joinAlongX ? 0 : joinPadStart + joinPadEnd)

  onOpenChanged: {
    startMotion()
    if (!bar) return
    if (open) bar.requestPopout(coordinatorKey)
    else if (bar.activePopout === coordinatorKey) bar.releasePopout(coordinatorKey)
  }

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

  SequentialAnimation {
    id: revealIn
    PauseAnimation { duration: 40 }
    NumberAnimation { target: root; property: "contentReveal"; to: 1; duration: 120 }
  }
  NumberAnimation { id: revealOut; target: root; property: "contentReveal"; to: 0; duration: 60 }

  // Outside-click dismissal via Hyprland's focus grab. While `active`, input
  // is routed only to the listed windows; clicking anywhere else clears the
  // grab and we close the popup. Skipped for hover-mode popups so the cursor
  // can move freely between the trigger and the popup.
  HyprlandFocusGrab {
    active: root.open && root.triggerMode === "click"
    windows: root.anchorWindow ? [root, root.anchorWindow] : [root]
    onCleared: root.close()
  }

  anchor {
    id: popupAnchor
    window: anchorItem ? anchorItem.QsWindow.window : null
    adjustment: PopupAdjustment.Slide
    edges: Edges.Top | Edges.Left
    gravity: Edges.Bottom | Edges.Right
    rect.width: 1
    rect.height: 1

    onAnchoring: {
      if (!root.anchorItem || !root.bar) return

      var target = root.anchorItem
      var bodyW = root.contentWidth
      var bodyH = root.contentHeight
      var window = target.QsWindow.window
      if (!window) return

      var localX = target.width / 2 - bodyW / 2
      var localY = 0
      var bodyX = 0
      var bodyY = 0

      if (root.centerOnBar) {
        if (root.bar.position === "top" || root.bar.position === "bottom") {
          bodyX = root.clampAlongBar(window.width / 2 - bodyW / 2, bodyW, window.width)
          bodyY = root.bar.position === "bottom"
            ? window.height - root.barThickness - bodyH + root.barTuck
            : root.barThickness - root.barTuck
          root.joinStart = bodyX > 0.5
          root.joinEnd = bodyX + bodyW < window.width - 0.5
        } else {
          bodyX = root.bar.position === "left"
            ? root.barThickness - root.barTuck
            : window.width - root.barThickness - bodyW + root.barTuck
          bodyY = root.clampAlongBar(window.height / 2 - bodyH / 2, bodyH, window.height)
          root.joinStart = bodyY > 0.5
          root.joinEnd = bodyY + bodyH < window.height - 0.5
        }
      } else if (root.bar.position === "bottom") {
        bodyY = window.height - root.barThickness - bodyH + root.barTuck
        var mappedBottom = window.contentItem.mapFromItem(target, localX, 0)
        bodyX = root.clampAlongBar(mappedBottom.x, bodyW, window.width)
        root.joinStart = bodyX > 0.5
        root.joinEnd = bodyX + bodyW < window.width - 0.5
      } else if (root.bar.position === "left") {
        localY = target.height / 2 - bodyH / 2
        var mappedLeft = window.contentItem.mapFromItem(target, 0, localY)
        bodyX = root.barThickness - root.barTuck
        bodyY = root.clampAlongBar(mappedLeft.y, bodyH, window.height)
        root.joinStart = bodyY > 0.5
        root.joinEnd = bodyY + bodyH < window.height - 0.5
      } else if (root.bar.position === "right") {
        localY = target.height / 2 - bodyH / 2
        var mappedRight = window.contentItem.mapFromItem(target, 0, localY)
        bodyX = window.width - root.barThickness - bodyW + root.barTuck
        bodyY = root.clampAlongBar(mappedRight.y, bodyH, window.height)
        root.joinStart = bodyY > 0.5
        root.joinEnd = bodyY + bodyH < window.height - 0.5
      } else {
        var mappedTop = window.contentItem.mapFromItem(target, localX, 0)
        bodyX = root.clampAlongBar(mappedTop.x, bodyW, window.width)
        bodyY = root.barThickness - root.barTuck
        root.joinStart = bodyX > 0.5
        root.joinEnd = bodyX + bodyW < window.width - 0.5
      }

      var padS = root.joinStart ? root.barJoin : 0
      if (root.joinAlongX) {
        popupAnchor.rect.x = Math.round(bodyX - padS)
        popupAnchor.rect.y = Math.round(bodyY)
      } else {
        popupAnchor.rect.x = Math.round(bodyX)
        popupAnchor.rect.y = Math.round(bodyY - padS)
      }
    }
  }

  Item {
    id: popoutClip
    x: root.barPos === "right" ? root.popoutFullW - root.popoutGrownW : 0
    y: root.barPos === "bottom" ? root.popoutFullH - root.popoutGrownH : 0
    width: root.popoutGrownW
    height: root.popoutGrownH
    clip: true
    // Solid while open; closing, it fades over the last third of its way
    // back into the bar and reaches 0 as it lands.
    opacity: root.open ? 1
      : Math.max(0, Math.min(1, (root.extent - root.popoutMin) / Math.max(1, 0.35 * (root.fullExtent - root.popoutMin))))

    HoverHandler {
      id: cardHover
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

    Item {
      id: card
      x: root.barPos === "right" ? root.popoutGrownW - root.popoutFullW : 0
      y: root.barPos === "bottom" ? root.popoutGrownH - root.popoutFullH : 0
      width: root.popoutFullW
      height: root.popoutFullH

      readonly property real contentTopInset: root.padding + Border.top(root.borderSpec) + (root.joinAlongX ? 0 : root.joinPadStart)
      readonly property real contentRightInset: root.padding + Border.right(root.borderSpec) + (root.joinAlongX ? root.joinPadEnd : 0)
      readonly property real contentBottomInset: root.padding + Border.bottom(root.borderSpec) + (root.joinAlongX ? 0 : root.joinPadEnd)
      readonly property real contentLeftInset: root.padding + Border.left(root.borderSpec) + (root.joinAlongX ? root.joinPadStart : 0)

      Item {
        id: contentHolder
        anchors.fill: parent
        // Right-to-left languages read the card mirrored; the card itself
        // stays where the bar puts it.
        LayoutMirroring.enabled: Commons.I18n.rightToLeft
        LayoutMirroring.childrenInherit: true
        anchors.topMargin: card.contentTopInset
        anchors.rightMargin: card.contentRightInset
        anchors.bottomMargin: card.contentBottomInset
        anchors.leftMargin: card.contentLeftInset
        opacity: root.contentReveal
      }
    }
  }

  // Rounded body plus additive concave ears at the bar-adjacent corners.
  // Disabled join sides stay square so the card can sit on the screen edge.
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
