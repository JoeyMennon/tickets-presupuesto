package es.joel.tickets

import android.Manifest
import android.annotation.SuppressLint
import android.app.Activity
import android.content.Intent
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.webkit.CookieManager
import android.webkit.WebView
import android.net.http.SslError
import android.webkit.SslErrorHandler
import android.webkit.WebViewClient
import android.widget.Toast
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.activity.result.IntentSenderRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.produceState
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.foundation.Image
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.Font
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontStyle
import androidx.compose.ui.text.font.FontVariation
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import androidx.compose.runtime.DisposableEffect
import com.google.mlkit.vision.documentscanner.GmsDocumentScannerOptions
import com.google.mlkit.vision.documentscanner.GmsDocumentScanning
import com.google.mlkit.vision.documentscanner.GmsDocumentScanningResult
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

// Colores de la web del presupuesto
private class Paleta(val fondo: Color, val papel: Color, val tinta: Color, val suave: Color,
                     val linea: Color, val acento: Color, val acentoFondo: Color,
                     val salvia: Color, val salviaFondo: Color)

private val Clara = Paleta(Color(0xFFF6F1EA), Color(0xFFFFFCF7), Color(0xFF2D2926), Color(0xFF8B827A),
    Color(0xFFEBE3D8), Color(0xFFC48577), Color(0xFFF6E4DE), Color(0xFF4B6646), Color(0xFFE5EDE2))
private val Oscura = Paleta(Color(0xFF191716), Color(0xFF221F1D), Color(0xFFEFE8E0), Color(0xFFA1978E),
    Color(0xFF34302C), Color(0xFFE0A294), Color(0xFF3A2A26), Color(0xFFB9D1B3), Color(0xFF2B3529))

@OptIn(androidx.compose.ui.text.ExperimentalTextApi::class)
private val Sans = FontFamily(
    Font(R.font.dm_sans, FontWeight.Normal, variationSettings = FontVariation.Settings(FontVariation.weight(400))),
    Font(R.font.dm_sans, FontWeight.Medium, variationSettings = FontVariation.Settings(FontVariation.weight(500))),
    Font(R.font.dm_sans, FontWeight.SemiBold, variationSettings = FontVariation.Settings(FontVariation.weight(600))),
)
private val Serif = FontFamily(
    Font(R.font.instrument_serif, FontWeight.Normal),
    Font(R.font.instrument_serif_italic, FontWeight.Normal, FontStyle.Italic),
)

class MainActivity : ComponentActivity() {

    private var abrirRevisar = mutableStateOf(false)
    private var conectada = mutableStateOf(0)

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        recibirCompartido(intent)
        recibirAlta(intent)
        abrirRevisar.value = intent.getBooleanExtra("revisar", false)
        if (Build.VERSION.SDK_INT >= 33) {
            requestPermissions(arrayOf(Manifest.permission.POST_NOTIFICATIONS), 1)
        }
        setContent { Pantalla(this, abrirRevisar, conectada) }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        recibirCompartido(intent)
        recibirAlta(intent)
        if (intent.getBooleanExtra("revisar", false)) abrirRevisar.value = true
    }

    /** Enlace tickets://alta del QR del PC, o del botón «Conectar la app» de la web. */
    private fun recibirAlta(intent: Intent?) {
        val enlace = intent?.data ?: return
        if (intent.action != Intent.ACTION_VIEW) return
        if (Ajustes.desdeEnlace(this, enlace)) {
            Toast.makeText(this, "App conectada al PC", Toast.LENGTH_SHORT).show()
            conectada.value++
        } else {
            Toast.makeText(this, "Ese enlace no es de alta", Toast.LENGTH_LONG).show()
        }
    }

    /** Tickets que llegan desde otra app con Compartir, como el PDF del ticket digital. */
    private fun recibirCompartido(intent: Intent?) {
        if (intent?.action != Intent.ACTION_SEND) return
        @Suppress("DEPRECATION")
        val uri = intent.getParcelableExtra<Uri>(Intent.EXTRA_STREAM) ?: return
        val ext = if (contentResolver.getType(uri) == "application/pdf") "pdf" else "jpg"
        if (Cola.anadir(this, uri, ext)) {
            Toast.makeText(this, "Ticket guardado. Se enviará al PC.", Toast.LENGTH_SHORT).show()
            EnvioWorker.pronto(this)
        }
    }
}

