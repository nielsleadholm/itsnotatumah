/// Copyright 2012-2025 (C) Butterfly Network, Inc.

import SwiftUI

let clientKey = "Replace with your client key"

@main
struct ButterflyImagingKitExampleApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView(model: Model.shared)
                .preferredColorScheme(.dark)
        }
    }
}
