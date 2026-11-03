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
import androidx.activity.SystemBarStyle
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

// mismos colores que la web: fondo, papel, línea, acento y fondo del acento, en claro y en oscuro
private class Paleta(val fondo: Color, val papel: Color, val tinta: Color, val suave: Color,
                     val linea: Color, val acento: Color, val acentoFondo: Color,
                     val salvia: Color, val salviaFondo: Color, val sobreAcento: Color, val oscura: Boolean)

private val TONOS = mapOf(
    "rosa" to (listOf(0xFFF6F1EA, 0xFFFFFCF7, 0xFFEBE3D8, 0xFFC48577, 0xFFF6E4DE) to listOf(0xFF191716, 0xFF221F1D, 0xFF34302C, 0xFFE0A294, 0xFF3A2A26)),
    "salvia" to (listOf(0xFFEFF3EC, 0xFFFBFDF9, 0xFFDFE7DA, 0xFF5F8159, 0xFFE0EADC) to listOf(0xFF151A16, 0xFF1D231E, 0xFF2D362E, 0xFFA9C7A2, 0xFF26302A)),
    "lavanda" to (listOf(0xFFF2F0F8, 0xFFFDFCFF, 0xFFE3DFEF, 0xFF7A6BB3, 0xFFE9E4F6) to listOf(0xFF17161D, 0xFF1F1D27, 0xFF312E3D, 0xFFBCAEEA, 0xFF2C2740)),
    "cielo" to (listOf(0xFFEEF3F7, 0xFFFBFDFF, 0xFFDCE6EE, 0xFF4F7FA3, 0xFFDEEBF5) to listOf(0xFF141A1F, 0xFF1B2229, 0xFF2B3540, 0xFF9CC3E2, 0xFF1F2E3A)),
    "miel" to (listOf(0xFFF7F2E7, 0xFFFFFDF7, 0xFFECE2CC, 0xFFA87A2C, 0xFFF6ECD5) to listOf(0xFF1A1814, 0xFF221F19, 0xFF36302A, 0xFFE2BF7A, 0xFF372D1C)),
)
private val MUESTRA = mapOf("rosa" to 0xFFC48577, "salvia" to 0xFF6F8F69, "lavanda" to 0xFF8B7CC0, "cielo" to 0xFF5F8DB0, "miel" to 0xFFC99A45)

