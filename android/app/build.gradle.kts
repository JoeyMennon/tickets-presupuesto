import java.util.Properties

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// Opcional: secretos.properties con llave, pc_ip, pc_puerto y huella deja la app ya conectada.
// Sin él, la app se conecta leyendo el QR que se crea en el PC, en Móviles.
val secretos = Properties().apply {
    val f = rootProject.file("secretos.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

android {
    namespace = "es.joel.tickets"
    compileSdk = 35

    defaultConfig {
        applicationId = "es.joel.tickets"
        minSdk = 26
        targetSdk = 35
        versionCode = 2
        versionName = "1.1"
        buildConfigField("String", "LLAVE", "\"${secretos.getProperty("llave", "")}\"")
        buildConfigField("String", "PC_IP", "\"${secretos.getProperty("pc_ip", "")}\"")
        buildConfigField("String", "HUELLA", "\"${secretos.getProperty("huella", "")}\"")
        buildConfigField("int", "PC_PUERTO", secretos.getProperty("pc_puerto", "8768"))
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("debug")
        }
    }
    buildFeatures {
        compose = true
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    val bom = platform("androidx.compose:compose-bom:2024.12.01")
    implementation(bom)
    implementation("androidx.compose.ui:ui")
    implementation("androidx.compose.foundation:foundation")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.core:core-ktx:1.15.0")
    implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.8.7")
    implementation("androidx.work:work-runtime-ktx:2.10.0")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.9.0")
    implementation("com.google.android.gms:play-services-mlkit-document-scanner:16.0.0-beta1")
}
