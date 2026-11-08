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


// Reproduce the real Windows brand as a compact 192px lossless PNG at build time.
// The original Windows logo.jpg is read-only and is never changed in the repository.
// Avoid decoding a full-size JPEG every time the Android launcher or splash appears.
val originalLogo = rootProject.projectDir.resolve("../logo.jpg")
val compactLogo = layout.buildDirectory.file(
    "generated/all-download-brand/drawable-nodpi/all_download_logo.png"
)
val prepareAndroidBranding by tasks.registering {
    inputs.file(originalLogo)
    outputs.file(compactLogo)
    doLast {
        val image = javax.imageio.ImageIO.read(originalLogo)
            ?: error("Original All-Download logo.jpg is invalid.")
        val size = 192
        val scale = minOf(size.toDouble() / image.width, size.toDouble() / image.height)
        val width = (image.width * scale).toInt().coerceAtLeast(1)
        val height = (image.height * scale).toInt().coerceAtLeast(1)
        val icon = java.awt.image.BufferedImage(size, size,
            java.awt.image.BufferedImage.TYPE_INT_ARGB)
        val graphics = icon.createGraphics()
        try {
            graphics.color = java.awt.Color(20, 20, 20)
            graphics.fillRect(0, 0, size, size)
            graphics.setRenderingHint(java.awt.RenderingHints.KEY_INTERPOLATION,
                java.awt.RenderingHints.VALUE_INTERPOLATION_BICUBIC)
            graphics.drawImage(image, (size - width) / 2, (size - height) / 2,
                width, height, null)
        } finally {
            graphics.dispose()
        }
        val target = compactLogo.get().asFile
        target.parentFile.mkdirs()
        check(javax.imageio.ImageIO.write(icon, "png", target)) {
            "Unable to create the compact original All-Download Android logo."
        }
    }
}
tasks.named("preBuild") { dependsOn(prepareAndroidBranding) }
