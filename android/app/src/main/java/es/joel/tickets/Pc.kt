package es.joel.tickets

import android.content.Context
import android.net.ConnectivityManager
import android.net.NetworkCapabilities
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.DataOutputStream
import java.net.HttpURLConnection
import javax.net.ssl.HttpsURLConnection
import java.net.Inet4Address
import java.net.URL
import java.util.UUID

/** Busca el PC en la wifi y le manda los tickets de la cola. */
object Pc {

    data class Estado(val ip: String?, val porRevisar: Int, val enviados: Int, val enCola: Int)

    private val candado = Mutex()

    fun direccion(c: Context, ip: String) = "https://$ip:${Ajustes.conexion(c)?.puerto ?: 8768}"

    private fun llave(c: Context) = Ajustes.conexion(c)?.llave.orEmpty()

    /** Conexión cifrada que solo acepta el certificado del PC. */
    private fun abrir(c: Context, url: String): HttpsURLConnection {
        val con = URL(url).openConnection() as HttpsURLConnection
        con.sslSocketFactory = Certificado.fabrica(c) ?: throw IllegalStateException("App sin conectar")
        con.hostnameVerifier = Certificado.verificador(c)
        return con
    }

    fun enWifi(c: Context): Boolean {
        val cm = c.getSystemService(ConnectivityManager::class.java)
        val caps = cm.getNetworkCapabilities(cm.activeNetwork) ?: return false
        return caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI) ||
            caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)
    }

    /** Devuelve lo que contesta el PC, o null si no es él o no responde. */
    private fun ping(c: Context, ip: String, espera: Int): JSONObject? = try {
        val con = abrir(c, "${direccion(c, ip)}/api/ping/")
        con.connectTimeout = espera
        con.readTimeout = espera * 2
        con.setRequestProperty("X-Llave", llave(c))
        try {
            if (con.responseCode != 200) null
            else JSONObject(con.inputStream.bufferedReader().readText())
                .takeIf { it.optString("app") == "presupuesto" }
        } finally {
            con.disconnect()
        }
    } catch (e: Exception) {
        null
    }

    private fun subred(c: Context): String? {
        val cm = c.getSystemService(ConnectivityManager::class.java)
        val props = cm.getLinkProperties(cm.activeNetwork) ?: return null
        val ip = props.linkAddresses.map { it.address }.filterIsInstance<Inet4Address>().firstOrNull()
            ?: return null
        return ip.hostAddress?.substringBeforeLast(".")
    }

    /** Primero la IP de siempre; si el router le dio otra al PC, recorre la wifi entera. */
    suspend fun buscar(c: Context): Pair<String, JSONObject>? = withContext(Dispatchers.IO) {
        if (!enWifi(c)) return@withContext null
        val guardada = Ajustes.conexion(c)?.ip ?: return@withContext null
        ping(c, guardada, 1500)?.let { return@withContext guardada to it }
        val base = subred(c) ?: return@withContext null
        val encontrada = coroutineScope {
            (1..254).map { n ->
                async { "$base.$n".let { ip -> ping(c, ip, 700)?.let { ip to it } } }
            }.awaitAll().firstOrNull { it != null }
        }
        encontrada?.also { Ajustes.nuevaIp(c, it.first) }
    }

    private fun subir(c: Context, ip: String, item: Cola.Item): JSONObject? {
        val limite = "----tickets${UUID.randomUUID()}"
        val con = abrir(c, "${direccion(c, ip)}/api/ticket/")
        return try {
            con.connectTimeout = 4000
            con.readTimeout = 90000
            con.doOutput = true
            con.requestMethod = "POST"
            con.setRequestProperty("X-Llave", llave(c))
            con.setRequestProperty("Content-Type", "multipart/form-data; boundary=$limite")
            DataOutputStream(con.outputStream).use { out ->
                fun campo(nombre: String, valor: String) {
                    out.writeBytes("--$limite\r\nContent-Disposition: form-data; name=\"$nombre\"\r\n\r\n")
                    out.write(valor.toByteArray())
                    out.writeBytes("\r\n")
                }
                campo("uid", item.uid)
                campo("fecha", item.fecha)
                val tipo = if (item.archivo.extension == "pdf") "application/pdf" else "image/jpeg"
                out.writeBytes("--$limite\r\nContent-Disposition: form-data; name=\"archivo\"; filename=\"ticket-${item.fecha}.${item.archivo.extension}\"\r\nContent-Type: $tipo\r\n\r\n")
                item.archivo.inputStream().use { it.copyTo(out) }
                out.writeBytes("\r\n--$limite--\r\n")
            }
            if (con.responseCode != 200) null
            else JSONObject(con.inputStream.bufferedReader().readText()).takeIf { it.optBoolean("ok") }
        } catch (e: Exception) {
            null
        } finally {
            con.disconnect()
        }
    }

    /** Manda todo lo que haya en la cola. Si el PC no está, no pasa nada: se queda para luego. */
    suspend fun enviarTodo(c: Context): Estado = candado.withLock {
        withContext(Dispatchers.IO) {
            val pc = buscar(c)
            if (pc == null) return@withContext Estado(null, 0, 0, Cola.lista(c).size)
            var enviados = 0
            for (item in Cola.lista(c)) {
                val respuesta = subir(c, pc.first, item) ?: break
                Cola.apuntarEnviado(c, item, respuesta)
                Cola.quitar(item)
                enviados++
            }
            val revisar = ping(c, pc.first, 1500)?.optInt("por_revisar") ?: pc.second.optInt("por_revisar")
            Estado(pc.first, revisar, enviados, Cola.lista(c).size)
        }
    }
}
