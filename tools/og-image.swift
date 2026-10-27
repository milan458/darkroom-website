// Renders the 1200×630 Open Graph / Twitter card image: assets/og/noxium-og.png
//
//     swift tools/og-image.swift [path/to/App/Fonts]
//
// Fonts default to ~/dev/darkroom/App/Fonts (Archivo Narrow variable + DM Mono, SIL OFL), the same files
// the App Store screenshots use (AppStore/compose.swift in the app repo).

import AppKit
import CoreText

let width = 1200, height = 630
let w = CGFloat(width), h = CGFloat(height)
let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
let fonts = CommandLine.arguments.count > 1
    ? URL(fileURLWithPath: CommandLine.arguments[1])
    : FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent("dev/darkroom/App/Fonts")
let out = root.appendingPathComponent("assets/og/noxium-og.png")

func color(_ hex: UInt32, _ alpha: CGFloat = 1) -> CGColor {
    CGColor(srgbRed: CGFloat((hex >> 16) & 0xFF) / 255, green: CGFloat((hex >> 8) & 0xFF) / 255, blue: CGFloat(hex & 0xFF) / 255, alpha: alpha)
}

for name in ["ArchivoNarrow-Variable.ttf", "DMMono-Regular.ttf", "DMMono-Medium.ttf"] {
    CTFontManagerRegisterFontsForURL(fonts.appendingPathComponent(name) as CFURL, .process, nil)
}

func archivoBold(_ size: CGFloat) -> CTFont {
    let base = CTFontCreateWithName("ArchivoNarrow-Regular" as CFString, size, nil)
    let descriptor = CTFontDescriptorCreateCopyWithAttributes(CTFontCopyFontDescriptor(base),
        [kCTFontVariationAttribute: [0x77676874: 700]] as CFDictionary)
    return CTFontCreateWithFontDescriptor(descriptor, size, nil)
}

func mono(_ size: CGFloat, medium: Bool = false) -> CTFont {
    CTFontCreateWithName((medium ? "DMMono-Medium" : "DMMono-Regular") as CFString, size, nil)
}

/// Draws left-aligned text with its top edge at `top` (top-down coordinates). Returns the height used.
@discardableResult
func drawText(_ text: String, font: CTFont, color fill: CGColor, tracking: CGFloat = 0, lineHeight: CGFloat = 1,
              x: CGFloat, top: CGFloat, width: CGFloat, context: CGContext) -> CGFloat {
    let paragraph = NSMutableParagraphStyle()
    paragraph.minimumLineHeight = CTFontGetSize(font) * lineHeight
    paragraph.maximumLineHeight = CTFontGetSize(font) * lineHeight
    let attributed = NSAttributedString(string: text, attributes: [
        .font: font, .foregroundColor: NSColor(cgColor: fill)!, .kern: tracking, .paragraphStyle: paragraph,
    ])
    let setter = CTFramesetterCreateWithAttributedString(attributed)
    let fit = CTFramesetterSuggestFrameSizeWithConstraints(setter, CFRange(), nil, CGSize(width: width, height: .greatestFiniteMagnitude), nil)
    let rect = CGRect(x: x, y: h - top - fit.height, width: width, height: fit.height)
    CTFrameDraw(CTFramesetterCreateFrame(setter, CFRange(), CGPath(rect: rect, transform: nil), nil), context)
    return fit.height
}

let context = CGContext(data: nil, width: width, height: height, bitsPerComponent: 8, bytesPerRow: 0,
                        space: CGColorSpace(name: CGColorSpace.sRGB)!, bitmapInfo: CGImageAlphaInfo.noneSkipLast.rawValue)!

// Ground and a soft white glow behind the icon.
context.setFillColor(color(0x000000))
context.fill(CGRect(x: 0, y: 0, width: w, height: h))
let glow = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB), colors: [color(0xFFFFFF, 0.06), color(0xFFFFFF, 0)] as CFArray, locations: [0, 1])!
context.drawRadialGradient(glow, startCenter: CGPoint(x: 300, y: 300), startRadius: 0, endCenter: CGPoint(x: 300, y: 300), endRadius: 430, options: [])

// The Orbit icon in a 420 × 420 square: 4.2 px per unit of its 100-unit canvas.
let icon = CGRect(x: 90, y: (h - 420) / 2, width: 420, height: 420)
let mid = CGPoint(x: icon.midX, y: icon.midY)
func circle(_ center: CGPoint, _ r: CGFloat) -> CGRect { CGRect(x: center.x - r, y: center.y - r, width: r * 2, height: r * 2) }

// Background: radial #1C1C22 → #000000 at 0.72, centred 10 units (42 px) above the middle (y is up here).
context.saveGState()
context.addPath(CGPath(roundedRect: icon, cornerWidth: 94, cornerHeight: 94, transform: nil))
context.clip()
let iconGround = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB),
                            colors: [color(0x1C1C22), color(0x000000), color(0x000000)] as CFArray, locations: [0, 0.72, 1])!
let groundCenter = CGPoint(x: mid.x, y: mid.y + 42)
context.drawRadialGradient(iconGround, startCenter: groundCenter, startRadius: 0, endCenter: groundCenter, endRadius: 328, options: [.drawsAfterEndLocation])
context.restoreGState()

// Orbit and the unlit bolt on it at −45°.
context.setStrokeColor(color(0xFFFFFF, 0.42))
context.setLineWidth(2.52)
context.strokeEllipse(in: circle(mid, 138.6))
context.setLineWidth(3.36)
context.strokeEllipse(in: circle(CGPoint(x: mid.x + 97.9, y: mid.y + 97.9), 10.1))

// Outer and inner glow, halo ring, lit bolt.
context.setFillColor(color(0xFFFFFF, 0.07))
context.fillEllipse(in: circle(mid, 96.6))
context.setFillColor(color(0xFFFFFF, 0.16))
context.fillEllipse(in: circle(mid, 75.6))
context.setStrokeColor(color(0xFFFFFF, 0.16))
context.setLineWidth(4.2)
context.strokeEllipse(in: circle(mid, 69.3))
context.setFillColor(color(0xFFFFFF))
context.fillEllipse(in: circle(mid, 52.5))

// Copy.
let textX: CGFloat = 584, textW: CGFloat = 580
var top: CGFloat = 132
top += drawText("NOXIUM · PHOTO VAULT", font: mono(22, medium: true), color: color(0xF5B759), tracking: 3.2, x: textX, top: top, width: textW, context: context) + 22
top += drawText("PHOTOS ONLY\nYOU CAN SEE.", font: archivoBold(96), color: color(0xF4EFEA), tracking: 1, lineHeight: 0.98, x: textX, top: top, width: textW, context: context) + 26
drawText("Encrypted on your iPhone.\nBacked up to your own iCloud.\nNo ads. No accounts.", font: mono(23), color: color(0xB2A79C), lineHeight: 1.45, x: textX, top: top, width: textW, context: context)
drawText("getnoxium.app", font: mono(20, medium: true), color: color(0xE83B2E), tracking: 1.5, x: textX, top: h - 72, width: textW, context: context)

try FileManager.default.createDirectory(at: out.deletingLastPathComponent(), withIntermediateDirectories: true)
let rep = NSBitmapImageRep(cgImage: context.makeImage()!)
try rep.representation(using: .png, properties: [:])!.write(to: out)
print("wrote", out.path)
