# Photo + Music to Video Feature - Technical Design Document

## Executive Summary

This document outlines the architecture and implementation for a feature that allows users to add music to photos and export as video, similar to Instagram's music feature.

---

## 1. Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              MOBILE CLIENT                                       │
│                                                                                  │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                           UI LAYER                                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │  │
│  │  │Photo Picker │  │Music Browser│  │ Timeline    │  │ Preview     │     │  │
│  │  │             │  │ & Search    │  │ Editor      │  │ Player      │     │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                            │
│                                    ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                        EDITING ENGINE                                     │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐     │  │
│  │  │ Image       │  │ Audio       │  │ Text/Overlay│  │ Animation   │     │  │
│  │  │ Processor   │  │ Processor   │  │ Manager     │  │ Controller  │     │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘     │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                            │
│                                    ▼                                            │
│  ┌──────────────────────────────────────────────────────────────────────────┐  │
│  │                      RENDERING PIPELINE                                   │  │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │  │
│  │  │ Real-time       │  │ Frame           │  │ Export          │          │  │
│  │  │ Preview (GPU)   │  │ Compositor      │  │ Encoder         │          │  │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘          │  │
│  └──────────────────────────────────────────────────────────────────────────┘  │
│                                    │                                            │
└────────────────────────────────────┼────────────────────────────────────────────┘
                                     │
                    ┌────────────────┴────────────────┐
                    │         DECISION POINT          │
                    │  Export Locally vs Server-side  │
                    └────────────────┬────────────────┘
                                     │
         ┌───────────────────────────┴───────────────────────────┐
         ▼                                                       ▼
┌─────────────────────────┐                       ┌─────────────────────────┐
│    LOCAL EXPORT         │                       │    SERVER EXPORT        │
│    (Recommended)        │                       │    (Complex edits)      │
│                         │                       │                         │
│  • Fast processing      │                       │  • Heavy filters        │
│  • No upload needed     │                       │  • AI enhancements      │
│  • Works offline        │                       │  • Batch processing     │
│  • iOS: AVFoundation    │                       │  • FFmpeg workers       │
│  • Android: MediaCodec  │                       │  • GPU acceleration     │
└─────────────────────────┘                       └─────────────────────────┘
```

---

## 2. Client vs Server Processing Decision Matrix

| Feature | Client-Side | Server-Side | Recommendation |
|---------|-------------|-------------|----------------|
| Image to video conversion | ✅ Fast, native APIs | ❌ Unnecessary upload | **Client** |
| Audio trimming | ✅ Instant feedback | ❌ Latency | **Client** |
| Basic filters | ✅ GPU shaders | ❌ Overkill | **Client** |
| Text overlays | ✅ Native rendering | ❌ Unnecessary | **Client** |
| Simple animations | ✅ Core Animation/OpenGL | ❌ Unnecessary | **Client** |
| Final MP4 export | ✅ Hardware encoders | ⚠️ Only if complex | **Client** |
| AI style transfer | ⚠️ ML Kit (limited) | ✅ Better quality | **Server** |
| Complex video effects | ⚠️ May drain battery | ✅ Distributed | **Server** |
| Music library streaming | ❌ Storage issues | ✅ On-demand | **Server** |

**Verdict: 90% Client-Side, 10% Server-Side**

---

## 3. Data Models

### 3.1 Project Model

```typescript
interface PhotoMusicProject {
  id: string;
  createdAt: Date;
  updatedAt: Date;
  
  // Source media
  photo: {
    uri: string;
    width: number;
    height: number;
    orientation: number;
  };
  
  // Music configuration
  music: {
    trackId: string;
    trackUri: string;
    title: string;
    artist: string;
    duration: number;        // Total track duration (ms)
    trimStart: number;       // Start position (ms)
    trimDuration: number;    // Selected duration (ms)
    volume: number;          // 0.0 - 1.0
    fadeIn: number;          // Fade in duration (ms)
    fadeOut: number;         // Fade out duration (ms)
  };
  
  // Video settings
  output: {
    duration: number;        // 5000 - 60000 ms
    resolution: '720p' | '1080p' | '4K';
    fps: 30 | 60;
    aspectRatio: '1:1' | '4:5' | '9:16' | '16:9';
  };
  
  // Overlays
  textOverlays: TextOverlay[];
  stickers: StickerOverlay[];
  
  // Effects
  filter: FilterConfig | null;
  animation: AnimationConfig;
}

interface TextOverlay {
  id: string;
  text: string;
  fontFamily: string;
  fontSize: number;
  fontWeight: 'normal' | 'bold';
  color: string;
  backgroundColor: string | null;
  position: { x: number; y: number };  // Normalized 0-1
  rotation: number;
  scale: number;
  alignment: 'left' | 'center' | 'right';
  animation: 'none' | 'fade' | 'typewriter' | 'bounce';
  startTime: number;
  endTime: number;
}

interface AnimationConfig {
  type: 'none' | 'ken_burns' | 'zoom_in' | 'zoom_out' | 'pan_left' | 'pan_right' | 'pulse';
  intensity: number;  // 0.0 - 1.0
  easing: 'linear' | 'ease_in' | 'ease_out' | 'ease_in_out';
}

interface FilterConfig {
  type: string;
  intensity: number;
  parameters: Record<string, number>;
}
```

---

## 4. iOS Implementation

### 4.1 Project Structure

```
PhotoMusicFeature/
├── Sources/
│   ├── UI/
│   │   ├── PhotoPickerView.swift
│   │   ├── MusicBrowserView.swift
│   │   ├── TimelineEditorView.swift
│   │   ├── TextOverlayEditor.swift
│   │   └── PreviewPlayerView.swift
│   ├── Engine/
│   │   ├── VideoCompositor.swift
│   │   ├── AudioProcessor.swift
│   │   ├── FilterEngine.swift
│   │   └── AnimationController.swift
│   ├── Export/
│   │   ├── VideoExporter.swift
│   │   └── ExportConfiguration.swift
│   └── Models/
│       └── PhotoMusicProject.swift
```

### 4.2 Core Video Compositor (iOS)

```swift
import AVFoundation
import CoreImage
import UIKit

class VideoCompositor {
    
    // MARK: - Properties
    
    private let ciContext: CIContext
    private let outputSettings: [String: Any]
    
    init() {
        // Use Metal for GPU acceleration
        if let metalDevice = MTLCreateSystemDefaultDevice() {
            self.ciContext = CIContext(mtlDevice: metalDevice)
        } else {
            self.ciContext = CIContext()
        }
        
        self.outputSettings = [
            AVVideoCodecKey: AVVideoCodecType.h264,
            AVVideoWidthKey: 1080,
            AVVideoHeightKey: 1920,
            AVVideoCompressionPropertiesKey: [
                AVVideoAverageBitRateKey: 10_000_000,  // 10 Mbps
                AVVideoProfileLevelKey: AVVideoProfileLevelH264HighAutoLevel,
                AVVideoMaxKeyFrameIntervalKey: 30
            ]
        ]
    }
    
