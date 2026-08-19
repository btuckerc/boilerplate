import Accessibility
import AppKit
import ApplicationServices
import Foundation

struct CLI {
    let args: [String]

    func contains(_ flag: String) -> Bool {
        args.contains(flag)
    }

    func value(_ flag: String, default defaultValue: String) -> String {
        guard let index = args.firstIndex(of: flag), index + 1 < args.count else {
            return defaultValue
        }
        return args[index + 1]
    }

    func intValue(_ flag: String, default defaultValue: Int) -> Int {
        Int(value(flag, default: "\(defaultValue)")) ?? defaultValue
    }
}

func jsonData(_ value: Any) -> Data {
    try! JSONSerialization.data(withJSONObject: value, options: [.prettyPrinted, .sortedKeys])
}

func emit(_ value: Any) {
    FileHandle.standardOutput.write(jsonData(value))
    FileHandle.standardOutput.write(Data([0x0a]))
}

func trustPayload(prompt: Bool, wait: Double) -> [String: Any] {
    let trustedBefore = AXIsProcessTrusted()
    var trustedAfter = trustedBefore

    if prompt {
        let options = [kAXTrustedCheckOptionPrompt.takeUnretainedValue() as String: true] as CFDictionary
        trustedAfter = AXIsProcessTrustedWithOptions(options)
        if wait > 0 {
            let deadline = Date().addingTimeInterval(wait)
            while Date() < deadline {
                if AXIsProcessTrusted() {
                    trustedAfter = true
                    break
                }
                RunLoop.current.run(until: Date().addingTimeInterval(0.25))
            }
        }
    }

    return [
        "path": CommandLine.arguments[0],
        "prompted": prompt,
        "trusted_after": trustedAfter,
        "trusted_before": trustedBefore,
    ]
}

func runningApplication(bundleID: String, activate: Bool) throws -> NSRunningApplication {
    if let app = NSRunningApplication.runningApplications(withBundleIdentifier: bundleID).first {
        if activate {
            app.activate()
            RunLoop.current.run(until: Date().addingTimeInterval(1.0))
        }
        return app
    }

    guard let url = NSWorkspace.shared.urlForApplication(withBundleIdentifier: bundleID) else {
        throw NSError(domain: "imsg-ui-helper", code: 2, userInfo: [NSLocalizedDescriptionKey: "application URL not found for \(bundleID)"])
    }
    let configuration = NSWorkspace.OpenConfiguration()
    configuration.activates = activate
    let semaphore = DispatchSemaphore(value: 0)
    var resultApp: NSRunningApplication?
    var resultError: Error?
    NSWorkspace.shared.openApplication(at: url, configuration: configuration) { app, error in
        resultApp = app
        resultError = error
        semaphore.signal()
    }
    _ = semaphore.wait(timeout: .now() + 10)
    if let error = resultError {
        throw error
    }
    guard let app = resultApp else {
        throw NSError(domain: "imsg-ui-helper", code: 1, userInfo: [NSLocalizedDescriptionKey: "application launch returned no process"])
    }
    if activate {
        app.activate()
        RunLoop.current.run(until: Date().addingTimeInterval(1.0))
    }
    return app
}

func axValue(_ element: AXUIElement, _ attribute: String) -> AnyObject? {
    var raw: CFTypeRef?
    let error = AXUIElementCopyAttributeValue(element, attribute as CFString, &raw)
    guard error == .success, let raw else {
        return nil
    }
    return raw
}

func axString(_ element: AXUIElement, _ attribute: String) -> String? {
    if let value = axValue(element, attribute) as? String, !value.isEmpty {
        return value
    }
    return nil
}

func axChildren(_ element: AXUIElement) -> [AXUIElement] {
    if let children = axValue(element, kAXChildrenAttribute as String) as? [AXUIElement] {
        return children
    }
    return []
}

func axElement(_ element: AXUIElement, _ attribute: String) -> AXUIElement? {
    var raw: CFTypeRef?
    let error = AXUIElementCopyAttributeValue(element, attribute as CFString, &raw)
    guard error == .success, let raw else {
        return nil
    }
    return unsafeBitCast(raw, to: AXUIElement.self)
}

