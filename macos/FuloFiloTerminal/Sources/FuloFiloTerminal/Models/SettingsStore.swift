import Foundation
import SwiftUI

/// Persistent application settings including font size and window size
@Observable
final class SettingsStore {
    // MARK: - Font Size
    var baseFontSize: CGFloat {
        didSet {
            UserDefaults.standard.set(baseFontSize, forKey: "baseFontSize")
            FontScale.shared.base = baseFontSize   // propagate to TerminalType
        }
    }
    
    var labelFontSizeOffset: CGFloat = 0 {
        didSet {
            UserDefaults.standard.set(labelFontSizeOffset, forKey: "labelFontSizeOffset")
        }
    }
    
    // MARK: - Window Size
    var windowWidth: CGFloat {
        didSet {
            UserDefaults.standard.set(windowWidth, forKey: "windowWidth")
        }
    }
    
    var windowHeight: CGFloat {
        didSet {
            UserDefaults.standard.set(windowHeight, forKey: "windowHeight")
        }
    }
    
    // MARK: - Computed Properties
    var labelFontSize: CGFloat {
        max(8, baseFontSize + labelFontSizeOffset)
    }
    
    var monoFontSize: CGFloat {
        max(9, baseFontSize + 1)
    }
    
    var valueFontSize: CGFloat {
        baseFontSize + 8
    }
    
    // MARK: - Init
    init() {
        let defaults = UserDefaults.standard
        
        // Load font sizes
        let savedBaseFontSize = defaults.double(forKey: "baseFontSize")
        let resolvedBase: CGFloat = savedBaseFontSize > 0 ? savedBaseFontSize : 10.0
        self.baseFontSize = resolvedBase
        FontScale.shared.base = resolvedBase   // seed on launch
        
        let savedLabelOffset = defaults.double(forKey: "labelFontSizeOffset")
        self.labelFontSizeOffset = savedLabelOffset
        
        // Load window size (default to readable dimensions)
        let savedWidth = defaults.double(forKey: "windowWidth")
        self.windowWidth = savedWidth > 0 ? savedWidth : 1400
        
        let savedHeight = defaults.double(forKey: "windowHeight")
        self.windowHeight = savedHeight > 0 ? savedHeight : 900
    }
    
    // MARK: - Actions
    func increaseFontSize() {
        baseFontSize = min(24, baseFontSize + 1)
    }
    
    func decreaseFontSize() {
        baseFontSize = max(8, baseFontSize - 1)
    }
    
    func resetFontSize() {
        baseFontSize = 10.0
        labelFontSizeOffset = 0
    }
    
    func resetWindowSize() {
        windowWidth = 1400
        windowHeight = 900
    }
}
