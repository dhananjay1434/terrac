import java.util.Properties
import java.io.FileInputStream

plugins {
    id("com.android.application")
    id("kotlin-android")
    // The Flutter Gradle Plugin must be applied after the Android and Kotlin Gradle plugins.
    id("dev.flutter.flutter-gradle-plugin")
}

// P0.6: release signing config loaded from android/key.properties (gitignored).
// When absent (e.g. CI, or a fresh checkout), the release buildType falls back to
// debug signing so the compile-smoke still runs — a debug-signed APK must NEVER
// be published. The keystore lives OUTSIDE the repo and must be backed up.
val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("key.properties")
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(FileInputStream(keystorePropertiesFile))
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

    signingConfigs {
        create("release") {
            if (keystorePropertiesFile.exists()) {
                keyAlias = keystoreProperties.getProperty("keyAlias")
                keyPassword = keystoreProperties.getProperty("keyPassword")
                storeFile = keystoreProperties.getProperty("storeFile")?.let { file(it) }
                storePassword = keystoreProperties.getProperty("storePassword")
            }
        }
    }

    buildTypes {
        release {
            // P0.6: Enforce release signing safety. The build MUST fail if
            // key.properties is missing, rather than silently falling back
            // to a debug signature that could be published by mistake.
            signingConfig = if (keystorePropertiesFile.exists())
                signingConfigs.getByName("release")
            else
                throw GradleException("Missing key.properties: Refusing to build a release APK without the production signing key. NEVER publish a debug-signed build.")

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
