package es.joel.tickets

import android.annotation.SuppressLint
import android.content.Context
import java.security.MessageDigest
import java.security.cert.CertificateException
import java.security.cert.X509Certificate
import javax.net.ssl.HostnameVerifier
import javax.net.ssl.SSLContext
import javax.net.ssl.SSLSocketFactory
import javax.net.ssl.X509TrustManager

/**
 * La app solo habla con un aparato cuyo certificado tenga la huella SHA-256 del QR.
 * Si otro se hace pasar por el PC, la conexión se corta antes de mandar la llave.
 */
object Certificado {

    @Volatile private var cache: Pair<String, SSLSocketFactory>? = null

    fun olvidar() { cache = null }

    fun huella(cert: X509Certificate): String =
        MessageDigest.getInstance("SHA-256").digest(cert.encoded).joinToString("") { "%02x".format(it) }

    fun esElNuestro(c: Context, otro: X509Certificate?): Boolean {
        val esperada = Ajustes.conexion(c)?.huella ?: return false
        return otro != null && MessageDigest.isEqual(huella(otro).toByteArray(), esperada.toByteArray())
    }

    @SuppressLint("CustomX509TrustManager")
    private class SoloElNuestro(val esperada: String) : X509TrustManager {
        override fun checkClientTrusted(chain: Array<out X509Certificate>?, authType: String?) =
            throw CertificateException("No se usa")

        override fun checkServerTrusted(chain: Array<out X509Certificate>?, authType: String?) {
            val primero = chain?.firstOrNull() ?: throw CertificateException("Sin certificado")
            if (!MessageDigest.isEqual(huella(primero).toByteArray(), esperada.toByteArray())) {
                throw CertificateException("No es el certificado del PC")
            }
        }

        override fun getAcceptedIssuers(): Array<X509Certificate> = emptyArray()
    }

    fun fabrica(c: Context): SSLSocketFactory? {
        val esperada = Ajustes.conexion(c)?.huella ?: return null
        cache?.let { if (it.first == esperada) return it.second }
        val ssl = SSLContext.getInstance("TLS").apply { init(null, arrayOf(SoloElNuestro(esperada)), null) }
        return ssl.socketFactory.also { cache = esperada to it }
    }

    /** La IP del PC puede cambiar; lo que vale es que el certificado sea exactamente el nuestro. */
    fun verificador(c: Context) = HostnameVerifier { _, sesion ->
        esElNuestro(c, sesion.peerCertificates.firstOrNull() as? X509Certificate)
    }
}