private fun paleta(oscura: Boolean, color: String): Paleta {
    val (clara, noche) = TONOS[color] ?: TONOS.getValue("rosa")
    val t = (if (oscura) noche else clara).map { Color(it) }
    return if (oscura) Paleta(t[0], t[1], Color(0xFFEFE8E0), Color(0xFFA89E95), t[2], t[3], t[4],
        Color(0xFFB9D1B3), Color(0xFF2B3529), Color(0xFF1A1716), true)
    else Paleta(t[0], t[1], Color(0xFF2D2926), Color(0xFF7D746C), t[2], t[3], t[4],
        Color(0xFF4B6646), Color(0xFFE5EDE2), Color.White, false)
}

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

    // compartir desde otra app, como el pdf del ticket digital
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
    val c = LocalContext.current
    var modo by remember { mutableStateOf(Ajustes.modo(c)) }
    var color by remember { mutableStateOf(Ajustes.color(c)) }
    var eligiendoTema by remember { mutableStateOf(false) }
    val sistemaOscuro = isSystemInDarkTheme()
    val p = paleta(if (modo == "auto") sistemaOscuro else modo == "oscuro", color)
    fun cambiarTema(m: String, col: String) { modo = m; color = col; Ajustes.tema(c, m, col) }
    // iconos de la barra de arriba a juego con el tema elegido
    LaunchedEffect(p.oscura) {
        val estilo = if (p.oscura) SystemBarStyle.dark(android.graphics.Color.TRANSPARENT)
        else SystemBarStyle.light(android.graphics.Color.TRANSPARENT, android.graphics.Color.TRANSPARENT)
        (actividad as ComponentActivity).enableEdgeToEdge(estilo, estilo)
    }
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

    // sin google play services no hay escáner, tiro de galería
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

    val ciclo = LocalLifecycleOwner.current
    DisposableEffect(ciclo) {
        val obs = LifecycleEventObserver { _, e -> if (e == Lifecycle.Event.ON_RESUME) { cola = Cola.lista(c); refrescar() } }
        ciclo.lifecycle.addObserver(obs)
        onDispose { ciclo.lifecycle.removeObserver(obs) }
    }

    val ip = estado?.ip
    if (abrirRevisar.value && ip != null && conexion != null) {
        val base = Pc.direccion(c, ip)
        Revisar(p, base, "$base/movil/?k=${Uri.encode(conexion.llave)}", modo, color) {
            // si ha cambiado el tema en la web, la app se queda con él
            val galletas = CookieManager.getInstance().getCookie(base).orEmpty()
            val leer = { n: String -> Regex("(?:^|; )$n=([a-z]+)").find(galletas)?.groupValues?.get(1) }
            val m = leer("modo")?.takeIf { v -> Ajustes.MODOS.any { it.first == v } } ?: modo
            val col = leer("color")?.takeIf { it in Ajustes.COLORES } ?: color
            if (m != modo || col != color) cambiarTema(m, col)
            abrirRevisar.value = false
            refrescar()
        }
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
                Text("agenda & cuentas", style = texto.copy(fontFamily = Serif, fontStyle = FontStyle.Italic, fontSize = 20.sp), modifier = Modifier.weight(1f))
                Row(
                    Modifier.clip(RoundedCornerShape(50)).background(p.papel).border(1.dp, p.linea, RoundedCornerShape(50))
                        .clickable { eligiendoTema = !eligiendoTema }.padding(horizontal = 12.dp, vertical = 6.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Box(Modifier.size(16.dp).clip(CircleShape).background(p.acento))
                    Spacer(Modifier.width(6.dp))
                    Text("Tema", style = texto.copy(fontSize = 13.sp, color = p.suave))
                }
            }
            if (eligiendoTema) {
                Spacer(Modifier.height(12.dp))
                ElegirTema(p, texto, modo, color) { m, col -> cambiarTema(m, col) }
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
                Text("✦", style = texto.copy(color = p.sobreAcento, fontSize = 22.sp))
                Spacer(Modifier.height(18.dp))
                Text("Escanear ticket", style = texto.copy(color = p.sobreAcento, fontFamily = Serif, fontSize = 34.sp))
                Text(
                    "Se guarda aquí y se pasa solo al PC cuando estés en casa.",
                    style = texto.copy(color = p.sobreAcento.copy(alpha = .85f), fontSize = 14.sp),
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
                        Column(Modifier.weight(1f)) {
                            Text("Presupuesto y gastos", style = texto.copy(fontFamily = Serif, fontSize = 24.sp))
                            Text("Ver lo que queda y cambiar cualquier gasto", style = texto.copy(color = p.suave, fontSize = 13.sp))
                        }
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
private fun Revisar(p: Paleta, base: String, url: String, modo: String, color: String, volver: () -> Unit) {
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
                CookieManager.getInstance().apply {
                    setAcceptCookie(true)
                    setCookie(base, "modo=$modo; Max-Age=31536000; Path=/; SameSite=Lax")
                    setCookie(base, "color=$color; Max-Age=31536000; Path=/; SameSite=Lax")
                    flush()
                }
                WebView(ctx).apply {
                    setBackgroundColor(android.graphics.Color.TRANSPARENT)
                    settings.javaScriptEnabled = true
                    webViewClient = object : WebViewClient() {
                        // autofirmado: solo seguimos si es el nuestro
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

@Composable
private fun ElegirTema(p: Paleta, texto: TextStyle, modo: String, color: String, elegir: (String, String) -> Unit) {
    Tarjeta(p) {
        Text("FONDO", style = etiqueta(texto, p))
        Spacer(Modifier.height(8.dp))
        Row(Modifier.fillMaxWidth().clip(RoundedCornerShape(14.dp)).background(p.fondo).padding(3.dp)) {
            Ajustes.MODOS.forEach { (valor, nombre) ->
                val activo = valor == modo
                Box(
                    Modifier.weight(1f).clip(RoundedCornerShape(11.dp)).background(if (activo) p.tinta else Color.Transparent)
                        .clickable { elegir(valor, color) }.padding(vertical = 10.dp),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(nombre, style = texto.copy(fontSize = 13.sp, color = if (activo) p.papel else p.suave,
                        fontWeight = if (activo) FontWeight.SemiBold else FontWeight.Normal))
                }
            }
        }
        Spacer(Modifier.height(14.dp))
        Text("COLOR", style = etiqueta(texto, p))
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            Ajustes.COLORES.forEach { valor ->
                Box(
                    Modifier.size(40.dp).clip(CircleShape)
                        .border(if (valor == color) 3.dp else 1.dp, if (valor == color) p.tinta else p.linea, CircleShape)
                        .padding(5.dp).clip(CircleShape).background(Color(MUESTRA.getValue(valor)))
                        .clickable { elegir(modo, valor) },
                )
            }
        }
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