func axActions(_ element: AXUIElement) -> [String] {
    var raw: CFArray?
    let error = AXUIElementCopyActionNames(element, &raw)
    guard error == .success, let raw else {
        return []
    }
    return raw as? [String] ?? []
}

@discardableResult
func axSetValue(_ element: AXUIElement, _ attribute: String, _ value: Any) -> AXError {
    AXUIElementSetAttributeValue(element, attribute as CFString, value as CFTypeRef)
}

@discardableResult
func axPerform(_ element: AXUIElement, _ action: String) -> AXError {
    AXUIElementPerformAction(element, action as CFString)
}

func summarize(_ value: AnyObject?) -> Any {
    guard let value else {
        return ""
    }
    switch value {
    case let string as String:
        return string
    case let number as NSNumber:
        return number
    case let array as [AnyObject]:
        return array.prefix(10).map { summarize($0) }
    case let element as AXUIElement:
        return [
            "role": axString(element, kAXRoleAttribute as String) ?? "",
            "subrole": axString(element, kAXSubroleAttribute as String) ?? "",
            "title": axString(element, kAXTitleAttribute as String) ?? "",
            "description": axString(element, kAXDescriptionAttribute as String) ?? "",
        ]
    default:
        return String(describing: value)
    }
}

func elementTextHaystack(_ element: AXUIElement) -> String {
    let parts = [
        axString(element, kAXRoleAttribute as String) ?? "",
        axString(element, kAXSubroleAttribute as String) ?? "",
        axString(element, kAXTitleAttribute as String) ?? "",
        axString(element, kAXDescriptionAttribute as String) ?? "",
        axString(element, kAXHelpAttribute as String) ?? "",
        axString(element, kAXIdentifierAttribute as String) ?? "",
        (summarize(axValue(element, kAXValueAttribute as String)) as? String) ?? "",
    ]
    return parts.joined(separator: "\n").lowercased()
}

func dumpElement(_ element: AXUIElement, depth: Int, maxDepth: Int) -> [String: Any] {
    var payload: [String: Any] = [
        "role": axString(element, kAXRoleAttribute as String) ?? "",
        "subrole": axString(element, kAXSubroleAttribute as String) ?? "",
        "title": axString(element, kAXTitleAttribute as String) ?? "",
        "value": summarize(axValue(element, kAXValueAttribute as String)),
        "description": axString(element, kAXDescriptionAttribute as String) ?? "",
        "identifier": axString(element, kAXIdentifierAttribute as String) ?? "",
        "help": axString(element, kAXHelpAttribute as String) ?? "",
        "actions": axActions(element),
    ]

    let selectedText = axString(element, kAXSelectedTextAttribute as String)
    if let selectedText, !selectedText.isEmpty {
        payload["selected_text"] = selectedText
    }

    let children = axChildren(element)
    payload["child_count"] = children.count
    if depth < maxDepth && !children.isEmpty {
        payload["children"] = children.prefix(40).map { dumpElement($0, depth: depth + 1, maxDepth: maxDepth) }
    }
    return payload
}

struct MatchResult {
    let element: AXUIElement
    let path: [Int]
    let payload: [String: Any]
}

func collectMatches(
    _ element: AXUIElement,
    depth: Int,
    maxDepth: Int,
    path: [Int],
    query: String,
    role: String,
    results: inout [MatchResult]
) {
    let queryMatches = query.isEmpty || elementTextHaystack(element).contains(query.lowercased())
    let roleMatches = role.isEmpty || (axString(element, kAXRoleAttribute as String) ?? "").caseInsensitiveCompare(role) == .orderedSame
    if queryMatches && roleMatches {
        results.append(MatchResult(element: element, path: path, payload: dumpElement(element, depth: depth, maxDepth: 1)))
    }
    guard depth < maxDepth else {
        return
    }
    for (index, child) in axChildren(element).enumerated() {
        collectMatches(child, depth: depth + 1, maxDepth: maxDepth, path: path + [index], query: query, role: role, results: &results)
    }
}

