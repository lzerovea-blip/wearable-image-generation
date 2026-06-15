import CoreGraphics
import Foundation
import ImageIO
import UniformTypeIdentifiers

@_silgen_name("CGWindowListCreateImage")
func legacyCGWindowListCreateImage(
    _ screenBounds: CGRect,
    _ listOption: UInt32,
    _ windowID: UInt32,
    _ imageOption: UInt32
) -> CGImage?

func windowList() -> [[String: Any]] {
    let options: CGWindowListOption = [.optionOnScreenOnly, .excludeDesktopElements]
    return (CGWindowListCopyWindowInfo(options, kCGNullWindowID) as? [[String: Any]]) ?? []
}

func listWindows() {
    for window in windowList() {
        let owner = window[kCGWindowOwnerName as String] as? String ?? ""
        let title = window[kCGWindowName as String] as? String ?? ""
        let id = window[kCGWindowNumber as String] as? UInt32 ?? 0
        let bounds = window[kCGWindowBounds as String] as? [String: Any] ?? [:]
        if owner.localizedCaseInsensitiveContains("iPhone")
            || owner.localizedCaseInsensitiveContains("Mirroring")
            || owner.localizedCaseInsensitiveContains("镜像")
            || title.localizedCaseInsensitiveContains("iPhone")
            || title.localizedCaseInsensitiveContains("镜像") {
            print("\(id)\t\(owner)\t\(title)\t\(bounds)")
        }
    }
}

func capture(windowID: UInt32, outputPath: String) throws {
    let image = legacyCGWindowListCreateImage(
        .null,
        CGWindowListOption.optionIncludingWindow.rawValue,
        windowID,
        CGWindowImageOption.boundsIgnoreFraming.rawValue | CGWindowImageOption.bestResolution.rawValue
    )
    guard let image else {
        throw NSError(domain: "capture_window", code: 1, userInfo: [NSLocalizedDescriptionKey: "CGWindowListCreateImage returned nil"])
    }

    let url = URL(fileURLWithPath: outputPath)
    guard let destination = CGImageDestinationCreateWithURL(url as CFURL, UTType.png.identifier as CFString, 1, nil) else {
        throw NSError(domain: "capture_window", code: 2, userInfo: [NSLocalizedDescriptionKey: "Could not create image destination"])
    }
    CGImageDestinationAddImage(destination, image, nil)
    guard CGImageDestinationFinalize(destination) else {
        throw NSError(domain: "capture_window", code: 3, userInfo: [NSLocalizedDescriptionKey: "Could not finalize image"])
    }
    print("\(outputPath)\t\(image.width)x\(image.height)")
}

let args = CommandLine.arguments
if args.count == 1 || args[1] == "list" {
    listWindows()
} else if args.count == 4 && args[1] == "capture" {
    guard let id = UInt32(args[2]) else {
        fputs("Invalid window id\n", stderr)
        exit(2)
    }
    do {
        try capture(windowID: id, outputPath: args[3])
    } catch {
        fputs("\(error.localizedDescription)\n", stderr)
        exit(1)
    }
} else {
    fputs("Usage: swift capture_window.swift list | capture <windowID> <output.png>\n", stderr)
    exit(2)
}