    // MARK: - Main Composition Method
    
    func createVideoFromPhoto(
        project: PhotoMusicProject,
        progressHandler: @escaping (Float) -> Void,
        completion: @escaping (Result<URL, Error>) -> Void
    ) {
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self = self else { return }
            
            do {
                // 1. Load and prepare image
                guard let image = self.loadImage(from: project.photo.uri) else {
                    throw CompositorError.imageLoadFailed
                }
                
                // 2. Apply filter if needed
                let processedImage = self.applyFilter(to: image, filter: project.filter)
                
                // 3. Create video composition
                let composition = AVMutableComposition()
                let videoTrack = composition.addMutableTrack(
                    withMediaType: .video,
                    preferredTrackID: kCMPersistentTrackID_Invalid
                )
                
                // 4. Generate video frames
                let outputURL = self.generateOutputURL()
                let videoWriter = try self.createVideoWriter(outputURL: outputURL, project: project)
                
                // 5. Write frames with animation
                try self.writeAnimatedFrames(
                    writer: videoWriter,
                    image: processedImage,
                    project: project,
                    progressHandler: progressHandler
                )
                
                // 6. Add audio track
                let finalURL = try self.addAudioToVideo(
                    videoURL: outputURL,
                    project: project
                )
                
                DispatchQueue.main.async {
                    completion(.success(finalURL))
                }
                
            } catch {
                DispatchQueue.main.async {
                    completion(.failure(error))
                }
            }
        }
    }
    
    // MARK: - Frame Generation with Animation
    
    private func writeAnimatedFrames(
        writer: AVAssetWriter,
        image: CIImage,
        project: PhotoMusicProject,
        progressHandler: @escaping (Float) -> Void
    ) throws {
        
        guard let writerInput = writer.inputs.first(where: { $0.mediaType == .video }),
              let adaptor = createPixelBufferAdaptor(for: writerInput) else {
            throw CompositorError.writerSetupFailed
        }
        
        writer.startWriting()
        writer.startSession(atSourceTime: .zero)
        
        let fps = project.output.fps
        let totalFrames = Int(Double(project.output.duration) / 1000.0 * Double(fps))
        let frameDuration = CMTime(value: 1, timescale: CMTimeScale(fps))
        
        let outputSize = getOutputSize(for: project.output)
        let animationCalculator = AnimationCalculator(
            config: project.animation,
            totalFrames: totalFrames,
            imageSize: image.extent.size,
            outputSize: outputSize
        )
        
        for frameIndex in 0..<totalFrames {
            // Wait for writer to be ready
            while !writerInput.isReadyForMoreMediaData {
                Thread.sleep(forTimeInterval: 0.01)
            }
            
            let progress = Float(frameIndex) / Float(totalFrames)
            
            // Calculate animation transform for this frame
            let transform = animationCalculator.transformForFrame(frameIndex)
            
            // Apply transform to image
            var frameImage = image.transformed(by: transform)
            
            // Add text overlays
            frameImage = addTextOverlays(
                to: frameImage,
                overlays: project.textOverlays,
                frameIndex: frameIndex,
                totalFrames: totalFrames,
                outputSize: outputSize
            )
            
            // Render to pixel buffer
            guard let pixelBuffer = createPixelBuffer(from: frameImage, size: outputSize) else {
                throw CompositorError.pixelBufferCreationFailed
            }
            
            let presentationTime = CMTimeMultiply(frameDuration, multiplier: Int32(frameIndex))
            adaptor.append(pixelBuffer, withPresentationTime: presentationTime)
            
            DispatchQueue.main.async {
                progressHandler(progress * 0.7)  // Video generation is 70% of work
            }
        }
        
        writerInput.markAsFinished()
        
        let semaphore = DispatchSemaphore(value: 0)
        writer.finishWriting {
            semaphore.signal()
        }
        semaphore.wait()
        
        if writer.status == .failed {
            throw writer.error ?? CompositorError.unknown
        }
    }
    
    // MARK: - Audio Processing
    
    private func addAudioToVideo(
        videoURL: URL,
        project: PhotoMusicProject
    ) throws -> URL {
        
        let composition = AVMutableComposition()
        
        // Add video track
        let videoAsset = AVAsset(url: videoURL)
        guard let videoAssetTrack = videoAsset.tracks(withMediaType: .video).first,
              let compositionVideoTrack = composition.addMutableTrack(
                withMediaType: .video,
                preferredTrackID: kCMPersistentTrackID_Invalid
              ) else {
            throw CompositorError.videoTrackCreationFailed
        }
        
        let videoDuration = CMTime(
            seconds: Double(project.output.duration) / 1000.0,
            preferredTimescale: 600
        )
        
        try compositionVideoTrack.insertTimeRange(
            CMTimeRange(start: .zero, duration: videoDuration),
            of: videoAssetTrack,
            at: .zero
        )
        
        // Add audio track
        let audioAsset = AVAsset(url: URL(string: project.music.trackUri)!)
        guard let audioAssetTrack = audioAsset.tracks(withMediaType: .audio).first,
              let compositionAudioTrack = composition.addMutableTrack(
                withMediaType: .audio,
                preferredTrackID: kCMPersistentTrackID_Invalid
              ) else {
            throw CompositorError.audioTrackCreationFailed
        }
        
        let audioStartTime = CMTime(
            seconds: Double(project.music.trimStart) / 1000.0,
            preferredTimescale: 600
        )
        let audioDuration = CMTime(
            seconds: Double(project.music.trimDuration) / 1000.0,
            preferredTimescale: 600
        )
        
        try compositionAudioTrack.insertTimeRange(
            CMTimeRange(start: audioStartTime, duration: audioDuration),
            of: audioAssetTrack,
            at: .zero
        )
        
        // Apply audio effects (volume, fade)
        let audioMix = createAudioMix(
            track: compositionAudioTrack,
            project: project
        )
        
        // Export final video
        let outputURL = generateOutputURL(suffix: "_final")
        
        guard let exportSession = AVAssetExportSession(
            asset: composition,
            presetName: AVAssetExportPresetHighestQuality
        ) else {
            throw CompositorError.exportSessionCreationFailed
        }
        
        exportSession.outputURL = outputURL
        exportSession.outputFileType = .mp4
        exportSession.audioMix = audioMix
        
        let semaphore = DispatchSemaphore(value: 0)
        var exportError: Error?
        
        exportSession.exportAsynchronously {
            if exportSession.status == .failed {
                exportError = exportSession.error
            }
            semaphore.signal()
        }
        
        semaphore.wait()
        
        if let error = exportError {
            throw error
        }
        
        // Clean up temp video file
        try? FileManager.default.removeItem(at: videoURL)
        
        return outputURL
    }
    
    // MARK: - Audio Mix with Fade
    
    private func createAudioMix(
        track: AVMutableCompositionTrack,
        project: PhotoMusicProject
    ) -> AVMutableAudioMix {
        
        let audioMix = AVMutableAudioMix()
        let parameters = AVMutableAudioMixInputParameters(track: track)
        
        let duration = Double(project.music.trimDuration) / 1000.0
        let fadeInDuration = Double(project.music.fadeIn) / 1000.0
        let fadeOutDuration = Double(project.music.fadeOut) / 1000.0
        let volume = project.music.volume
        
        // Fade in
        if fadeInDuration > 0 {
            parameters.setVolumeRamp(
                fromStartVolume: 0,
                toEndVolume: Float(volume),
                timeRange: CMTimeRange(
                    start: .zero,
                    duration: CMTime(seconds: fadeInDuration, preferredTimescale: 600)
                )
            )
        } else {
            parameters.setVolume(Float(volume), at: .zero)
        }
        
        // Fade out
        if fadeOutDuration > 0 {
            let fadeOutStart = CMTime(
                seconds: duration - fadeOutDuration,
                preferredTimescale: 600
            )
            parameters.setVolumeRamp(
                fromStartVolume: Float(volume),
                toEndVolume: 0,
                timeRange: CMTimeRange(
                    start: fadeOutStart,
                    duration: CMTime(seconds: fadeOutDuration, preferredTimescale: 600)
                )
            )
        }
        
        audioMix.inputParameters = [parameters]
        return audioMix
    }
    
    // MARK: - Helpers
    
    private func loadImage(from uri: String) -> CIImage? {
        guard let url = URL(string: uri),
              let data = try? Data(contentsOf: url),
              let uiImage = UIImage(data: data) else {
            return nil
        }
        return CIImage(image: uiImage)
    }
    
    private func applyFilter(to image: CIImage, filter: FilterConfig?) -> CIImage {
        guard let filter = filter else { return image }
        
        // Apply CIFilter based on filter type
        switch filter.type {
        case "vintage":
            return applyVintageFilter(to: image, intensity: filter.intensity)
        case "noir":
            return applyNoirFilter(to: image, intensity: filter.intensity)
        case "warm":
            return applyWarmFilter(to: image, intensity: filter.intensity)
        case "cool":
            return applyCoolFilter(to: image, intensity: filter.intensity)
        default:
            return image
        }
    }
    
    private func applyVintageFilter(to image: CIImage, intensity: Double) -> CIImage {
        guard let sepia = CIFilter(name: "CISepiaTone") else { return image }
        sepia.setValue(image, forKey: kCIInputImageKey)
        sepia.setValue(intensity, forKey: kCIInputIntensityKey)
        return sepia.outputImage ?? image
    }
    
    private func getOutputSize(for output: PhotoMusicProject.OutputConfig) -> CGSize {
        switch output.aspectRatio {
        case "1:1":
            return output.resolution == "1080p" ? CGSize(width: 1080, height: 1080) : CGSize(width: 720, height: 720)
        case "4:5":
            return output.resolution == "1080p" ? CGSize(width: 1080, height: 1350) : CGSize(width: 720, height: 900)
        case "9:16":
            return output.resolution == "1080p" ? CGSize(width: 1080, height: 1920) : CGSize(width: 720, height: 1280)
        case "16:9":
            return output.resolution == "1080p" ? CGSize(width: 1920, height: 1080) : CGSize(width: 1280, height: 720)
        default:
            return CGSize(width: 1080, height: 1920)
        }
    }
    
    private func generateOutputURL(suffix: String = "") -> URL {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let fileName = "photo_music_\(UUID().uuidString)\(suffix).mp4"
        return documentsPath.appendingPathComponent(fileName)
    }
}

