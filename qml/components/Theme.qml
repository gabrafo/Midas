pragma Singleton
import QtQuick 2.15

/**
 * Centralized design tokens for the MIDAS application.
 * Import as: import "../components" then use Theme.fontSize.body, etc.
 */
QtObject {

    // --- Type scale (pointSize) ---
    readonly property QtObject fontSize: QtObject {
        readonly property int display: 48   // Splash / hero
        readonly property int h1:      28   // Page-level prominent text
        readonly property int h2:      18   // Section heading
        readonly property int h3:      14   // Sub-section heading
        readonly property int subtitle:12   // Card title
        readonly property int body:    11   // Default body text
        readonly property int label:   10   // Form labels, buttons
        readonly property int caption:  9   // Secondary info
        readonly property int small:    8   // Fine print
    }

    // --- Spacing ---
    readonly property QtObject spacing: QtObject {
        readonly property int xs:  4
        readonly property int sm:  8
        readonly property int md: 16
        readonly property int lg: 24
        readonly property int xl: 32
    }

    // --- Shape ---
    readonly property QtObject radius: QtObject {
        readonly property int card:   12
        readonly property int button:  8
        readonly property int pill:   20
        readonly property int small:   4
    }

    // --- Misc ---
    readonly property int borderWidth: 1
    readonly property real dimOpacity: 0.7
    readonly property real hoverOpacity: 0.1
}
