import CoreGraphics
import Foundation
import ImageIO
import AppKit
import ScreenCaptureKit
import UniformTypeIdentifiers

@main
struct SCKCapture {
    static func save(_ image: CGImage, to path: String) throws {
        let url = URL(fileURLWithPath: path)
        guard let destination = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil) else {
            throw NSError(domain: "sck_capture", code: 1, userInfo: [NSLocalizedDescriptionKey: "Could not create image destination"])
        }
        CGImageDestinationAddImage(destination, image, nil)
        guard CGImageDestinationFinalize(destination) else {
            throw NSError(domain: "sck_capture", code: 2, userInfo: [NSLocalizedDescriptionKey: "Could not finalize image"])
        }
        print("\(path)\t\(image.width)x\(image.height)")
    }

    static func content() async throws -> SCShareableContent {
        if #available(macOS 14.0, *) {
            return try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: true)
        }
        return try await SCShareableContent.current
    }

    static func isIPhoneWindow(_ window: SCWindow) -> Bool {
        let owner = window.owningApplication?.applicationName ?? ""
        let title = window.title ?? ""
        return owner.localizedCaseInsensitiveContains("iPhone")
            || owner.localizedCaseInsensitiveContains("Mirroring")
            || owner.localizedCaseInsensitiveContains("镜像")
            || title.localizedCaseInsensitiveContains("iPhone")
            || title.localizedCaseInsensitiveContains("镜像")
    }

    static func listWindows(_ windows: [SCWindow]) {
        for window in windows where isIPhoneWindow(window) {
            let owner = window.owningApplication?.applicationName ?? ""
            let title = window.title ?? ""
            let frame = window.frame
            print("\(window.windowID)\t\(owner)\t\(title)\t\(Int(frame.origin.x)),\(Int(frame.origin.y)),\(Int(frame.width))x\(Int(frame.height))")
        }
    }

    static func capture(windowID: UInt32, outputPath: String) async throws {
        let shareable = try await content()
        guard let window = shareable.windows.first(where: { $0.windowID == windowID }) else {
            throw NSError(domain: "sck_capture", code: 3, userInfo: [NSLocalizedDescriptionKey: "Window \(windowID) not found"])
        }
        let frame = window.frame
        let filter = SCContentFilter(desktopIndependentWindow: window)
        let config = SCStreamConfiguration()
        config.width = max(1, Int(frame.width * 2))
        config.height = max(1, Int(frame.height * 2))
        config.showsCursor = false
        let image = try await SCScreenshotManager.captureImage(contentFilter: filter, configuration: config)
        try save(image, to: outputPath)
    }

    static func main() async {
        _ = NSApplication.shared
        let args = CommandLine.arguments
        do {
            if args.count == 1 || args[1] == "list" {
                let shareable = try await content()
                listWindows(shareable.windows)
            } else if args.count == 4 && args[1] == "capture" {
                guard let id = UInt32(args[2]) else {
                    fputs("Invalid window id\n", stderr)
                    exit(2)
                }
                try await capture(windowID: id, outputPath: args[3])
            } else {
                fputs("Usage: swift sck_capture.swift list | capture <windowID> <output.png>\n", stderr)
                exit(2)
            }
        } catch {
            fputs("\(error.localizedDescription)\n", stderr)
            exit(1)
        }
    }
}