// MARK: - Animation Calculator

class AnimationCalculator {
    
    let config: AnimationConfig
    let totalFrames: Int
    let imageSize: CGSize
    let outputSize: CGSize
    
    init(config: AnimationConfig, totalFrames: Int, imageSize: CGSize, outputSize: CGSize) {
        self.config = config
        self.totalFrames = totalFrames
        self.imageSize = imageSize
        self.outputSize = outputSize
    }
    
    func transformForFrame(_ frameIndex: Int) -> CGAffineTransform {
        let progress = Double(frameIndex) / Double(totalFrames)
        let easedProgress = applyEasing(progress)
        
        switch config.type {
        case .kenBurns:
            return kenBurnsTransform(progress: easedProgress)
        case .zoomIn:
            return zoomInTransform(progress: easedProgress)
        case .zoomOut:
            return zoomOutTransform(progress: easedProgress)
        case .panLeft:
            return panLeftTransform(progress: easedProgress)
        case .panRight:
            return panRightTransform(progress: easedProgress)
        case .pulse:
            return pulseTransform(progress: easedProgress)
        default:
            return fitToOutputTransform()
        }
    }
    
    private func kenBurnsTransform(progress: Double) -> CGAffineTransform {
        // Start zoomed in at top-left, end zoomed out centered
        let startScale = 1.3
        let endScale = 1.0
        let scale = startScale + (endScale - startScale) * progress * config.intensity
        
        let startX = -imageSize.width * 0.1
        let endX = 0.0
        let translateX = startX + (endX - startX) * progress
        
        let startY = -imageSize.height * 0.1
        let endY = 0.0
        let translateY = startY + (endY - startY) * progress
        
        return CGAffineTransform(translationX: translateX, y: translateY)
            .scaledBy(x: scale, y: scale)
    }
    
    private func zoomInTransform(progress: Double) -> CGAffineTransform {
        let scale = 1.0 + (config.intensity * 0.3 * progress)
        let centerX = outputSize.width / 2
        let centerY = outputSize.height / 2
        
        return CGAffineTransform(translationX: centerX, y: centerY)
            .scaledBy(x: scale, y: scale)
            .translatedBy(x: -centerX, y: -centerY)
    }
    
    private func zoomOutTransform(progress: Double) -> CGAffineTransform {
        let scale = 1.0 + config.intensity * 0.3 - (config.intensity * 0.3 * progress)
        let centerX = outputSize.width / 2
        let centerY = outputSize.height / 2
        
        return CGAffineTransform(translationX: centerX, y: centerY)
            .scaledBy(x: scale, y: scale)
            .translatedBy(x: -centerX, y: -centerY)
    }
    
    private func applyEasing(_ progress: Double) -> Double {
        switch config.easing {
        case .easeIn:
            return progress * progress
        case .easeOut:
            return 1 - pow(1 - progress, 2)
        case .easeInOut:
            return progress < 0.5
                ? 2 * progress * progress
                : 1 - pow(-2 * progress + 2, 2) / 2
        default:
            return progress
        }
    }
}

// MARK: - Errors

enum CompositorError: Error {
    case imageLoadFailed
    case writerSetupFailed
    case pixelBufferCreationFailed
    case videoTrackCreationFailed
    case audioTrackCreationFailed
    case exportSessionCreationFailed
    case unknown
}
```

### 4.3 Music Trimmer UI (iOS SwiftUI)

```swift
import SwiftUI
import AVFoundation

