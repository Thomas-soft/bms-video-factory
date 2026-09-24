// Repères du visage par Apple Vision (framework système, 0 Go) — étape 29.
// Usage : swift reperes_visage.swift image.png → JSON sur stdout, coordonnées en pixels,
// origine en haut à gauche.
import Foundation
import Vision
import AppKit

let chemin = CommandLine.arguments[1]
guard let image = NSImage(contentsOfFile: chemin),
      let cg = image.cgImage(forProposedRect: nil, context: nil, hints: nil) else {
    print("{\"erreur\": \"image illisible\"}"); exit(2)
}
let l = Double(cg.width), h = Double(cg.height)
let requete = VNDetectFaceLandmarksRequest()
try VNImageRequestHandler(cgImage: cg, options: [:]).perform([requete])
guard let visages = requete.results, !visages.isEmpty else {
    print("{\"visages\": 0}"); exit(0)
}
let v = visages.max(by: { $0.boundingBox.width < $1.boundingBox.width })!
func points(_ r: VNFaceLandmarkRegion2D?) -> [[Double]] {
    guard let r = r else { return [] }
    return r.pointsInImage(imageSize: CGSize(width: l, height: h)).map { [Double($0.x), h - Double($0.y)] }
}
let b = v.boundingBox
let sortie: [String: Any] = [
    "visages": visages.count,
    "confiance": Double(v.confidence),
    "boite": [b.minX * l, (1 - b.maxY) * h, b.width * l, b.height * h],
    "levres": points(v.landmarks?.outerLips),
    "levres_int": points(v.landmarks?.innerLips),
    "oeil_g": points(v.landmarks?.leftEye),
    "oeil_d": points(v.landmarks?.rightEye),
    "sourcil_g": points(v.landmarks?.leftEyebrow),
    "sourcil_d": points(v.landmarks?.rightEyebrow),
]
let data = try JSONSerialization.data(withJSONObject: sortie)
print(String(data: data, encoding: .utf8)!)
