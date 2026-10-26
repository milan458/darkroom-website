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

// Ground and a low safelight glow behind the plate.
context.setFillColor(color(0x070605))
context.fill(CGRect(x: 0, y: 0, width: w, height: h))
let glow = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB), colors: [color(0xE83B2E, 0.34), color(0xE83B2E, 0)] as CFArray, locations: [0, 1])!
context.drawRadialGradient(glow, startCenter: CGPoint(x: 300, y: 300), startRadius: 0, endCenter: CGPoint(x: 300, y: 300), endRadius: 430, options: [])

// Bolt plate: 5×5 grid on a machined panel, with the logo's pattern lit in safelight red.
let plate = CGRect(x: 90, y: (h - 420) / 2, width: 420, height: 420)
let platePath = CGPath(roundedRect: plate, cornerWidth: 64, cornerHeight: 64, transform: nil)
let plateFill = CGGradient(colorsSpace: CGColorSpace(name: CGColorSpace.sRGB), colors: [color(0x2B2520), color(0x13100E)] as CFArray, locations: [0, 1])!
context.saveGState()
context.addPath(platePath)
context.clip()
context.drawLinearGradient(plateFill, start: CGPoint(x: 0, y: plate.maxY), end: CGPoint(x: 0, y: plate.minY), options: [])
context.restoreGState()
context.addPath(platePath)
context.setStrokeColor(color(0x3D332C))
context.setLineWidth(2)
context.strokePath()

let step: CGFloat = 76, origin = CGPoint(x: plate.minX + 58, y: plate.maxY - 58)
func bolt(_ col: Int, _ row: Int) -> CGPoint { CGPoint(x: origin.x + CGFloat(col) * step, y: origin.y - CGFloat(row) * step) }
let lit: [(Int, Int)] = [(0, 4), (1, 3), (1, 2), (2, 1), (3, 1), (4, 0)]

let path = CGMutablePath()
path.move(to: bolt(lit[0].0, lit[0].1))
for (c, r) in lit.dropFirst() { path.addLine(to: bolt(c, r)) }
context.addPath(path)
context.setStrokeColor(color(0xF04E37))
context.setLineWidth(14)
context.setLineCap(.round)
context.setLineJoin(.round)
context.strokePath()

for row in 0..<5 {
    for col in 0..<5 {
        let center = bolt(col, row)
        let isLit = lit.contains { $0 == (col, row) }
        let r: CGFloat = isLit ? 25 : 22
        let rect = CGRect(x: center.x - r, y: center.y - r, width: r * 2, height: r * 2)
        context.setFillColor(isLit ? color(0xF04E37) : color(0x433932))
        context.fillEllipse(in: rect)
        if !isLit {
            context.setStrokeColor(color(0x574B42))
            context.setLineWidth(3)
            context.strokeEllipse(in: rect)
        }
    }
}

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