struct MusicTrimmerView: View {
    
    @Binding var project: PhotoMusicProject
    @State private var waveformImage: UIImage?
    @State private var isPlaying = false
    @State private var currentTime: Double = 0
    
    private let audioPlayer = AudioPreviewPlayer()
    
    var body: some View {
        VStack(spacing: 20) {
            // Track info
            HStack {
                AsyncImage(url: URL(string: project.music.artworkUrl ?? "")) { image in
                    image.resizable()
                } placeholder: {
                    Color.gray
                }
                .frame(width: 50, height: 50)
                .cornerRadius(8)
                
                VStack(alignment: .leading) {
                    Text(project.music.title)
                        .font(.headline)
                    Text(project.music.artist)
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                
                Spacer()
                
                Text(formatDuration(project.music.trimDuration))
                    .font(.caption)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.blue.opacity(0.2))
                    .cornerRadius(4)
            }
            .padding(.horizontal)
            
            // Waveform with trim handles
            WaveformTrimmerView(
                audioURL: URL(string: project.music.trackUri)!,
                trimStart: $project.music.trimStart,
                trimDuration: $project.music.trimDuration,
                totalDuration: project.music.duration,
                currentTime: $currentTime
            )
            .frame(height: 80)
            .padding(.horizontal)
            
            // Time labels
            HStack {
                Text(formatTime(project.music.trimStart))
                    .font(.caption)
                    .foregroundColor(.secondary)
                
                Spacer()
                
                Text(formatTime(project.music.trimStart + project.music.trimDuration))
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal)
            
            // Duration selector
            VStack(alignment: .leading, spacing: 8) {
                Text("Duration")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
                
                HStack(spacing: 12) {
                    ForEach([5, 10, 15, 30], id: \.self) { seconds in
                        DurationButton(
                            seconds: seconds,
                            isSelected: project.music.trimDuration == seconds * 1000,
                            maxDuration: project.music.duration
                        ) {
                            withAnimation {
                                project.music.trimDuration = min(seconds * 1000, project.music.duration - project.music.trimStart)
                            }
                        }
                    }
                }
            }
            .padding(.horizontal)
            
            // Volume slider
            VStack(alignment: .leading, spacing: 8) {
                HStack {
                    Text("Volume")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    Spacer()
                    Text("\(Int(project.music.volume * 100))%")
                        .font(.caption)
                }
                
                Slider(value: $project.music.volume, in: 0...1)
                    .accentColor(.blue)
            }
            .padding(.horizontal)
            
            // Fade options
            HStack(spacing: 20) {
                FadeOptionView(
                    title: "Fade In",
                    duration: $project.music.fadeIn,
                    maxDuration: project.music.trimDuration / 2
                )
                
                FadeOptionView(
                    title: "Fade Out",
                    duration: $project.music.fadeOut,
                    maxDuration: project.music.trimDuration / 2
                )
            }
            .padding(.horizontal)
            
            // Preview controls
            HStack(spacing: 30) {
                Button(action: skipBackward) {
                    Image(systemName: "gobackward.15")
                        .font(.title2)
                }
                
                Button(action: togglePlayback) {
                    Image(systemName: isPlaying ? "pause.circle.fill" : "play.circle.fill")
                        .font(.system(size: 50))
                }
                
                Button(action: skipForward) {
                    Image(systemName: "goforward.15")
                        .font(.title2)
                }
            }
            .padding()
        }
        .onAppear {
            loadWaveform()
        }
        .onDisappear {
            audioPlayer.stop()
        }
    }
    
    private func togglePlayback() {
        if isPlaying {
            audioPlayer.pause()
        } else {
            audioPlayer.play(
                url: URL(string: project.music.trackUri)!,
                startTime: Double(project.music.trimStart) / 1000.0,
                duration: Double(project.music.trimDuration) / 1000.0,
                volume: Float(project.music.volume)
            ) { time in
                currentTime = time
            }
        }
        isPlaying.toggle()
    }
}

// MARK: - Waveform Trimmer

struct WaveformTrimmerView: View {
    
    let audioURL: URL
    @Binding var trimStart: Int
    @Binding var trimDuration: Int
    let totalDuration: Int
    @Binding var currentTime: Double
    
    @State private var waveformSamples: [Float] = []
    @State private var isDraggingStart = false
    @State private var isDraggingEnd = false
    
    var body: some View {
        GeometryReader { geometry in
            ZStack(alignment: .leading) {
                // Full waveform (dimmed)
                WaveformShape(samples: waveformSamples)
                    .fill(Color.gray.opacity(0.3))
                
                // Selected region waveform
                WaveformShape(samples: waveformSamples)
                    .fill(Color.blue)
                    .mask(
                        Rectangle()
                            .offset(x: startPosition(in: geometry.size.width))
                            .frame(width: selectionWidth(in: geometry.size.width))
                    )
                
                // Selection handles
                SelectionHandle(isDragging: $isDraggingStart)
                    .position(x: startPosition(in: geometry.size.width), y: geometry.size.height / 2)
                    .gesture(
                        DragGesture()
                            .onChanged { value in
                                let newStart = Int(value.location.x / geometry.size.width * Double(totalDuration))
                                trimStart = max(0, min(newStart, trimStart + trimDuration - 1000))
                            }
                    )
                
                SelectionHandle(isDragging: $isDraggingEnd)
                    .position(x: endPosition(in: geometry.size.width), y: geometry.size.height / 2)
                    .gesture(
                        DragGesture()
                            .onChanged { value in
                                let newEnd = Int(value.location.x / geometry.size.width * Double(totalDuration))
                                let newDuration = max(1000, min(newEnd - trimStart, totalDuration - trimStart))
                                trimDuration = newDuration
                            }
                    )
                
                // Playhead
                Rectangle()
                    .fill(Color.white)
                    .frame(width: 2)
                    .position(
                        x: CGFloat(currentTime * 1000 / Double(totalDuration)) * geometry.size.width,
                        y: geometry.size.height / 2
                    )
            }
        }
        .onAppear {
            loadWaveform()
        }
    }
    
    private func startPosition(in width: CGFloat) -> CGFloat {
        CGFloat(trimStart) / CGFloat(totalDuration) * width
    }
    
    private func endPosition(in width: CGFloat) -> CGFloat {
        CGFloat(trimStart + trimDuration) / CGFloat(totalDuration) * width
    }
    
    private func selectionWidth(in width: CGFloat) -> CGFloat {
        CGFloat(trimDuration) / CGFloat(totalDuration) * width
    }
    
    private func loadWaveform() {
        Task {
            waveformSamples = await WaveformGenerator.generateSamples(from: audioURL, count: 200)
        }
    }
}
```

---

## 5. Android Implementation

### 5.1 Video Compositor (Android/Kotlin)

```kotlin
package com.looksy.photomusic

import android.content.Context
import android.graphics.*
import android.media.*
import android.opengl.*
import android.os.Handler
import android.os.HandlerThread
import kotlinx.coroutines.*
import java.io.File
import java.nio.ByteBuffer

