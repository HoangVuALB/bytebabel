// system_audio_capture.swift
// Captures system audio via ScreenCaptureKit and writes raw PCM s16le 16kHz mono to stdout.
// Usage: ./system_audio_capture
// Requires: macOS 13+, Screen Recording permission granted.

import Foundation
import ScreenCaptureKit
import AVFoundation
import CoreAudio

// PCM output config
let TARGET_SAMPLE_RATE: Double = 16000
let TARGET_CHANNELS: Int = 1

// Signal handler for clean shutdown
var shouldStop = false
signal(SIGINT)  { _ in shouldStop = true }
signal(SIGTERM) { _ in shouldStop = true }

@available(macOS 13.0, *)
class AudioCaptureDelegate: NSObject, SCStreamOutput, SCStreamDelegate {
    private var converter: AVAudioConverter?
    private let outputFormat = AVAudioFormat(
        commonFormat: .pcmFormatInt16,
        sampleRate: TARGET_SAMPLE_RATE,
        channels: AVAudioChannelCount(TARGET_CHANNELS),
        interleaved: true
    )!
    private let queue = DispatchQueue(label: "audio.output")

    func stream(_ stream: SCStream, didOutputSampleBuffer sampleBuffer: CMSampleBuffer, of type: SCStreamOutputType) {
        guard type == .audio else { return }
        guard let formatDesc = CMSampleBufferGetFormatDescription(sampleBuffer) else { return }
        let asbd = CMAudioFormatDescriptionGetStreamBasicDescription(formatDesc)!.pointee

        // Build input AVAudioFormat from the sample buffer's ASBD
        var asbdCopy = asbd
        guard let inputFormat = AVAudioFormat(streamDescription: &asbdCopy) else { return }

        // Lazy-init converter when format is known
        if converter == nil {
            converter = AVAudioConverter(from: inputFormat, to: outputFormat)
            if converter == nil {
                fputs("ERROR: Cannot create audio converter\n", stderr)
                return
            }
        }

        // Get audio buffer list from sample buffer
        var blockBuffer: CMBlockBuffer?
        var _ = AudioBufferList()
        var bufferListSize = Int(0)
        CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer,
            bufferListSizeNeededOut: &bufferListSize,
            bufferListOut: nil,
            bufferListSize: 0,
            blockBufferAllocator: nil,
            blockBufferMemoryAllocator: nil,
            flags: 0,
            blockBufferOut: nil
        )

        let audioBufferListPtr = UnsafeMutablePointer<AudioBufferList>.allocate(capacity: 1 + bufferListSize)
        defer { audioBufferListPtr.deallocate() }

        CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(
            sampleBuffer,
            bufferListSizeNeededOut: nil,
            bufferListOut: audioBufferListPtr,
            bufferListSize: bufferListSize,
            blockBufferAllocator: nil,
            blockBufferMemoryAllocator: nil,
            flags: kCMSampleBufferFlag_AudioBufferList_Assure16ByteAlignment,
            blockBufferOut: &blockBuffer
        )

        let frameCount = AVAudioFrameCount(CMSampleBufferGetNumSamples(sampleBuffer))
        guard let inputBuffer = AVAudioPCMBuffer(pcmFormat: inputFormat, frameCapacity: frameCount) else { return }
        inputBuffer.frameLength = frameCount
        
        // Copy audio data into the PCM buffer
        let abl = UnsafeMutableAudioBufferListPointer(audioBufferListPtr)
        let inputABL = inputBuffer.mutableAudioBufferList
        let inputABLPtr = UnsafeMutableAudioBufferListPointer(inputABL)
        for i in 0..<min(abl.count, inputABLPtr.count) {
            if let dst = inputABLPtr[i].mData,
               let src = abl[i].mData {
                let bytesToCopy = min(Int(inputABLPtr[i].mDataByteSize), Int(abl[i].mDataByteSize))
                memcpy(dst, src, bytesToCopy)
            }
        }

