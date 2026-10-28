package es.joel.tickets

import android.content.Context
import android.net.Uri

// ip, llave y huella del pc. llegan con el enlace tickets://alta del QR
object Ajustes {

    data class Conexion(val ip: String, val puerto: Int, val llave: String, val huella: String)

    private fun prefs(c: Context) = c.getSharedPreferences("conexion", Context.MODE_PRIVATE)

    fun conexion(c: Context): Conexion? {
        val p = prefs(c)
        val llave = p.getString("llave", null) ?: BuildConfig.LLAVE
        val huella = p.getString("huella", null) ?: BuildConfig.HUELLA
        val ip = p.getString("ip", null) ?: BuildConfig.PC_IP
        val puerto = p.getInt("puerto", BuildConfig.PC_PUERTO)
        if (llave.isBlank() || huella.isBlank() || ip.isBlank()) return null
        return Conexion(ip, puerto, llave, huella.lowercase())
    }

    // tickets://alta?u=https://IP:PUERTO&k=LLAVE&h=HUELLA
    fun desdeEnlace(c: Context, enlace: Uri): Boolean {
        if (enlace.scheme != "tickets" || enlace.host != "alta") return false
        val dir = Uri.parse(enlace.getQueryParameter("u") ?: return false)
        val llave = enlace.getQueryParameter("k").orEmpty()
        val huella = enlace.getQueryParameter("h").orEmpty().lowercase()
        val ip = dir.host.orEmpty()
        if (dir.scheme != "https" || ip.isBlank() || llave.isBlank() || !huella.matches(Regex("[0-9a-f]{64}"))) return false
        prefs(c).edit()
            .putString("ip", ip).putInt("puerto", if (dir.port > 0) dir.port else 8768)
            .putString("llave", llave).putString("huella", huella)
            .apply()
        Certificado.olvidar()
        return true
    }

    fun nuevaIp(c: Context, ip: String) = prefs(c).edit().putString("ip", ip).apply()
}
