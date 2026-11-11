import QtQuick
import qs.Commons

Item {
  id: root

  property real iconSize: Style.font.icon
  property color color: Color.foreground

  width: iconSize
  height: iconSize
  implicitWidth: iconSize
  implicitHeight: iconSize

  readonly property real pad: iconSize * 0.16
  readonly property real stroke: Math.max(1, iconSize * 1.25 / 16)
  readonly property real knob: Math.max(3, iconSize * 0.22)
  readonly property real inner: iconSize - pad * 2

  component Slider: Item {
    required property real cy
    required property real knobFrac

    width: root.iconSize
    height: root.iconSize

    Rectangle {
      x: root.pad
      y: cy - root.stroke / 2
      width: root.inner
      height: root.stroke
      radius: height / 2
      color: root.color
    }

    Rectangle {
      x: root.pad + root.inner * knobFrac - root.knob / 2
      y: cy - root.knob / 2
      width: root.knob
      height: root.knob
      radius: width / 2
      color: root.color
    }
  }

  Slider { cy: root.pad + root.inner * 0.18; knobFrac: 0.70 }
  Slider { cy: root.pad + root.inner * 0.50; knobFrac: 0.28 }
  Slider { cy: root.pad + root.inner * 0.82; knobFrac: 0.56 }
}