        // Target output: ~10ms per chunk = 160 frames at 16kHz
        let outputFrames = AVAudioFrameCount(TARGET_SAMPLE_RATE * 0.1)
        guard let outputBuffer = AVAudioPCMBuffer(pcmFormat: outputFormat, frameCapacity: outputFrames) else { return }

        var error: NSError?
        var inputConsumed = false
        let status = converter!.convert(to: outputBuffer, error: &error) { _, outStatus in
            if inputConsumed {
                outStatus.pointee = .noDataNow
                return nil
            }
            outStatus.pointee = .haveData
            inputConsumed = true
            return inputBuffer
        }

        if status == .error || error != nil {
            fputs("Converter error: \(error?.localizedDescription ?? "unknown")\n", stderr)
            return
        }

        guard outputBuffer.frameLength > 0 else { return }

        // Write raw int16 PCM bytes to stdout
        let byteCount = Int(outputBuffer.frameLength) * TARGET_CHANNELS * 2 // 2 bytes per int16
        if let int16Data = outputBuffer.int16ChannelData?[0] {
            queue.sync {
                let data = Data(bytes: int16Data, count: byteCount)
                FileHandle.standardOutput.write(data)
            }
        }
    }

    func stream(_ stream: SCStream, didStopWithError error: Error) {
        let nsError = error as NSError
        fputs("Stream stopped: \(error.localizedDescription)\n", stderr)
        // Error code -3801 / "application connection being interrupted" is the SCK signal
        // for Screen Recording permission not granted (or revoked) for this binary.
        let desc = error.localizedDescription.lowercased()
        if nsError.code == -3801
            || desc.contains("application connection")
            || desc.contains("connection being interrupted") {
            fputs("SCREEN_RECORDING_PERMISSION_NEEDED\n", stderr)
        }
        shouldStop = true
    }
}


@available(macOS 13.0, *)
func run() async {
    // Get shareable content (enumerates displays, apps, windows)
    let content: SCShareableContent
    do {
        content = try await SCShareableContent.excludingDesktopWindows(false, onScreenWindowsOnly: false)
    } catch {
        fputs("ERROR: Cannot get shareable content: \(error.localizedDescription)\n", stderr)
        fputs("Make sure Screen Recording permission is granted in System Settings > Privacy & Security\n", stderr)
        exit(1)
    }

    guard let display = content.displays.first else {
        fputs("ERROR: No display found\n", stderr)
        exit(1)
    }

    // Capture all audio from the display (= all system audio)
    let filter = SCContentFilter(display: display, excludingApplications: [], exceptingWindows: [])

    let config = SCStreamConfiguration()
    config.capturesAudio = true
    config.excludesCurrentProcessAudio = true
    config.sampleRate = 48000  // native rate; we'll downsample to 16kHz
    config.channelCount = 2
    // Minimal video (required by SCStream but we ignore it)
    config.width = 2
    config.height = 2
    config.minimumFrameInterval = CMTime(value: 1, timescale: 1)  // 1 fps — minimal CPU

    let delegate = AudioCaptureDelegate()
    let stream = SCStream(filter: filter, configuration: config, delegate: delegate)

    do {
        try stream.addStreamOutput(delegate, type: .audio, sampleHandlerQueue: DispatchQueue(label: "audio.capture"))
        try await stream.startCapture()
    } catch {
        fputs("ERROR: Failed to start capture: \(error.localizedDescription)\n", stderr)
        exit(1)
    }

    // Wait briefly so that any immediate stream failure (e.g. SCK session conflict)
    // has time to fire didStopWithError and set shouldStop before we signal READY.
    try? await Task.sleep(nanoseconds: 300_000_000)  // 300ms
    if shouldStop {
        // Stream died immediately — Python will see EOF and retry
        exit(1)
    }

    fputs("READY\n", stderr)  // Python reads this to know capture has started

    // Run until signalled
    while !shouldStop {
        try? await Task.sleep(nanoseconds: 100_000_000)
    }

    try? await stream.stopCapture()
}

if #available(macOS 13.0, *) {
    Task { await run() }
    RunLoop.main.run()
} else {
    fputs("ERROR: macOS 13.0+ required\n", stderr)
    exit(1)
}
