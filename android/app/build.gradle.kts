plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}
android {
    namespace = "com.alldownload.android"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.alldownload.android"
        minSdk = 24
        targetSdk = 35
        versionCode = 1
        versionName = "0.1.0-beta"
        ndk {
            abiFilters += listOf("armeabi-v7a", "arm64-v8a", "x86", "x86_64")
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
    packaging {
        jniLibs {
            useLegacyPackaging = true
        }
    }
}
dependencies {
    val ytDlpVersion = "0.18.1"
    implementation("io.github.junkfood02.youtubedl-android:library:$ytDlpVersion")
    implementation("io.github.junkfood02.youtubedl-android:ffmpeg:$ytDlpVersion")
}
