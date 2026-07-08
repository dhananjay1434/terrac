package io.dmrv.dmrv_app

import android.os.Bundle
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity

class MainActivity : FlutterActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        // T2.5: block screenshots and hide the app from the recents thumbnail so
        // on-screen PII (batch UUIDs, GPS, buyer identity) can't be silently
        // captured. Gated on release builds so screenshots still work in dev.
        if (!BuildConfig.DEBUG) {
            window.setFlags(
                WindowManager.LayoutParams.FLAG_SECURE,
                WindowManager.LayoutParams.FLAG_SECURE,
            )
        }
        super.onCreate(savedInstanceState)
    }
}
