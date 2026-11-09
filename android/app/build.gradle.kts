import java.awt.Color as DesktopColor
import java.awt.RenderingHints
import java.awt.image.BufferedImage

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
        versionCode = 14
        versionName = "0.6.7-beta"
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
// An Android-only asset; Windows's original logo remains unchanged.
val androidLogo = rootProject.projectDir.resolve("branding/android-launcher.jpg")
val compactLogo = layout.buildDirectory.file(
    "generated/all-download-brand/drawable-nodpi/all_download_logo.png"
)
val launcherLogo = layout.buildDirectory.file(
    "generated/all-download-brand/drawable-nodpi/all_download_launcher.png"
)
val androidBrandLogo = layout.buildDirectory.file(
    "generated/all-download-brand/drawable-nodpi/all_download_android_logo.png"
)
val prepareAndroidBranding by tasks.registering {
    inputs.file(originalLogo)
    inputs.file(androidLogo)
    outputs.file(compactLogo)
    outputs.file(launcherLogo)
    outputs.file(androidBrandLogo)
    doLast {
        val image = javax.imageio.ImageIO.read(originalLogo)
            ?: error("Original All-Download logo.jpg is invalid.")
        val size = 192
        val scale = minOf(size.toDouble() / image.width, size.toDouble() / image.height)
        val width = (image.width * scale).toInt().coerceAtLeast(1)
        val height = (image.height * scale).toInt().coerceAtLeast(1)
        val icon = BufferedImage(size, size,
            BufferedImage.TYPE_INT_ARGB)
        val graphics = icon.createGraphics()
        try {
            graphics.color = DesktopColor(20, 20, 20)
            graphics.fillRect(0, 0, size, size)
            graphics.setRenderingHint(RenderingHints.KEY_INTERPOLATION,
                RenderingHints.VALUE_INTERPOLATION_BICUBIC)
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
        // Render the supplied original Android artwork; do not alter logo.jpg.
        val artwork = javax.imageio.ImageIO.read(androidLogo)
            ?: error("Android-only brand artwork is corrupt.")
        check(artwork.width == artwork.height && artwork.width >= 96) {
            "Android app icon source must be square."
        }
        fun renderIcon(size: Int, canvas: Int, destination: java.io.File) {
            val bitmap = BufferedImage(canvas, canvas, BufferedImage.TYPE_INT_ARGB)
            val paint = bitmap.createGraphics()
            try {
                paint.setRenderingHint(RenderingHints.KEY_INTERPOLATION,
                    RenderingHints.VALUE_INTERPOLATION_BICUBIC)
                paint.setRenderingHint(RenderingHints.KEY_RENDERING,
                    RenderingHints.VALUE_RENDER_QUALITY)
                paint.drawImage(artwork, (canvas - size) / 2, (canvas - size) / 2,
                    size, size, null)
            } finally { paint.dispose() }
            destination.parentFile.mkdirs()
            check(javax.imageio.ImageIO.write(bitmap, "png", destination))
        }
        renderIcon(192, 192, androidBrandLogo.get().asFile)
        // Adaptive icon visible region stays inside Android's OEM mask safe zone.
        renderIcon(192, 288, launcherLogo.get().asFile)
    }
}
tasks.named("preBuild") { dependsOn(prepareAndroidBranding) }
