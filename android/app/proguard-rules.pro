# T2.4 — R8/ProGuard keep rules for release obfuscation + shrinking.
# Start conservative; tighten once a device build confirms nothing is stripped.

# Flutter embedding + plugins reflect into these.
-keep class io.flutter.** { *; }
-keep class io.flutter.plugins.** { *; }
-dontwarn io.flutter.**

# drift / sqlite3 native loader (Dart FFI + NDK).
-keep class org.sqlite.** { *; }
-keep class com.tekartik.sqflite.** { *; }
-dontwarn org.sqlite.**

# flutter_secure_storage (Android Keystore access).
-keep class io.flutter.plugins.flutter_secure_storage.** { *; }

# Sentry crash reporting (needs class/line info to symbolicate).
-keep class io.sentry.** { *; }
-dontwarn io.sentry.**
-keepattributes SourceFile,LineNumberTable

# freeRASP / Talsec device integrity.
-keep class com.aheaditec.talsec.** { *; }
-keep class com.aheaditec.freerasp.** { *; }
-dontwarn com.aheaditec.**

# flutter_reactive_ble, workmanager, sensors_plus, geolocator (plugin channels).
-keep class com.signify.hue.flutterreactiveble.** { *; }
-keep class dev.fluttercommunity.workmanager.** { *; }
-keep class dev.fluttercommunity.plus.** { *; }
-dontwarn com.google.android.play.**

# Kotlin coroutines internals occasionally referenced reflectively.
-dontwarn kotlinx.coroutines.**
