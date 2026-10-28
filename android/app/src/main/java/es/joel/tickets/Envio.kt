package es.joel.tickets

import android.Manifest
import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import androidx.work.Constraints
import androidx.work.CoroutineWorker
import androidx.work.ExistingPeriodicWorkPolicy
import androidx.work.ExistingWorkPolicy
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.PeriodicWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.WorkerParameters
import java.util.concurrent.TimeUnit

class App : Application() {
    override fun onCreate() {
        super.onCreate()
        val canal = NotificationChannel(EnvioWorker.CANAL, "Tickets enviados", NotificationManager.IMPORTANCE_DEFAULT)
        getSystemService(NotificationManager::class.java).createNotificationChannel(canal)
        EnvioWorker.programar(this)
    }
}

// cada 15 min con wifi intenta mandar la cola
class EnvioWorker(c: Context, p: WorkerParameters) : CoroutineWorker(c, p) {

    override suspend fun doWork(): Result {
        if (Cola.lista(applicationContext).isEmpty()) return Result.success()
        val estado = Pc.enviarTodo(applicationContext)
        if (estado.enviados > 0) avisar(estado)
        return Result.success()
    }

    private fun avisar(estado: Pc.Estado) {
        val c = applicationContext
        if (Build.VERSION.SDK_INT >= 33 &&
            ContextCompat.checkSelfPermission(c, Manifest.permission.POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED
        ) return
        val abrir = PendingIntent.getActivity(
            c, 0, Intent(c, MainActivity::class.java).putExtra("revisar", true),
            PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT,
        )
        val texto = if (estado.enviados == 1) "1 ticket ha llegado al PC" else "${estado.enviados} tickets han llegado al PC"
        val aviso = NotificationCompat.Builder(c, CANAL)
            .setSmallIcon(R.drawable.ic_aviso)
            .setContentTitle(texto)
            .setContentText("Toca para revisarlos")
            .setContentIntent(abrir)
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(c).notify(1, aviso)
    }

    companion object {
        const val CANAL = "enviados"
        private val conWifi = Constraints.Builder().setRequiredNetworkType(NetworkType.UNMETERED).build()

        fun programar(c: Context) {
            val trabajo = PeriodicWorkRequestBuilder<EnvioWorker>(15, TimeUnit.MINUTES)
                .setConstraints(conWifi).build()
            WorkManager.getInstance(c).enqueueUniquePeriodicWork("envio", ExistingPeriodicWorkPolicy.KEEP, trabajo)
        }

        fun pronto(c: Context) {
            val trabajo = OneTimeWorkRequestBuilder<EnvioWorker>().setConstraints(conWifi).build()
            WorkManager.getInstance(c).enqueueUniqueWork("envio-pronto", ExistingWorkPolicy.REPLACE, trabajo)
        }
    }
}
