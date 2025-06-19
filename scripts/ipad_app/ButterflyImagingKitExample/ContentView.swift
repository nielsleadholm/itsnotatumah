/// Copyright 2012-2025 (C) Butterfly Network, Inc.

import ButterflyImagingKit
import SwiftUI

struct ContentView: View {
    @ObservedObject var model: Model
    @State private var availablePresets: [ImagingPreset] = []
    @State private var initialPreset: ImagingPreset?
    @State private var initialDepth = 7.0
    @State private var initialDepthBounds = Measurement.centimeters(0)...Measurement.centimeters(0)
    @State private var controlDepth = 7.0
    @State private var controlGain = 50.0
    @State private var controlColorGain = 0.0
    @State private var controlPreset: ImagingPreset?
    @State private var controlMode: UltrasoundMode = .bMode

    let imaging = ButterflyImaging.shared

    var body: some View {
        ZStack {
            switch model.stage {
            case .startingUp:
                Text("Initializing...")

            case .ready:
                VStack(spacing: 10) {
                    if model.inProgress {
                        ProgressView()
                    } else if model.probe?.state == .disconnected {
                        Button("Connect a simulated probe") {
                            Task {
                                await model.connectSimulatedProbe()
                            }
                        }
                    } else if !model.availablePresets.isEmpty {
                        if model.probe?.isSimulated == true {
                            Button("Disconnect simulated probe") {
                                Task {
                                    await model.disconnectSimulatedProbe()
                                    initialPreset = nil
                                }
                            }
                        }
                        PresetPicker(controlPreset: $initialPreset, availablePresets: $availablePresets)
                            .onChange(of: initialPreset) { preset in
                                guard let preset else { return }
                                initialDepth = preset.defaultDepth.value
                                initialDepthBounds = preset.depthBounds
                            }
                        if initialPreset != nil {
                            BoundsSlider(title: "Depth", control: $initialDepth, bounds: $initialDepthBounds)
                        }
                        Button("Start imaging!") {
                            // Probe (real or simulated) needs to be connected before tapping this.
                            model.startImaging(preset: initialPreset, depth: initialDepth)
                        }
                    } else {
                        ProgressView()
                    }
                    Spacer()
                }
                .padding()

            case .updateNeeded:
                UpdateFirmwareView()
                    .environmentObject(model)

            case .startingImaging:
                ProgressView()

            case .imaging:
                if let image = model.image {
                    Image(uiImage: image)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .edgesIgnoringSafeArea(.all)
                }
                VStack {
                    Button("Stop imaging") {
                        model.stopImaging()
                        initialPreset = nil
                    }
                    Button("Capture") {
                        model.incrementButtonPressCounter()
                        if let image = model.image {
                            Task {
                                await model.sendImageToServer(image: image, depth: model.depth)
                            }
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    PresetPicker(controlPreset: $controlPreset, availablePresets: $availablePresets)
                        .onChange(of: controlPreset) { preset in
                            guard let preset else { return }
                            imaging.setPreset(preset, parameters: nil)
                            self.controlMode = .bMode
                            print("change preset: \(preset.name); mode: \(controlMode.description)")
                        }
                    Picker("Select a mode", selection: $controlMode) {
                        if let supportedModes = model.preset?.supportedModes {
                            ForEach(supportedModes) {
                                Text($0.description)
                            }
                        }
                    }
                    .pickerStyle(SegmentedPickerStyle())
                    .onChange(of: controlMode) { value in
                        imaging.setMode(value)
                        print("change mode: \(value.description) preset: \(String(describing: controlPreset?.name))")
                    }
                    BoundsSlider(title: "Depth", control: $controlDepth, bounds: $model.depthBounds) { editing in
                        guard !editing else { return }
                        imaging.setDepth(Measurement.centimeters(controlDepth))
                    }
                    HStack {
                        Text("Gain:")
                        Slider(
                            value: Binding(get: {
                                controlGain
                            }, set: { (newVal) in
                                controlGain = newVal
                                imaging.setGain(Int(controlGain))
                            }),
                            in: 0...100
                        ) {
                            Text("Gain:")
                        } minimumValueLabel: {
                            Text("0")
                        } maximumValueLabel: {
                            Text("100")
                        }
                    }
                    if model.mode == .colorDoppler {
                        HStack {
                            Text("Color Gain:")
                            Slider(
                                value: Binding(get: {
                                    controlColorGain
                                }, set: { (newVal) in
                                    controlColorGain = newVal
                                    imaging.setColorGain(Int(controlColorGain))
                                }),
                                in: 0...100
                            ) {
                                Text("Color Gain:")
                            } minimumValueLabel: {
                                Text("0")
                            } maximumValueLabel: {
                                Text("100")
                            }
                        }
                    }
                    
                    Spacer()
                }
                .padding()
            }

            HStack {
                VStack(alignment: .leading) {
                    Spacer()
                    Text("Button Press Count: \(model.buttonPressCounter)")
                        .opacity(0.7)
                        .font(.system(size: 14))
                    Button("Reset Counter") {
                        model.resetButtonPressCounter()
                    }
                    .font(.system(size: 12))
                    .buttonStyle(.bordered)
                    
                    Button("Set External") {
                        Task {
                            await model.sendSetExternalRequest()
                        }
                    }
                    .font(.system(size: 12))
                    .buttonStyle(.bordered)
                    
                    ServerSelectionView(model: model)
                    
                    if let probe = model.probe {
                        Text("Main Button: \(probe.buttonPressedCountMain)")
                            .opacity(0.5)
                            .font(.system(size: 12))
                        
                        // Try to display additional button press counts if they exist
                        // TODO: Add top/bottom button detection once we know the correct property names
                    }
                    
                    if let probeDataList = model.probe?.probeDataList {
                        ForEach(probeDataList) { probeData in
                            Text("\(probeData.id): \(probeData.value)")
                                .opacity(0.5)
                                .font(.system(size: 12))
                        }
                    }

                    Text("license: \(String(describing: model.licenseState))")
                        .opacity(0.5)
                        .font(.system(size: 12))
                }
                Spacer()
            }
            .padding()
        }
        .onAppear {
            imaging.states = { state, imagingStateChanges in

                // Check for state changes.

                if model.preset != state.preset {
                    controlPreset = state.preset
                }

                if model.depth != state.depth {
                    controlDepth = state.depth.value
                }

                if model.gain != state.gain {
                    controlGain = Double(state.gain)
                }

                if model.colorGain != state.colorGain {
                    controlColorGain = Double(state.colorGain)
                }

                // Set the new state.
                model.setState(state, imagingStateChanges: imagingStateChanges)
                let freshAvailablePresets = state.availablePresets
                availablePresets = freshAvailablePresets // Update the @State for the View

                if initialPreset == nil { // Only set if no preset is currently selected
                    // Try to find "musculoskeletal" (case-insensitive)
                    if let targetPreset = freshAvailablePresets.first(where: { $0.name.localizedCaseInsensitiveCompare("musculoskeletal") == .orderedSame }) {
                        initialPreset = targetPreset
                    }
                }
            }

            // Initialize default server selection
            model.setServerFromName("Will")

            Task { try? await model.startup(clientKey: clientKey) }
        }
        .alert(
            "Error",
            isPresented: $model.showingAlert,
            presenting: model.alertError,
            actions: { _ in Button("OK", role: .cancel) { model.clearError() } },
            message: { detail in Text("Error: \(String(describing: detail))") }
        )
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView(model: Model.shared)
            .preferredColorScheme(.dark)
    }
}

struct PresetPicker: View {
    @Binding var controlPreset: ImagingPreset?
    @Binding var availablePresets: [ImagingPreset]

    var body: some View {
        HStack {
            Text("Preset:")
            Picker("Preset", selection: $controlPreset) {
                if controlPreset == nil {
                    Text("---").tag(nil as ImagingPreset?)
                }
                ForEach(availablePresets, id: \.self) {
                    Text($0.name).tag($0 as ImagingPreset?)
                }
            }
        }
    }
}

struct BoundsSlider: View {
    var title: String
    @Binding var control: Double
    @Binding var bounds: ClosedRange<Measurement<UnitLength>>
    var onEditingChanged: ((Bool) -> Void) = { _ in }

    var body: some View {
        HStack {
            Text("\(title):")
            Slider(
                value: $control,
                in: bounds.lowerBound.value...bounds.upperBound.value,
                label: {
                    Text("\(title):")
                },
                minimumValueLabel: {
                    Text(bounds.lowerBound.label)
                },
                maximumValueLabel: {
                    Text(bounds.upperBound.label)
                },
                onEditingChanged: onEditingChanged
            )
        }
    }
}

struct UpdateFirmwareView: View {
    @EnvironmentObject var model: Model

    var body: some View {
        VStack {
            Text("⚠️")
                .font(.title)
            Text("Probe firmware is out-of-date")
            if !model.updating {
                Button("Update firmware") {
                    Task {
                        await model.updateFirmware()
                    }
                }
            } else {
                Text("Updating firmware...")
                Text("Please keep the app open and iQ plugged in.")
                    .fontWeight(.bold)
                if let progress = model.updateProgress {
                    Text("\(Int(progress.timeRemaining)) seconds remaining")
                    Text("\(Int(progress.fractionCompleted * 100))%")
                }
                ProgressView()
            }
        }
    }
}

struct ServerSelectionView: View {
    @ObservedObject var model: Model

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Text("Server:")
                    .font(.system(size: 12))
                    .opacity(0.7)
                Picker("Server", selection: $model.selectedServerName) {
                    ForEach(model.getServerNames(), id: \.self) { serverName in
                        Text(serverName).tag(serverName)
                    }
                }
                .pickerStyle(MenuPickerStyle())
                .onChange(of: model.selectedServerName) { serverName in
                    model.setServerFromName(serverName)
                }
            }
            
            HStack {
                Text("IP:")
                    .font(.system(size: 12))
                    .opacity(0.7)
                TextField("IP Address", text: $model.serverIP)
                    .textFieldStyle(RoundedBorderTextFieldStyle())
                    .font(.system(size: 12))
            }
        }
    }
}
