import SwiftUI
import UniformTypeIdentifiers

struct ImportArtworkView: View {
    @ObservedObject var vm: ProjectViewModel
    @State private var isTargeted = false

    var body: some View {
        GroupBox("1. Import Artwork") {
            VStack(spacing: 12) {
                dropZone
                if let path = vm.selectedImagePath {
                    selectedImageInfo(path: path)
                }
            }
            .padding(8)
        }
    }

    private var dropZone: some View {
        VStack(spacing: 6) {
        ZStack {
            RoundedRectangle(cornerRadius: 10)
                .strokeBorder(
                    isTargeted ? Color.accentColor : Color.secondary.opacity(0.4),
                    style: StrokeStyle(lineWidth: 2, dash: [6])
                )
                .background(
                    RoundedRectangle(cornerRadius: 10)
                        .fill(isTargeted ? Color.accentColor.opacity(0.07) : Color.clear)
                )
                .frame(height: 120)

            if let path = vm.selectedImagePath, let img = NSImage(contentsOfFile: path) {
                Image(nsImage: img)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(height: 100)
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            } else {
                VStack(spacing: 6) {
                    Image(systemName: "photo.badge.plus")
                        .font(.system(size: 28))
                        .foregroundStyle(.secondary)
                    Text("Drop image here or click Browse")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text("JPG, PNG, TIFF, HEIC")
                        .font(.caption2)
                        .foregroundStyle(.tertiary)
                }
            }
        }
        .onDrop(of: [.image, .fileURL], isTargeted: $isTargeted) { providers in
            handleDrop(providers: providers)
        }
        .onTapGesture { vm.browseForImage() }

        // Browse button below
        Button("Browse…") { vm.browseForImage() }
            .font(.caption)
            .padding(.top, 2)
        } // end VStack
    }

    private func selectedImageInfo(path: String) -> some View {
        let url = URL(fileURLWithPath: path)
        return HStack(spacing: 6) {
            Image(systemName: "checkmark.circle.fill").foregroundStyle(.green)
            VStack(alignment: .leading, spacing: 1) {
                Text(url.lastPathComponent).font(.caption.bold())
                Text(url.deletingLastPathComponent().path).font(.caption2).foregroundStyle(.secondary).lineLimit(1)
            }
            Spacer()
            Button {
                vm.selectedImagePath = nil
                vm.analysis = nil
            } label: {
                Image(systemName: "xmark.circle").foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(8)
        .background(Color.secondary.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 6))
    }

    private func handleDrop(providers: [NSItemProvider]) -> Bool {
        guard let provider = providers.first else { return false }

        if provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) {
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier) { item, _ in
                guard let data = item as? Data,
                      let url = URL(dataRepresentation: data, relativeTo: nil) else { return }
                DispatchQueue.main.async {
                    vm.selectImage(at: url.path)
                }
            }
            return true
        }
        return false
    }
}
