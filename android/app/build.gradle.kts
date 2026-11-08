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
        versionCode = 4
        versionName = "0.3.0-beta"
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        ndk {
            abiFilters += listOf("armeabi-v7a", "arm64-v8a", "x86", "x86_64")
        }
    }
    buildFeatures {
        buildConfig = true
    }
    sourceSets {
        getByName("main") {
            // Reuse the original Windows logo without altering Windows files.
            res.srcDir(layout.buildDirectory.dir("generated/all-download-brand"))
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
    testImplementation("junit:junit:4.13.2")
    implementation("androidx.core:core:1.15.0")
    androidTestImplementation("androidx.test:runner:1.6.2")
    androidTestImplementation("androidx.test.ext:junit:1.2.1")
    androidTestImplementation("androidx.test:core:1.6.1")
    val ytDlpVersion = "0.18.1"
    implementation("io.github.junkfood02.youtubedl-android:library:$ytDlpVersion")
    implementation("io.github.junkfood02.youtubedl-android:ffmpeg:$ytDlpVersion")
}


// Copies the original root logo into generated Android resources.
// No binary is duplicated or modified in the Windows edition.
val prepareAndroidBranding by tasks.registering(Copy::class) {
    from(rootProject.projectDir.resolve("../logo.jpg"))
    into(layout.buildDirectory.dir("generated/all-download-brand/drawable-nodpi"))
    rename { "all_download_logo.jpg" }
}
tasks.named("preBuild") { dependsOn(prepareAndroidBranding) }