@Composable
private fun Pantalla(
    actividad: Activity,
    abrirRevisar: androidx.compose.runtime.MutableState<Boolean>,
    conectada: androidx.compose.runtime.MutableState<Int>,
) {
    val p = if (isSystemInDarkTheme()) Oscura else Clara
    val c = LocalContext.current
    val conexion = remember(conectada.value) { Ajustes.conexion(c) }
    val scope = rememberCoroutineScope()

    var cola by remember { mutableStateOf(Cola.lista(c)) }
    var enviados by remember { mutableStateOf(Cola.enviados(c)) }
    var estado by remember { mutableStateOf<Pc.Estado?>(null) }
    var buscando by remember { mutableStateOf(false) }

    fun refrescar() {
        if (buscando) return
        buscando = true
        scope.launch {
            estado = Pc.enviarTodo(c)
            cola = Cola.lista(c)
            enviados = Cola.enviados(c)
            buscando = false
        }
    }

    val escaner = rememberLauncherForActivityResult(ActivityResultContracts.StartIntentSenderForResult()) { r ->
        if (r.resultCode == Activity.RESULT_OK) {
            val paginas = GmsDocumentScanningResult.fromActivityResultIntent(r.data)?.pages.orEmpty()
            paginas.forEach { Cola.anadir(c, it.imageUri) }
            cola = Cola.lista(c)
            EnvioWorker.pronto(c)
            refrescar()
        }
    }

    // Móviles sin servicios de Google: se elige la foto de la galería o de la cámara
    val galeria = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null && Cola.anadir(c, uri)) {
            cola = Cola.lista(c)
            EnvioWorker.pronto(c)
            refrescar()
        }
    }

    fun escanear() {
        val opciones = GmsDocumentScannerOptions.Builder()
            .setGalleryImportAllowed(true)
            .setPageLimit(1)
            .setResultFormats(GmsDocumentScannerOptions.RESULT_FORMAT_JPEG)
            .setScannerMode(GmsDocumentScannerOptions.SCANNER_MODE_FULL)
            .build()
        GmsDocumentScanning.getClient(opciones).getStartScanIntent(actividad)
            .addOnSuccessListener { escaner.launch(IntentSenderRequest.Builder(it).build()) }
            .addOnFailureListener { galeria.launch("image/*") }
    }

    // Al volver a la app, mira si el PC está
    val ciclo = LocalLifecycleOwner.current
    DisposableEffect(ciclo) {
        val obs = LifecycleEventObserver { _, e -> if (e == Lifecycle.Event.ON_RESUME) { cola = Cola.lista(c); refrescar() } }
        ciclo.lifecycle.addObserver(obs)
        onDispose { ciclo.lifecycle.removeObserver(obs) }
    }

    val ip = estado?.ip
    if (abrirRevisar.value && ip != null && conexion != null) {
        Revisar(p, "${Pc.direccion(c, ip)}/movil/?k=${Uri.encode(conexion.llave)}") { abrirRevisar.value = false; refrescar() }
        return
    }

    val texto = TextStyle(fontFamily = Sans, color = p.tinta, fontSize = 15.sp)

    if (conexion == null) {
        SinConectar(p, texto)
        return
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize().background(p.fondo).safeDrawingPadding(),
        contentPadding = PaddingValues(horizontal = 18.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("✦ ", style = texto.copy(color = p.acento))
                Text("agenda & cuentas", style = texto.copy(fontFamily = Serif, fontStyle = FontStyle.Italic, fontSize = 20.sp))
            }
            Spacer(Modifier.height(18.dp))
            Text("tickets", style = texto.copy(fontFamily = Serif, fontStyle = FontStyle.Italic, fontSize = 64.sp, lineHeight = 60.sp))
            Spacer(Modifier.height(10.dp))
            EstadoPc(p, texto, estado, buscando) { refrescar() }
        }

        item {
            Column(
                Modifier.fillMaxWidth().clip(RoundedCornerShape(24.dp)).background(p.acento)
                    .clickable { escanear() }.padding(22.dp),
            ) {
                Text("✦", style = texto.copy(color = Color.White, fontSize = 22.sp))
                Spacer(Modifier.height(18.dp))
                Text("Escanear ticket", style = texto.copy(color = Color.White, fontFamily = Serif, fontSize = 34.sp))
                Text(
                    "Se guarda aquí y se pasa solo al PC cuando estés en casa.",
                    style = texto.copy(color = Color.White.copy(alpha = .85f), fontSize = 14.sp),
                )
            }
        }

        if (ip != null && (estado?.porRevisar ?: 0) > 0) {
            item {
                Tarjeta(p, Modifier.clickable { abrirRevisar.value = true }) {
                    Text("EN EL PC", style = etiqueta(texto, p))
                    Row(verticalAlignment = Alignment.Bottom) {
                        Text("${estado?.porRevisar} por revisar", style = texto.copy(fontFamily = Serif, fontSize = 28.sp), modifier = Modifier.weight(1f))
                        Text("Revisar ›", style = texto.copy(color = p.acento, fontWeight = FontWeight.SemiBold))
                    }
                }
            }
        } else if (ip != null) {
            item {
                Tarjeta(p, Modifier.clickable { abrirRevisar.value = true }) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Text("Ver el presupuesto y los últimos gastos", style = texto, modifier = Modifier.weight(1f))
                        Text("›", style = texto.copy(color = p.acento, fontSize = 22.sp))
                    }
                }
            }
        }

        if (cola.isNotEmpty()) {
            item { Text("EN COLA · ${cola.size}", style = etiqueta(texto, p), modifier = Modifier.padding(top = 6.dp)) }
            items(cola, key = { it.uid }) { t ->
                Tarjeta(p) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Miniatura(t.archivo, p)
                        Spacer(Modifier.width(14.dp))
                        Column(Modifier.weight(1f)) {
                            Text("Ticket del ${fechaBonita(t.fecha)}", style = texto.copy(fontWeight = FontWeight.Medium))
                            Text("Esperando al PC", style = texto.copy(color = p.suave, fontSize = 13.sp))
                        }
                        Text(
                            "×", style = texto.copy(color = p.suave, fontSize = 24.sp),
                            modifier = Modifier.clip(CircleShape).clickable { Cola.quitar(t); cola = Cola.lista(c) }.padding(horizontal = 10.dp),
                        )
                    }
                }
            }
        }

        if (enviados.isNotEmpty()) {
            item { Text("YA EN EL PC", style = etiqueta(texto, p), modifier = Modifier.padding(top = 6.dp)) }
            items(enviados) { e ->
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 4.dp, vertical = 2.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(Modifier.size(8.dp).clip(CircleShape).background(p.salvia))
                    Spacer(Modifier.width(10.dp))
                    Text(
                        listOf(e.sitio.ifBlank { "Ticket" }, fechaBonita(e.fecha)).joinToString(" · "),
                        style = texto.copy(fontSize = 14.sp), modifier = Modifier.weight(1f),
                    )
                    Text(if (e.importe.isBlank()) "por leer" else e.importe.replace(".", ",") + " €",
                        style = texto.copy(fontSize = 14.sp, color = p.suave))
                }
            }
        }
        item { Spacer(Modifier.height(24.dp)) }
    }

    LaunchedEffect(conectada.value) { refrescar() }
}