class VideoCompositor(private val context: Context) {
    
    private val handlerThread = HandlerThread("VideoCompositor").apply { start() }
    private val handler = Handler(handlerThread.looper)
    
    companion object {
        private const val MIME_TYPE = MediaFormat.MIMETYPE_VIDEO_AVC
        private const val BIT_RATE = 10_000_000  // 10 Mbps
        private const val I_FRAME_INTERVAL = 1
    }
    
    suspend fun createVideoFromPhoto(
        project: PhotoMusicProject,
        progressCallback: (Float) -> Unit
    ): Result<File> = withContext(Dispatchers.IO) {
        try {
            // 1. Load and process image
            val bitmap = loadAndProcessImage(project)
                ?: return@withContext Result.failure(Exception("Failed to load image"))
            
            // 2. Create video from frames
            val videoFile = generateVideoFrames(bitmap, project) { progress ->
                progressCallback(progress * 0.7f)
            }
            
            // 3. Add audio track
            val finalFile = addAudioToVideo(videoFile, project) { progress ->
                progressCallback(0.7f + progress * 0.3f)
            }
            
            // Cleanup temp file
            videoFile.delete()
            
            Result.success(finalFile)
            
        } catch (e: Exception) {
            Result.failure(e)
        }
    }
    
    private fun loadAndProcessImage(project: PhotoMusicProject): Bitmap? {
        val options = BitmapFactory.Options().apply {
            inPreferredConfig = Bitmap.Config.ARGB_8888
        }
        
        var bitmap = BitmapFactory.decodeFile(project.photo.uri, options) ?: return null
        
        // Apply filter if configured
        project.filter?.let { filter ->
            bitmap = applyFilter(bitmap, filter)
        }
        
        // Resize to output dimensions
        val outputSize = getOutputSize(project.output)
        bitmap = Bitmap.createScaledBitmap(bitmap, outputSize.width, outputSize.height, true)
        
        return bitmap
    }
    
