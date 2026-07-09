plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "io.dmrv.dmrv_app"
    compileSdk = flutter.compileSdkVersion
    ndkVersion = flutter.ndkVersion

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_17.toString()
    }

    defaultConfig {
        // P0.9: applicationId finalized as io.dmrv.dmrv_app — PERMANENT once on
        // Play. Changing it later orphans installs + their local DBs.
        applicationId = "io.dmrv.dmrv_app"
        minSdk = flutter.minSdkVersion
        targetSdk = flutter.targetSdkVersion
        versionCode = flutter.versionCode
        versionName = flutter.versionName
    }

    // T2.5: MainActivity reads BuildConfig.DEBUG to gate FLAG_SECURE.
    buildFeatures {
        buildConfig = true
    }

    buildTypes {
        release {
            // T0.6 (BLOCKER before store release): replace the debug keystore
            // with a real release signingConfig. Kept as debug ONLY so
            // `flutter run --release` builds locally; a debug-signed APK is
            // package-replaceable and MUST NOT be published.
            signingConfig = signingConfigs.getByName("debug")

            // T2.4: obfuscate + shrink release builds. Keep rules in
            // proguard-rules.pro. Build with:
            //   flutter build apk --release --obfuscate --split-debug-info=build/symbols
            // and archive build/symbols per release for Sentry symbolication.
            isMinifyEnabled = true
            isShrinkResources = true
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro",
            )
        }
    }
}

flutter {
    source = "../.."
}