@Composable
private fun SinConectar(p: Paleta, texto: TextStyle) {
    Column(
        Modifier.fillMaxSize().background(p.fondo).safeDrawingPadding().padding(horizontal = 18.dp, vertical = 16.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("✦ ", style = texto.copy(color = p.acento))
            Text("agenda & cuentas", style = texto.copy(fontFamily = Serif, fontStyle = FontStyle.Italic, fontSize = 20.sp))
        }
        Spacer(Modifier.height(8.dp))
        Text("tickets", style = texto.copy(fontFamily = Serif, fontStyle = FontStyle.Italic, fontSize = 64.sp, lineHeight = 60.sp))
        Tarjeta(p) {
            Text("CONECTAR CON EL PC", style = etiqueta(texto, p))
            Spacer(Modifier.height(8.dp))
            listOf(
                "En el PC, abre el presupuesto y entra en Móviles.",
                "Crea un QR para este móvil.",
                "Escanéalo con la cámara y abre el enlace con Tickets.",
            ).forEachIndexed { i, paso ->
                Row(Modifier.padding(vertical = 4.dp)) {
                    Text("${i + 1}", style = texto.copy(color = p.acento, fontWeight = FontWeight.SemiBold), modifier = Modifier.width(22.dp))
                    Text(paso, style = texto)
                }
            }
        }
    }
}

