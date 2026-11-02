// Kerf Studio for macOS: a native single-window app around the local Kerf Studio server.
// One process = one window = one Dock icon. Clicking the Dock icon while it runs just brings the window forward.
// Closing the window (or Cmd+Q) quits the app AND the engine, asking first if a job is still running.
// Built by tools/mac/install_app.sh:  swiftc -O KerfStudio.swift -framework Cocoa -framework WebKit
import Cocoa
import WebKit
import UserNotifications

final class App: NSObject, NSApplicationDelegate, NSWindowDelegate, WKNavigationDelegate, WKUIDelegate, WKScriptMessageHandler,
                 UNUserNotificationCenterDelegate {
    let repo = Bundle.main.object(forInfoDictionaryKey: "KerfRepo") as? String ?? ""
    var window: NSWindow!
    var web: WKWebView!
    var popups: [NSWindow] = []
    var server: Process?
    var base = URL(string: "http://127.0.0.1:8765/")!
    var log: FileHandle?
    var loaded = false, starting = false, quitting = false, fails = 0
    var outBuf = ""                 // server output not yet split into lines (main thread only)

    // MARK: launch
    func applicationDidFinishLaunching(_ n: Notification) {
        let me = NSRunningApplication.current
        if let other = NSRunningApplication.runningApplications(withBundleIdentifier: Bundle.main.bundleIdentifier ?? "")
            .first(where: { $0.processIdentifier != me.processIdentifier }) {
            other.activate(options: [.activateAllWindows])   // already open: bring that one forward, never a second copy
            exit(0)
        }
        openLog()
        let center = UNUserNotificationCenter.current()     // job notifications that open the right view when clicked
        center.delegate = self
        center.requestAuthorization(options: [.alert, .sound]) { _, _ in }
        buildMenu()
        makeWindow()
        status("Starting Kerf Studio…")
        ping { ok in if ok { self.load() } else { self.startServer() } }
        Timer.scheduledTimer(withTimeInterval: 5, repeats: true) { _ in self.health() }
        NSWorkspace.shared.notificationCenter.addObserver(forName: NSWorkspace.didWakeNotification, object: nil, queue: .main) { _ in self.health() }
    }

    func applicationShouldHandleReopen(_ s: NSApplication, hasVisibleWindows: Bool) -> Bool {
        window.makeKeyAndOrderFront(nil)                       // Dock click while running: show the one window
        return true
    }

    func makeWindow() {
        window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1440, height: 920),
                          styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        window.title = "Kerf Studio"
        window.minSize = NSSize(width: 900, height: 600)
        window.backgroundColor = NSColor(red: 0.07, green: 0.07, blue: 0.08, alpha: 1)
        window.delegate = self
        window.center()
        window.setFrameAutosaveName("KerfStudioMain")
        let cfg = WKWebViewConfiguration()
        let ucc = WKUserContentController()
        ucc.add(self, name: "kerf")
        // the page's own Quit button calls window.close(); route it to a real app quit
        ucc.addUserScript(WKUserScript(source: "window.close = () => window.webkit.messageHandlers.kerf.postMessage('close');",
                                       injectionTime: .atDocumentStart, forMainFrameOnly: true))
        cfg.userContentController = ucc
        cfg.preferences.setValue(true, forKey: "developerExtrasEnabled")
        web = WKWebView(frame: .zero, configuration: cfg)
        web.navigationDelegate = self
        web.uiDelegate = self
        web.setValue(false, forKey: "drawsBackground")
        window.contentView = web
        window.makeKeyAndOrderFront(nil)
        NSApp.activate(ignoringOtherApps: true)
    }

    // MARK: server
    func openLog() {
        let url = FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("Library/Logs/KerfStudio.log")
        if !FileManager.default.fileExists(atPath: url.path) { FileManager.default.createFile(atPath: url.path, contents: nil) }
        log = try? FileHandle(forWritingTo: url)
        log?.seekToEndOfFile()
    }

    func ping(_ done: @escaping (Bool) -> Void) {
        var r = URLRequest(url: base.appendingPathComponent("api/jobs"))
        r.timeoutInterval = 2
        URLSession.shared.dataTask(with: r) { _, resp, _ in
            let ok = (resp as? HTTPURLResponse)?.statusCode == 200
            DispatchQueue.main.async { done(ok) }
        }.resume()
    }

    func startServer() {
        guard !starting, !quitting else { return }
        starting = true
        let p = Process()
        p.executableURL = URL(fileURLWithPath: "/bin/bash")
        p.arguments = ["\(repo)/tools/mac/start.sh", repo]
        let pipe = Pipe()
        p.standardOutput = pipe
        p.standardError = pipe
        outBuf = ""
        pipe.fileHandleForReading.readabilityHandler = { h in   // runs on a background thread
            let d = h.availableData
            if d.isEmpty { h.readabilityHandler = nil; return }
            DispatchQueue.main.async { self.serverOutput(d) }
        }
        p.terminationHandler = { proc in
            DispatchQueue.main.async {
                self.server = nil; self.starting = false
                if !self.quitting && !self.loaded {
                    self.status("Kerf Studio couldn't start (exit \(proc.terminationStatus)).",
                                detail: "Details are in ~/Library/Logs/KerfStudio.log", retry: true)
                }
            }
        }
        do { try p.run(); server = p } catch {
            starting = false
            status("Couldn't run the start script.", detail: "\(repo)/tools/mac/start.sh — \(error.localizedDescription)", retry: true)
        }
    }

    func serverOutput(_ d: Data) {
        log?.write(d)
        outBuf += String(decoding: d, as: UTF8.self)
        while let nl = outBuf.firstIndex(of: "\n") {
            let line = String(outBuf[..<nl]); outBuf = String(outBuf[outBuf.index(after: nl)...])
            serverLine(line)
        }
    }

    func serverLine(_ line: String) {
        if line.hasPrefix("STATUS ") { status(String(line.dropFirst(7))) }
        if line.hasPrefix("ERROR ") { status(String(line.dropFirst(6)), retry: true) }
        if let r = line.range(of: "Kerf Studio running at "), let u = URL(string: line[r.upperBound...]
            .split(separator: " ").first.map(String.init) ?? "") {
            base = u; starting = false; load()
        }
    }

    func load() {
        loaded = true; fails = 0
        web.load(URLRequest(url: base))
    }

    // the engine stopped while the window is open (crash, or the Mac slept long): start it again and reconnect
    func health() {
        guard loaded, !quitting, !starting else { return }
        ping { ok in
            if ok { self.fails = 0; return }
            self.fails += 1
            if self.fails >= 2 { self.loaded = false; self.status("Reconnecting…"); self.startServer() }
        }
    }

    func status(_ msg: String, detail: String = "", retry: Bool = false) {
        let esc = { (s: String) in s.replacingOccurrences(of: "&", with: "&amp;").replacingOccurrences(of: "<", with: "&lt;") }
        let html = """
        <html><body style="margin:0;height:100vh;display:flex;align-items:center;justify-content:center;background:#121214;
        color:#e8e6e3;font:15px -apple-system,system-ui"><div style="text-align:center">
        <div style="width:64px;height:64px;margin:0 auto 18px;border-radius:18px;background:linear-gradient(135deg,#ff9b3d,#ff6a1a);
        display:flex;align-items:center;justify-content:center"><svg width="32" height="32" viewBox="0 0 30 30"><path d="M8 24V6m0 9 11-9m-7 6 9 12"
        stroke="#160a03" stroke-width="3.6" fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg></div>
        <div style="font-size:17px;font-weight:600">\(esc(msg))</div>
        <div style="opacity:.6;margin-top:8px">\(esc(detail))</div>
        \(retry ? "<a href=\"kerfapp://retry\" style=\"display:inline-block;margin-top:18px;padding:8px 18px;border-radius:8px;background:#ff7a1a;color:#160a03;text-decoration:none;font-weight:600\">Try again</a>" : "")
        </div></body></html>
        """
        web.loadHTMLString(html, baseURL: nil)
    }

    // MARK: quitting — one path for the red close button, Cmd+Q, Cmd+W and the page's own Quit button
    func windowShouldClose(_ w: NSWindow) -> Bool {
        if w == window { NSApp.terminate(nil); return false }
        popups.removeAll { $0 == w }
        return true
    }

    func applicationShouldTerminate(_ s: NSApplication) -> NSApplication.TerminateReply {
        if quitting { return .terminateNow }
        quitting = true
        postQuit(force: false) { code, running in
            if code == 409 {
                let a = NSAlert()
                a.messageText = "Still running"
                a.informativeText = running.map { "• \($0)" }.joined(separator: "\n") + "\n\nStop and quit?"
                a.addButton(withTitle: "Stop and Quit")
                a.addButton(withTitle: "Cancel")
                if a.runModal() == .alertFirstButtonReturn {
                    self.postQuit(force: true) { _, _ in self.finishQuit() }
                } else {
                    self.quitting = false
                    NSApp.reply(toApplicationShouldTerminate: false)
                }
            } else { self.finishQuit() }
        }
        return .terminateLater
    }

    func postQuit(force: Bool, _ done: @escaping (Int, [String]) -> Void) {
        var r = URLRequest(url: base.appendingPathComponent("api/quit"))
        r.httpMethod = "POST"; r.timeoutInterval = 3
        r.setValue("application/json", forHTTPHeaderField: "Content-Type")
        r.httpBody = force ? Data("{\"force\": true}".utf8) : Data("{}".utf8)
        URLSession.shared.dataTask(with: r) { data, resp, _ in
            let code = (resp as? HTTPURLResponse)?.statusCode ?? 0
            let running = (data.flatMap { try? JSONSerialization.jsonObject(with: $0) } as? [String: Any])?["running"] as? [String] ?? []
            DispatchQueue.main.async { done(code, running) }
        }.resume()
    }

    func finishQuit() {
        // the server shuts itself down after /api/quit; make sure our child is gone either way
        let deadline = Date().addingTimeInterval(3)
        while let p = server, p.isRunning, Date() < deadline { RunLoop.current.run(until: Date().addingTimeInterval(0.1)) }
        if let p = server, p.isRunning { p.terminate() }
        NSApp.reply(toApplicationShouldTerminate: true)
    }

    func userContentController(_ c: WKUserContentController, didReceive m: WKScriptMessage) {
        if (m.body as? String) == "close" { NSApp.terminate(nil); return }
        // {title, body, target} from the page: a desktop notification; clicking it calls the page's kerfOpen(target)
        if let d = m.body as? [String: Any], let title = d["title"] as? String {
            let content = UNMutableNotificationContent()
            content.title = "Kerf Studio"
            content.subtitle = title
            content.body = (d["body"] as? String) ?? ""
            content.sound = .default
            content.userInfo = ["target": (d["target"] as? String) ?? ""]
            let req = UNNotificationRequest(identifier: UUID().uuidString, content: content, trigger: nil)
            UNUserNotificationCenter.current().add(req) { _ in }
        }
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter, didReceive response: UNNotificationResponse,
                                withCompletionHandler completionHandler: @escaping () -> Void) {
        let target = (response.notification.request.content.userInfo["target"] as? String) ?? ""
        DispatchQueue.main.async {
            NSApp.activate(ignoringOtherApps: true)
            self.window.makeKeyAndOrderFront(nil)
            if let data = try? JSONSerialization.data(withJSONObject: [target]), let arg = String(data: data, encoding: .utf8) {
                self.web.evaluateJavaScript("window.kerfOpen && window.kerfOpen(\(arg)[0])", completionHandler: nil)
            }
            completionHandler()
        }
    }

    func userNotificationCenter(_ center: UNUserNotificationCenter, willPresent notification: UNNotification,
                                withCompletionHandler completionHandler: @escaping (UNNotificationPresentationOptions) -> Void) {
        completionHandler([])        // the window is in front: its own clickable pop-up already shows it
    }

    // MARK: browser behaviour a real app needs
    func webView(_ w: WKWebView, decidePolicyFor a: WKNavigationAction, decisionHandler: @escaping (WKNavigationActionPolicy) -> Void) {
        guard let url = a.request.url else { return decisionHandler(.allow) }
        if url.scheme == "kerfapp" { decisionHandler(.cancel); status("Starting Kerf Studio…"); return startServer() }
        var isDownload = false
        if #available(macOS 11.3, *) { isDownload = a.shouldPerformDownload }
        if isDownload { decisionHandler(.cancel); return download(url) }
        if let host = url.host, host != base.host, ["http", "https"].contains(url.scheme ?? ""), a.targetFrame?.isMainFrame ?? true {
            decisionHandler(.cancel); NSWorkspace.shared.open(url); return   // outside links open in the normal browser
        }
        decisionHandler(.allow)
    }

    func webView(_ w: WKWebView, decidePolicyFor r: WKNavigationResponse, decisionHandler: @escaping (WKNavigationResponsePolicy) -> Void) {
        if !r.canShowMIMEType, let url = r.response.url { decisionHandler(.cancel); return download(url) }
        decisionHandler(.allow)
    }

    func download(_ url: URL) {
        URLSession.shared.downloadTask(with: url) { tmp, resp, err in
            DispatchQueue.main.async {
                guard let tmp = tmp, err == nil else { return self.alert("Download failed", err?.localizedDescription ?? "") }
                let fm = FileManager.default
                let dir = fm.urls(for: .downloadsDirectory, in: .userDomainMask)[0]
                let name = resp?.suggestedFilename ?? url.lastPathComponent
                var dest = dir.appendingPathComponent(name)
                var i = 2
                while fm.fileExists(atPath: dest.path) {
                    let stem = (name as NSString).deletingPathExtension, ext = (name as NSString).pathExtension
                    dest = dir.appendingPathComponent("\(stem) \(i)" + (ext.isEmpty ? "" : ".\(ext)")); i += 1
                }
                do { try fm.moveItem(at: tmp, to: dest); NSWorkspace.shared.activateFileViewerSelecting([dest]) }
                catch { self.alert("Download failed", error.localizedDescription) }
            }
        }.resume()
    }

    // target=_blank / window.open: our own pages get their own window, other sites open in the normal browser
    func webView(_ w: WKWebView, createWebViewWith cfg: WKWebViewConfiguration, for a: WKNavigationAction, windowFeatures f: WKWindowFeatures) -> WKWebView? {
        guard let url = a.request.url else { return nil }
        if url.host != base.host { NSWorkspace.shared.open(url); return nil }
        let win = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1200, height: 800),
                           styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
        let v = WKWebView(frame: .zero, configuration: cfg)
        v.navigationDelegate = self; v.uiDelegate = self
        win.contentView = v; win.delegate = self; win.title = "Kerf Studio"
        win.isReleasedWhenClosed = false
        win.cascadeTopLeft(from: window.frame.origin); win.makeKeyAndOrderFront(nil)
        popups.append(win)
        return v
    }

    func webViewDidClose(_ v: WKWebView) {
        if v == web { NSApp.terminate(nil) } else { v.window?.close() }
    }

    func webView(_ w: WKWebView, runJavaScriptAlertPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping () -> Void) {
        alert("Kerf Studio", m); completionHandler()
    }

    func webView(_ w: WKWebView, runJavaScriptConfirmPanelWithMessage m: String, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping (Bool) -> Void) {
        let a = NSAlert(); a.messageText = "Kerf Studio"; a.informativeText = m
        a.addButton(withTitle: "OK"); a.addButton(withTitle: "Cancel")
        completionHandler(a.runModal() == .alertFirstButtonReturn)
    }

    func webView(_ w: WKWebView, runJavaScriptTextInputPanelWithPrompt p: String, defaultText d: String?, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping (String?) -> Void) {
        let a = NSAlert(); a.messageText = "Kerf Studio"; a.informativeText = p
        let field = NSTextField(frame: NSRect(x: 0, y: 0, width: 320, height: 24)); field.stringValue = d ?? ""
        a.accessoryView = field; a.addButton(withTitle: "OK"); a.addButton(withTitle: "Cancel")
        completionHandler(a.runModal() == .alertFirstButtonReturn ? field.stringValue : nil)
    }

    func webView(_ w: WKWebView, runOpenPanelWith p: WKOpenPanelParameters, initiatedByFrame f: WKFrameInfo, completionHandler: @escaping ([URL]?) -> Void) {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = p.allowsMultipleSelection
        panel.canChooseDirectories = p.allowsDirectories
        panel.canChooseFiles = true
        completionHandler(panel.runModal() == .OK ? panel.urls : nil)
    }

    func alert(_ t: String, _ m: String) {
        let a = NSAlert(); a.messageText = t; a.informativeText = m; a.runModal()
    }

    // MARK: menu (without an Edit menu, Cmd+C / Cmd+V do nothing in a web view)
    func buildMenu() {
        let main = NSMenu()
        func sub(_ title: String, _ items: [NSMenuItem]) {
            let m = NSMenu(title: title); items.forEach { m.addItem($0) }
            let it = NSMenuItem(); it.submenu = m; main.addItem(it)
        }
        func item(_ t: String, _ s: Selector?, _ k: String, _ mods: NSEvent.ModifierFlags = .command) -> NSMenuItem {
            let i = NSMenuItem(title: t, action: s, keyEquivalent: k); i.keyEquivalentModifierMask = mods; return i
        }
        let reload = item("Reload", #selector(reloadPage), "r"); reload.target = self
        sub("Kerf Studio", [item("About Kerf Studio", #selector(NSApplication.orderFrontStandardAboutPanel(_:)), ""), .separator(),
                            item("Hide Kerf Studio", #selector(NSApplication.hide(_:)), "h"),
                            item("Hide Others", #selector(NSApplication.hideOtherApplications(_:)), "h", [.command, .option]), .separator(),
                            item("Quit Kerf Studio", #selector(NSApplication.terminate(_:)), "q")])
        sub("Edit", [item("Undo", Selector(("undo:")), "z"), item("Redo", Selector(("redo:")), "z", [.command, .shift]), .separator(),
                     item("Cut", #selector(NSText.cut(_:)), "x"), item("Copy", #selector(NSText.copy(_:)), "c"),
                     item("Paste", #selector(NSText.paste(_:)), "v"), item("Select All", #selector(NSText.selectAll(_:)), "a")])
        sub("View", [reload])
        sub("Window", [item("Minimize", #selector(NSWindow.performMiniaturize(_:)), "m"),
                       item("Close", #selector(NSWindow.performClose(_:)), "w")])
        NSApp.mainMenu = main
    }

    @objc func reloadPage() { if loaded { _ = web.reload() } else { startServer() } }   // reload() returns WKNavigation?
}

let app = NSApplication.shared
let delegate = App()
app.delegate = delegate
app.setActivationPolicy(.regular)
app.run()