func findMessagesElements(cli: CLI) -> [String: Any] {
    let bundleID = cli.value("--bundle-id", default: "com.apple.MobileSMS")
    let activate = cli.contains("--activate")
    let maxDepth = cli.intValue("--depth", default: 7)
    let query = cli.value("--query", default: "")
    let role = cli.value("--role", default: "")

    let trust = trustPayload(prompt: false, wait: 0)
    guard (trust["trusted_after"] as? Bool) == true else {
        return [
            "status": "blocked",
            "detail": "Accessibility not granted for this helper",
            "trust": trust,
        ]
    }

    do {
        let app = try runningApplication(bundleID: bundleID, activate: activate)
        let appElement = AXUIElementCreateApplication(app.processIdentifier)
        var matches: [MatchResult] = []
        collectMatches(appElement, depth: 0, maxDepth: maxDepth, path: [], query: query, role: role, results: &matches)
        return [
            "status": "ok",
            "bundle_id": bundleID,
            "pid": app.processIdentifier,
            "count": matches.count,
            "matches": matches.prefix(80).map { match in
                var payload = match.payload
                payload["path"] = match.path
                return payload
            },
        ]
    } catch {
        return [
            "status": "error",
            "detail": String(describing: error),
            "bundle_id": bundleID,
            "trust": trust,
        ]
    }
}

func performMessagesAction(cli: CLI) -> [String: Any] {
    let bundleID = cli.value("--bundle-id", default: "com.apple.MobileSMS")
    let activate = cli.contains("--activate")
    let maxDepth = cli.intValue("--depth", default: 7)
    let query = cli.value("--query", default: "")
    let role = cli.value("--role", default: "")
    let index = cli.intValue("--index", default: 0)
    let action = cli.value("--action", default: kAXPressAction as String)
    let setValue = cli.value("--set-value", default: "")

    let trust = trustPayload(prompt: false, wait: 0)
    guard (trust["trusted_after"] as? Bool) == true else {
        return [
            "status": "blocked",
            "detail": "Accessibility not granted for this helper",
            "trust": trust,
        ]
    }

    do {
        let app = try runningApplication(bundleID: bundleID, activate: activate)
        let appElement = AXUIElementCreateApplication(app.processIdentifier)
        var matches: [MatchResult] = []
        collectMatches(appElement, depth: 0, maxDepth: maxDepth, path: [], query: query, role: role, results: &matches)
        guard index >= 0 && index < matches.count else {
            return [
                "status": "error",
                "detail": "match index out of range",
                "count": matches.count,
            ]
        }
        let match = matches[index]
        let result: AXError
        if !setValue.isEmpty {
            result = axSetValue(match.element, kAXValueAttribute as String, setValue)
        } else {
            result = axPerform(match.element, action)
        }
        return [
            "status": result == .success ? "ok" : "error",
            "ax_error": result.rawValue,
            "action": setValue.isEmpty ? action : "set-value",
            "path": match.path,
            "match": match.payload,
        ]
    } catch {
        return [
            "status": "error",
            "detail": String(describing: error),
            "bundle_id": bundleID,
            "trust": trust,
        ]
    }
}