@Composable
private fun EstadoPc(p: Paleta, texto: TextStyle, estado: Pc.Estado?, buscando: Boolean, alPulsar: () -> Unit) {
    val (punto, frase) = when {
        buscando -> p.suave to "Buscando el PC…"
        estado?.ip != null -> p.salvia to "PC conectado"
        else -> p.acento to "Fuera de casa o PC apagado"
    }
    Row(
        Modifier.clip(RoundedCornerShape(50)).background(p.papel).border(1.dp, p.linea, RoundedCornerShape(50))
            .clickable { alPulsar() }.padding(horizontal = 14.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(8.dp).clip(CircleShape).background(punto))
        Spacer(Modifier.width(8.dp))
        Text(frase, style = texto.copy(fontSize = 13.sp, fontWeight = FontWeight.Medium))
    }
}

@Composable
private fun Tarjeta(p: Paleta, modifier: Modifier = Modifier, contenido: @Composable () -> Unit) {
    Column(
        Modifier.fillMaxWidth().clip(RoundedCornerShape(20.dp)).background(p.papel)
            .border(1.dp, p.linea, RoundedCornerShape(20.dp)).then(modifier).padding(16.dp),
    ) { contenido() }
}

@Composable
private fun Miniatura(archivo: File, p: Paleta) {
    val imagen by produceState<Bitmap?>(null, archivo) {
        value = withContext(Dispatchers.IO) {
            if (archivo.extension == "pdf") null
            else BitmapFactory.decodeFile(archivo.path, BitmapFactory.Options().apply { inSampleSize = 8 })
        }
    }
    Box(
        Modifier.size(52.dp).clip(RoundedCornerShape(12.dp)).background(p.acentoFondo),
        contentAlignment = Alignment.Center,
    ) {
        val bmp = imagen
        if (bmp != null) {
            Image(bmp.asImageBitmap(), null, contentScale = ContentScale.Crop, modifier = Modifier.fillMaxSize())
        } else {
            Text(if (archivo.extension == "pdf") "PDF" else "✦", style = TextStyle(color = p.acento, fontFamily = Sans, fontWeight = FontWeight.SemiBold))
        }
    }
}

@SuppressLint("SetJavaScriptEnabled")
@Composable
private fun Revisar(p: Paleta, url: String, volver: () -> Unit) {
    BackHandler { volver() }
    Column(Modifier.fillMaxSize().background(p.fondo).safeDrawingPadding()) {
        Row(
            Modifier.fillMaxWidth().clickable { volver() }.padding(horizontal = 18.dp, vertical = 12.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text("‹  Tickets", style = TextStyle(fontFamily = Sans, color = p.acento, fontSize = 16.sp, fontWeight = FontWeight.Medium))
        }
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = { ctx ->
                CookieManager.getInstance().setAcceptCookie(true)
                WebView(ctx).apply {
                    setBackgroundColor(android.graphics.Color.TRANSPARENT)
                    settings.javaScriptEnabled = true
                    webViewClient = object : WebViewClient() {
                        // Solo se sigue si el certificado es exactamente el del PC de casa
                        override fun onReceivedSslError(v: WebView, h: SslErrorHandler, e: SslError) {
                            val cert = if (Build.VERSION.SDK_INT >= 29) e.certificate.x509Certificate else null
                            if (Certificado.esElNuestro(ctx, cert)) h.proceed() else h.cancel()
                        }
                    }
                    loadUrl(url)
                }
            },
        )
    }
}

private fun etiqueta(t: TextStyle, p: Paleta) = t.copy(color = p.suave, fontSize = 11.sp, letterSpacing = 1.4.sp, fontWeight = FontWeight.Medium)

private val MESES = listOf("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")

private fun fechaBonita(iso: String): String {
    val partes = iso.split("-")
    if (partes.size != 3) return iso
    val mes = partes[1].toIntOrNull()?.let { MESES.getOrNull(it - 1) } ?: return iso
    return "${partes[2].trimStart('0')} $mes"
}
