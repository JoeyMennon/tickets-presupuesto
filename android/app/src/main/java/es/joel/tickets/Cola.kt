package es.joel.tickets

import android.content.Context
import android.net.Uri
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

object Cola {

    data class Item(val archivo: File, val uid: String, val fecha: String)

    data class Enviado(val fecha: String, val sitio: String, val importe: String)

    private fun carpeta(c: Context) = File(c.filesDir, "cola").apply { mkdirs() }

    private fun hoy() = SimpleDateFormat("yyyy-MM-dd", Locale.ROOT).format(Date())

    // nombre: uid__fecha.ext
    fun anadir(c: Context, uri: Uri, extension: String = "jpg"): Boolean {
        val destino = File(carpeta(c), "${UUID.randomUUID()}__${hoy()}.$extension")
        return try {
            c.contentResolver.openInputStream(uri)?.use { entrada ->
                destino.outputStream().use { entrada.copyTo(it) }
            } != null
        } catch (e: Exception) {
            destino.delete()
            false
        }
    }

    fun lista(c: Context): List<Item> =
        carpeta(c).listFiles().orEmpty()
            .filter { it.name.contains("__") }
            .sortedBy { it.lastModified() }
            .map {
                val partes = it.nameWithoutExtension.split("__")
                Item(it, partes[0], partes.getOrElse(1) { hoy() })
            }

    fun quitar(item: Item) {
        item.archivo.delete()
    }

    private fun prefs(c: Context) = c.getSharedPreferences("enviados", Context.MODE_PRIVATE)

    fun apuntarEnviado(c: Context, item: Item, respuesta: JSONObject) {
        val viejos = JSONArray(prefs(c).getString("lista", "[]"))
        val nuevo = JSONObject()
            .put("fecha", item.fecha)
            .put("sitio", respuesta.optString("sitio", ""))
            .put("importe", respuesta.optString("importe", ""))
        val lista = JSONArray().put(nuevo)
        for (i in 0 until minOf(viejos.length(), 14)) lista.put(viejos.get(i))
        prefs(c).edit().putString("lista", lista.toString()).apply()
    }

    fun enviados(c: Context): List<Enviado> {
        val arr = JSONArray(prefs(c).getString("lista", "[]"))
        return (0 until arr.length()).map {
            val o = arr.getJSONObject(it)
            Enviado(o.optString("fecha"), o.optString("sitio"), o.optString("importe"))
        }
    }
}