    private fun generateVideoFrames(
        baseBitmap: Bitmap,
        project: PhotoMusicProject,
        progressCallback: (Float) -> Unit
    ): File {
        val outputSize = getOutputSize(project.output)
        val fps = project.output.fps
        val durationMs = project.output.duration
        val totalFrames = (durationMs / 1000.0 * fps).toInt()
        
        // Setup encoder
        val format = MediaFormat.createVideoFormat(MIME_TYPE, outputSize.width, outputSize.height).apply {
            setInteger(MediaFormat.KEY_COLOR_FORMAT, MediaCodecInfo.CodecCapabilities.COLOR_FormatSurface)
            setInteger(MediaFormat.KEY_BIT_RATE, BIT_RATE)
            setInteger(MediaFormat.KEY_FRAME_RATE, fps)
            setInteger(MediaFormat.KEY_I_FRAME_INTERVAL, I_FRAME_INTERVAL)
        }
        
        val encoder = MediaCodec.createEncoderByType(MIME_TYPE)
        encoder.configure(format, null, null, MediaCodec.CONFIGURE_FLAG_ENCODE)
        
        val inputSurface = encoder.createInputSurface()
        encoder.start()
        
        // Setup output file
        val outputFile = File(context.cacheDir, "temp_video_${System.currentTimeMillis()}.mp4")
        val muxer = MediaMuxer(outputFile.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        var videoTrackIndex = -1
        var muxerStarted = false
        
        // Setup EGL for rendering
        val eglHelper = EGLHelper()
        eglHelper.init(inputSurface)
        
        val animationCalculator = AnimationCalculator(
            config = project.animation,
            totalFrames = totalFrames,
            imageSize = Size(baseBitmap.width, baseBitmap.height),
            outputSize = outputSize
        )
        
        val textRenderer = TextOverlayRenderer(outputSize)
        
        try {
            val bufferInfo = MediaCodec.BufferInfo()
            
            for (frameIndex in 0 until totalFrames) {
                // Calculate animation transform
                val transform = animationCalculator.getTransformForFrame(frameIndex)
                
                // Render frame
                eglHelper.makeCurrent()
                
                // Clear and draw
                GLES20.glClearColor(0f, 0f, 0f, 1f)
                GLES20.glClear(GLES20.GL_COLOR_BUFFER_BIT)
                
                // Draw bitmap with transform
                drawBitmapWithTransform(baseBitmap, transform, outputSize)
                
                // Draw text overlays
                project.textOverlays.forEach { overlay ->
                    if (shouldShowOverlay(overlay, frameIndex, totalFrames)) {
                        textRenderer.drawText(overlay, frameIndex, totalFrames)
                    }
                }
                
                // Set presentation time
                val presentationTimeNs = frameIndex * 1_000_000_000L / fps
                eglHelper.setPresentationTime(presentationTimeNs)
                eglHelper.swapBuffers()
                
                // Drain encoder
                drainEncoder(encoder, muxer, bufferInfo, videoTrackIndex, muxerStarted).let { (track, started) ->
                    videoTrackIndex = track
                    muxerStarted = started
                }
                
                progressCallback(frameIndex.toFloat() / totalFrames)
            }
            
            // Signal end of stream
            encoder.signalEndOfInputStream()
            drainEncoder(encoder, muxer, bufferInfo, videoTrackIndex, muxerStarted, endOfStream = true)
            
        } finally {
            encoder.stop()
            encoder.release()
            eglHelper.release()
            muxer.stop()
            muxer.release()
        }
        
        return outputFile
    }
    
    private fun addAudioToVideo(
        videoFile: File,
        project: PhotoMusicProject,
        progressCallback: (Float) -> Unit
    ): File {
        val outputFile = File(context.cacheDir, "final_video_${System.currentTimeMillis()}.mp4")
        
        // Extract video track
        val videoExtractor = MediaExtractor().apply {
            setDataSource(videoFile.absolutePath)
        }
        val videoTrackIndex = findTrack(videoExtractor, "video/")
        videoExtractor.selectTrack(videoTrackIndex)
        val videoFormat = videoExtractor.getTrackFormat(videoTrackIndex)
        
        // Extract audio track
        val audioExtractor = MediaExtractor().apply {
            setDataSource(project.music.trackUri)
        }
        val audioTrackIndex = findTrack(audioExtractor, "audio/")
        audioExtractor.selectTrack(audioTrackIndex)
        val audioFormat = audioExtractor.getTrackFormat(audioTrackIndex)
        
        // Seek to trim start
        val trimStartUs = project.music.trimStart * 1000L
        audioExtractor.seekTo(trimStartUs, MediaExtractor.SEEK_TO_CLOSEST_SYNC)
        
        // Setup muxer
        val muxer = MediaMuxer(outputFile.absolutePath, MediaMuxer.OutputFormat.MUXER_OUTPUT_MPEG_4)
        val muxerVideoTrack = muxer.addTrack(videoFormat)
        val muxerAudioTrack = muxer.addTrack(audioFormat)
        muxer.start()
        
        // Copy video track
        copyTrack(videoExtractor, muxer, muxerVideoTrack, Long.MAX_VALUE) { progressCallback(it * 0.5f) }
        
        // Copy audio track (trimmed duration)
        val trimDurationUs = project.music.trimDuration * 1000L
        copyTrack(audioExtractor, muxer, muxerAudioTrack, trimDurationUs) { progressCallback(0.5f + it * 0.5f) }
        
        videoExtractor.release()
        audioExtractor.release()
        muxer.stop()
        muxer.release()
        
        return outputFile
    }
    
    private fun applyFilter(bitmap: Bitmap, filter: FilterConfig): Bitmap {
        val result = bitmap.copy(Bitmap.Config.ARGB_8888, true)
        val canvas = Canvas(result)
        val paint = Paint()
        
        when (filter.type) {
            "vintage" -> {
                val colorMatrix = ColorMatrix().apply {
                    setSaturation(1f - filter.intensity.toFloat() * 0.5f)
                }
                paint.colorFilter = ColorMatrixColorFilter(colorMatrix)
            }
            "noir" -> {
                val colorMatrix = ColorMatrix().apply {
                    setSaturation(0f)
                    val contrast = 1f + filter.intensity.toFloat() * 0.5f
                    setScale(contrast, contrast, contrast, 1f)
                }
                paint.colorFilter = ColorMatrixColorFilter(colorMatrix)
            }
            "warm" -> {
                val colorMatrix = ColorMatrix(floatArrayOf(
                    1f + filter.intensity.toFloat() * 0.2f, 0f, 0f, 0f, 0f,
                    0f, 1f, 0f, 0f, 0f,
                    0f, 0f, 1f - filter.intensity.toFloat() * 0.2f, 0f, 0f,
                    0f, 0f, 0f, 1f, 0f
                ))
                paint.colorFilter = ColorMatrixColorFilter(colorMatrix)
            }
        }
        
        canvas.drawBitmap(bitmap, 0f, 0f, paint)
        return result
    }
    
    private fun getOutputSize(output: PhotoMusicProject.OutputConfig): Size {
        return when (output.aspectRatio) {
            "1:1" -> if (output.resolution == "1080p") Size(1080, 1080) else Size(720, 720)
            "4:5" -> if (output.resolution == "1080p") Size(1080, 1350) else Size(720, 900)
            "9:16" -> if (output.resolution == "1080p") Size(1080, 1920) else Size(720, 1280)
            "16:9" -> if (output.resolution == "1080p") Size(1920, 1080) else Size(1280, 720)
            else -> Size(1080, 1920)
        }
    }
}

// MARK: - Animation Calculator

class AnimationCalculator(
    private val config: AnimationConfig,
    private val totalFrames: Int,
    private val imageSize: Size,
    private val outputSize: Size
) {
    
    fun getTransformForFrame(frameIndex: Int): Matrix {
        val progress = frameIndex.toFloat() / totalFrames
        val easedProgress = applyEasing(progress)
        
        return when (config.type) {
            AnimationType.KEN_BURNS -> kenBurnsTransform(easedProgress)
            AnimationType.ZOOM_IN -> zoomInTransform(easedProgress)
            AnimationType.ZOOM_OUT -> zoomOutTransform(easedProgress)
            AnimationType.PAN_LEFT -> panLeftTransform(easedProgress)
            AnimationType.PAN_RIGHT -> panRightTransform(easedProgress)
            AnimationType.PULSE -> pulseTransform(easedProgress)
            else -> Matrix()
        }
    }
    
    private fun kenBurnsTransform(progress: Float): Matrix {
        val matrix = Matrix()
        val startScale = 1.3f
        val endScale = 1.0f
        val scale = startScale + (endScale - startScale) * progress * config.intensity.toFloat()
        
        matrix.postScale(scale, scale, outputSize.width / 2f, outputSize.height / 2f)
        
        val translateX = -imageSize.width * 0.1f * (1 - progress)
        val translateY = -imageSize.height * 0.1f * (1 - progress)
        matrix.postTranslate(translateX, translateY)
        
        return matrix
    }
    
    private fun zoomInTransform(progress: Float): Matrix {
        val matrix = Matrix()
        val scale = 1f + config.intensity.toFloat() * 0.3f * progress
        matrix.postScale(scale, scale, outputSize.width / 2f, outputSize.height / 2f)
        return matrix
    }
    
    private fun applyEasing(progress: Float): Float {
        return when (config.easing) {
            EasingType.EASE_IN -> progress * progress
            EasingType.EASE_OUT -> 1 - (1 - progress).pow(2)
            EasingType.EASE_IN_OUT -> {
                if (progress < 0.5f) 2 * progress * progress
                else 1 - (-2 * progress + 2).pow(2) / 2
            }
            else -> progress
        }
    }
}
```

---

## 6. Backend Processing (Optional - For Complex Effects)

### 6.1 FFmpeg Worker Service

```python
# backend/services/video_processor.py

import asyncio
import subprocess
import os
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
import aiofiles
import aiohttp

@dataclass
class ProcessingJob:
    job_id: str
    photo_url: str
    music_url: str
    trim_start_ms: int
    trim_duration_ms: int
    output_duration_ms: int
    animation_type: str
    filter_type: Optional[str]
    text_overlays: list
    output_format: str = "mp4"
    resolution: str = "1080p"
    fps: int = 30

class VideoProcessor:
    """Server-side video processing using FFmpeg"""
    
    def __init__(self, work_dir: str = "/tmp/video_processing"):
        self.work_dir = Path(work_dir)
        self.work_dir.mkdir(parents=True, exist_ok=True)
    
    async def process(self, job: ProcessingJob, progress_callback=None) -> str:
        """Process a photo + music job and return output URL"""
        
        job_dir = self.work_dir / job.job_id
        job_dir.mkdir(exist_ok=True)
        
        try:
            # 1. Download assets
            if progress_callback:
                await progress_callback(0.1, "Downloading assets...")
            
            photo_path = await self._download_file(job.photo_url, job_dir / "photo.jpg")
            music_path = await self._download_file(job.music_url, job_dir / "music.mp3")
            
            # 2. Generate video from photo with animation
            if progress_callback:
                await progress_callback(0.3, "Generating video frames...")
            
            video_path = await self._generate_animated_video(
                photo_path=photo_path,
                output_path=job_dir / "video_no_audio.mp4",
                duration_ms=job.output_duration_ms,
                animation_type=job.animation_type,
                filter_type=job.filter_type,
                text_overlays=job.text_overlays,
                resolution=job.resolution,
                fps=job.fps
            )
            
            # 3. Trim and add audio
            if progress_callback:
                await progress_callback(0.7, "Adding audio...")
            
            output_path = job_dir / f"output_{job.job_id}.mp4"
            await self._add_audio(
                video_path=video_path,
                audio_path=music_path,
                output_path=output_path,
                trim_start_ms=job.trim_start_ms,
                trim_duration_ms=job.trim_duration_ms
            )
            