func sendKeystroke(cli: CLI) -> [String: Any] {
    let text = cli.value("--text", default: "")
    let key = cli.value("--key", default: "")
    let flagsRaw = cli.value("--flags", default: "")
    let activate = cli.contains("--activate")
    let bundleID = cli.value("--bundle-id", default: "com.apple.MobileSMS")

    let trust = trustPayload(prompt: false, wait: 0)
    guard (trust["trusted_after"] as? Bool) == true else {
        return [
            "status": "blocked",
            "detail": "Accessibility not granted for this helper",
            "trust": trust,
        ]
    }

    do {
        _ = try runningApplication(bundleID: bundleID, activate: activate)
        let source = CGEventSource(stateID: .hidSystemState)
        var flags: CGEventFlags = []
        for part in flagsRaw.split(separator: ",").map({ $0.trimmingCharacters(in: .whitespaces) }) {
            switch part.lowercased() {
            case "command": flags.insert(.maskCommand)
            case "shift": flags.insert(.maskShift)
            case "option": flags.insert(.maskAlternate)
            case "control": flags.insert(.maskControl)
            default: break
            }
        }

        if !text.isEmpty {
            let down = CGEvent(keyboardEventSource: source, virtualKey: 0, keyDown: true)
            let up = CGEvent(keyboardEventSource: source, virtualKey: 0, keyDown: false)
            let chars = Array(text.utf16)
            down?.keyboardSetUnicodeString(stringLength: chars.count, unicodeString: chars)
            up?.keyboardSetUnicodeString(stringLength: chars.count, unicodeString: chars)
            down?.flags = flags
            up?.flags = flags
            down?.post(tap: .cghidEventTap)
            up?.post(tap: .cghidEventTap)
            return ["status": "ok", "sent": text]
        }

        let keyMap: [String: CGKeyCode] = [
            "return": 36,
            "escape": 53,
            "tab": 48,
            "up": 126,
            "down": 125,
            "left": 123,
            "right": 124,
            "space": 49,
            "f": 3,
            "r": 15,
            "c": 8,
        ]
        guard let code = keyMap[key.lowercased()] else {
            return ["status": "error", "detail": "unsupported key"]
        }
        let down = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: true)
        let up = CGEvent(keyboardEventSource: source, virtualKey: code, keyDown: false)
        down?.flags = flags
        up?.flags = flags
        down?.post(tap: .cghidEventTap)
        up?.post(tap: .cghidEventTap)
        return ["status": "ok", "key": key, "flags": flagsRaw]
    } catch {
        return ["status": "error", "detail": String(describing: error)]
    }
}

func dumpMessagesTree(cli: CLI) -> [String: Any] {
    let bundleID = cli.value("--bundle-id", default: "com.apple.MobileSMS")
    let activate = cli.contains("--activate")
    let maxDepth = cli.intValue("--depth", default: 4)

    let trust = trustPayload(prompt: false, wait: 0)
    guard (trust["trusted_after"] as? Bool) == true else {
        return [
            "status": "blocked",
            "detail": "Accessibility not granted for this helper",
            "trust": trust,
        ]
    }

    do {
        let app = try runningApplication(bundleID: bundleID, activate: activate)
        let appElement = AXUIElementCreateApplication(app.processIdentifier)
        let windows = (axValue(appElement, kAXWindowsAttribute as String) as? [AXUIElement]) ?? []
        let focusedWindow = axElement(appElement, kAXFocusedWindowAttribute as String)
        let focusedElement = axElement(appElement, kAXFocusedUIElementAttribute as String)

        return [
            "status": "ok",
            "bundle_id": bundleID,
            "pid": app.processIdentifier,
            "app": dumpElement(appElement, depth: 0, maxDepth: min(maxDepth, 2)),
            "focused_window": focusedWindow.map { dumpElement($0, depth: 0, maxDepth: maxDepth) } ?? [:],
            "focused_element": focusedElement.map { dumpElement($0, depth: 0, maxDepth: maxDepth) } ?? [:],
            "windows": windows.prefix(10).map { dumpElement($0, depth: 0, maxDepth: maxDepth) },
        ]
    } catch {
        return [
            "status": "error",
            "detail": String(describing: error),
            "bundle_id": bundleID,
            "trust": trust,
        ]
    }
}

let cli = CLI(args: Array(CommandLine.arguments.dropFirst()))
let command = cli.args.first ?? "trust"

switch command {
case "trust":
    emit(trustPayload(prompt: cli.contains("--prompt"), wait: cli.contains("--wait") ? 10.0 : 0.0))
case "dump-messages":
    emit(dumpMessagesTree(cli: cli))
case "find-messages":
    emit(findMessagesElements(cli: cli))
case "perform-messages":
    emit(performMessagesAction(cli: cli))
case "send-key":
    emit(sendKeystroke(cli: cli))
default:
    emit([
        "status": "error",
        "detail": "unknown command",
        "command": command,
    ])
}