            # 4. Upload to storage
            if progress_callback:
                await progress_callback(0.9, "Uploading result...")
            
            output_url = await self._upload_to_storage(output_path)
            
            if progress_callback:
                await progress_callback(1.0, "Complete!")
            
            return output_url
            
        finally:
            # Cleanup
            await self._cleanup_job_dir(job_dir)
    
    async def _generate_animated_video(
        self,
        photo_path: Path,
        output_path: Path,
        duration_ms: int,
        animation_type: str,
        filter_type: Optional[str],
        text_overlays: list,
        resolution: str,
        fps: int
    ) -> Path:
        """Generate video with animation using FFmpeg"""
        
        duration_s = duration_ms / 1000.0
        
        # Build filter chain
        filters = []
        
        # Resolution
        width, height = self._get_resolution(resolution)
        filters.append(f"scale={width}:{height}:force_original_aspect_ratio=decrease")
        filters.append(f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:black")
        
        # Animation filter
        animation_filter = self._get_animation_filter(animation_type, duration_s)
        if animation_filter:
            filters.append(animation_filter)
        
        # Color filter
        color_filter = self._get_color_filter(filter_type)
        if color_filter:
            filters.append(color_filter)
        
        # Text overlays
        for overlay in text_overlays:
            text_filter = self._get_text_filter(overlay, duration_s)
            filters.append(text_filter)
        
        filter_chain = ",".join(filters)
        
        # FFmpeg command
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", str(photo_path),
            "-t", str(duration_s),
            "-vf", filter_chain,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-r", str(fps),
            "-movflags", "+faststart",
            str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        _, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"FFmpeg error: {stderr.decode()}")
        
        return output_path
    
    async def _add_audio(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path,
        trim_start_ms: int,
        trim_duration_ms: int
    ) -> Path:
        """Add trimmed audio to video"""
        
        trim_start_s = trim_start_ms / 1000.0
        trim_duration_s = trim_duration_ms / 1000.0
        
        # Add fade in/out
        fade_duration = min(0.5, trim_duration_s / 4)
        
        cmd = [
            "ffmpeg", "-y",
            "-i", str(video_path),
            "-ss", str(trim_start_s),
            "-t", str(trim_duration_s),
            "-i", str(audio_path),
            "-filter_complex",
            f"[1:a]afade=t=in:st=0:d={fade_duration},afade=t=out:st={trim_duration_s - fade_duration}:d={fade_duration}[a]",
            "-map", "0:v",
            "-map", "[a]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            str(output_path)
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        _, stderr = await process.communicate()
        
        if process.returncode != 0:
            raise Exception(f"FFmpeg audio error: {stderr.decode()}")
        
        return output_path
    
    def _get_animation_filter(self, animation_type: str, duration: float) -> Optional[str]:
        """Generate FFmpeg filter for animation effect"""
        
        animations = {
            "zoom_in": f"zoompan=z='min(zoom+0.002,1.5)':d={int(duration * 25)}:s=1080x1920",
            "zoom_out": f"zoompan=z='if(eq(on,1),1.5,max(zoom-0.002,1))':d={int(duration * 25)}:s=1080x1920",
            "pan_left": f"zoompan=z=1.2:x='iw/2-(iw/zoom/2)+on*2':y='ih/2-(ih/zoom/2)':d={int(duration * 25)}:s=1080x1920",
            "pan_right": f"zoompan=z=1.2:x='iw/2-(iw/zoom/2)-on*2':y='ih/2-(ih/zoom/2)':d={int(duration * 25)}:s=1080x1920",
            "ken_burns": f"zoompan=z='1.5-on/{int(duration * 25)}*0.5':x='iw/2-(iw/zoom/2)+on':y='ih/2-(ih/zoom/2)-on*0.5':d={int(duration * 25)}:s=1080x1920",
        }
        
        return animations.get(animation_type)
    
    def _get_color_filter(self, filter_type: Optional[str]) -> Optional[str]:
        """Generate FFmpeg filter for color effects"""
        
        if not filter_type:
            return None
        
        filters = {
            "vintage": "curves=vintage",
            "noir": "hue=s=0,curves=m='0/0 0.5/0.4 1/1'",
            "warm": "colorbalance=rs=0.2:gs=0.1:bs=-0.1",
            "cool": "colorbalance=rs=-0.1:gs=0:bs=0.2",
            "vivid": "eq=saturation=1.5:contrast=1.1",
            "fade": "colorlevels=rimax=0.9:gimax=0.9:bimax=0.85",
        }
        
        return filters.get(filter_type)
    
    def _get_text_filter(self, overlay: dict, duration: float) -> str:
        """Generate FFmpeg drawtext filter"""
        
        text = overlay.get("text", "").replace("'", "\\'")
        font_size = overlay.get("fontSize", 48)
        color = overlay.get("color", "white")
        x = overlay.get("x", 0.5)
        y = overlay.get("y", 0.5)
        
        # Convert normalized coords to FFmpeg expression
        x_expr = f"(w-text_w)*{x}"
        y_expr = f"(h-text_h)*{y}"
        
        # Animation
        animation = overlay.get("animation", "none")
        if animation == "fade":
            alpha_expr = f"if(lt(t,0.5),t*2,if(gt(t,{duration-0.5}),({duration}-t)*2,1))"
        else:
            alpha_expr = "1"
        
        return (
            f"drawtext=text='{text}':"
            f"fontsize={font_size}:"
            f"fontcolor={color}:"
            f"x={x_expr}:"
            f"y={y_expr}:"
            f"alpha='{alpha_expr}'"
        )
    
    def _get_resolution(self, resolution: str) -> tuple:
        resolutions = {
            "720p": (720, 1280),
            "1080p": (1080, 1920),
            "4K": (2160, 3840),
        }
        return resolutions.get(resolution, (1080, 1920))
    
    async def _download_file(self, url: str, output_path: Path) -> Path:
        """Download file from URL"""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                async with aiofiles.open(output_path, 'wb') as f:
                    await f.write(await response.read())
        return output_path
    
    async def _upload_to_storage(self, file_path: Path) -> str:
        """Upload to cloud storage and return URL"""
        # Implementation depends on your storage provider (S3, GCS, etc.)
        # For now, return local path
        return f"/api/videos/{file_path.name}"
    
    async def _cleanup_job_dir(self, job_dir: Path):
        """Clean up temporary files"""
        import shutil
        shutil.rmtree(job_dir, ignore_errors=True)


# API Endpoint
from fastapi import BackgroundTasks

@api_router.post("/videos/create-from-photo")
async def create_video_from_photo(
    request: Request,
    job_data: dict,
    background_tasks: BackgroundTasks
):
    user = await get_current_user(request)
    if not user:
        raise HTTPException(status_code=401)
    
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    
    job = ProcessingJob(
        job_id=job_id,
        photo_url=job_data["photo_url"],
        music_url=job_data["music_url"],
        trim_start_ms=job_data.get("trim_start_ms", 0),
        trim_duration_ms=job_data.get("trim_duration_ms", 15000),
        output_duration_ms=job_data.get("output_duration_ms", 15000),
        animation_type=job_data.get("animation_type", "none"),
        filter_type=job_data.get("filter_type"),
        text_overlays=job_data.get("text_overlays", []),
    )
    
    # Process in background
    background_tasks.add_task(process_video_job, job, user.user_id)
    
    return {
        "job_id": job_id,
        "status": "processing",
        "estimated_time_seconds": 30
    }
```

---

## 7. Performance Optimizations

### 7.1 Memory Management

```swift
// iOS - Efficient frame rendering
class MemoryEfficientRenderer {
    
    private let pixelBufferPool: CVPixelBufferPool
    private var reusableBuffer: CVPixelBuffer?
    
    init(size: CGSize) {
        // Create pixel buffer pool for reuse
        let attributes: [String: Any] = [
            kCVPixelBufferWidthKey as String: Int(size.width),
            kCVPixelBufferHeightKey as String: Int(size.height),
            kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA,
            kCVPixelBufferIOSurfacePropertiesKey as String: [:]
        ]
        
        var pool: CVPixelBufferPool?
        CVPixelBufferPoolCreate(nil, nil, attributes as CFDictionary, &pool)
        self.pixelBufferPool = pool!
    }
    
    func getPixelBuffer() -> CVPixelBuffer? {
        var buffer: CVPixelBuffer?
        CVPixelBufferPoolCreatePixelBuffer(nil, pixelBufferPool, &buffer)
        return buffer
    }
    
    func renderFrame(_ image: CIImage, to pixelBuffer: CVPixelBuffer, context: CIContext) {
        // Render directly to pixel buffer (zero-copy)
        context.render(image, to: pixelBuffer)
    }
}
```

### 7.2 Battery Optimization

```kotlin
// Android - Battery-efficient processing
class BatteryEfficientProcessor(context: Context) {
    
    private val powerManager = context.getSystemService(Context.POWER_SERVICE) as PowerManager
    private val wakeLock = powerManager.newWakeLock(
        PowerManager.PARTIAL_WAKE_LOCK,
        "Looksy::VideoProcessing"
    )
    
    suspend fun processWithBatteryOptimization(
        job: ProcessingJob,
        priority: ProcessingPriority
    ): Result<File> {
        
        // Acquire wake lock only during processing
        wakeLock.acquire(10 * 60 * 1000L)  // 10 minutes max
        
        try {
            // Check battery level
            val batteryLevel = getBatteryLevel()
            
            // Adjust quality based on battery
            val adjustedJob = when {
                batteryLevel < 15 -> job.copy(
                    resolution = "720p",
                    fps = 24
                )
                batteryLevel < 30 && priority != ProcessingPriority.HIGH -> job.copy(
                    resolution = "720p",
                    fps = 30
                )
                else -> job
            }
            
            // Use efficient encoder settings
            val result = processVideo(adjustedJob)
            
            return result
            
        } finally {
            if (wakeLock.isHeld) {
                wakeLock.release()
            }
        }
    }
    
    private fun getBatteryLevel(): Int {
        val batteryStatus = context.registerReceiver(
            null,
            IntentFilter(Intent.ACTION_BATTERY_CHANGED)
        )
        val level = batteryStatus?.getIntExtra(BatteryManager.EXTRA_LEVEL, -1) ?: -1
        val scale = batteryStatus?.getIntExtra(BatteryManager.EXTRA_SCALE, -1) ?: -1
        return (level * 100 / scale.toFloat()).toInt()
    }
}
```

### 7.3 Fast Preview Rendering

```swift
// iOS - Real-time preview with Metal
import Metal
import MetalKit

class MetalPreviewRenderer {
    
    private let device: MTLDevice
    private let commandQueue: MTLCommandQueue
    private let pipelineState: MTLRenderPipelineState
    private var currentTexture: MTLTexture?
    
    init() {
        self.device = MTLCreateSystemDefaultDevice()!
        self.commandQueue = device.makeCommandQueue()!
        self.pipelineState = createPipelineState()
    }
    
    func updatePreview(
        image: CIImage,
        animation: AnimationConfig,
        progress: Float,
        in view: MTKView
    ) {
        // Apply animation transform
        let transform = calculateTransform(animation: animation, progress: progress)
        let transformedImage = image.transformed(by: transform)
        
        // Render to Metal texture
        guard let commandBuffer = commandQueue.makeCommandBuffer(),
              let drawable = view.currentDrawable else { return }
        
        let context = CIContext(mtlDevice: device)
        context.render(
            transformedImage,
            to: drawable.texture,
            commandBuffer: commandBuffer,
            bounds: transformedImage.extent,
            colorSpace: CGColorSpaceCreateDeviceRGB()
        )
        
        commandBuffer.present(drawable)
        commandBuffer.commit()
    }
}
```

---

## 8. Implementation Timeline

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Phase 1: Core** | 2 weeks | Photo selection, basic video export, audio trimming |
| **Phase 2: Animations** | 1 week | Ken Burns, zoom, pan animations |
| **Phase 3: Filters** | 1 week | Color filters, GPU shaders |
| **Phase 4: Text** | 1 week | Text overlays, fonts, animations |
| **Phase 5: Polish** | 1 week | Performance optimization, UI refinement |
| **Phase 6: Backend** | 1 week | Server processing (optional), music library API |

---

## 9. Music Library Integration

```typescript
// API for music browsing
interface MusicTrack {
  id: string;
  title: string;
  artist: string;
  album: string;
  duration: number;
  previewUrl: string;      // 30-second preview
  fullTrackUrl: string;    // Requires license
  artworkUrl: string;
  bpm: number;
  genre: string;
  mood: string[];
  isLicensed: boolean;
}

// Endpoints
GET /api/music/trending
GET /api/music/search?q={query}
GET /api/music/genres/{genre}
GET /api/music/moods/{mood}
GET /api/music/track/{trackId}
GET /api/music/track/{trackId}/waveform
```

---

## 10. Summary

### Key Decisions

1. **Client-First Processing**: 90% of work done on-device for speed and offline support
2. **Native Frameworks**: AVFoundation (iOS) and MediaCodec (Android) for hardware acceleration
3. **GPU Rendering**: Metal/OpenGL for real-time preview and efficient encoding
4. **Server Backup**: FFmpeg workers for complex effects or batch processing
5. **Memory Pooling**: Reuse pixel buffers to minimize allocations
6. **Battery Awareness**: Adaptive quality based on power state

### Expected Performance

| Metric | Target | Method |
|--------|--------|--------|
| Preview latency | <16ms | GPU rendering |
| Export time (15s video) | <10s | Hardware encoder |
| Memory usage | <200MB | Buffer pooling |
| Battery drain | <5% per export | Efficient encoding |
