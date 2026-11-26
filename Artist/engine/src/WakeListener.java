package local.artist.engine;
import android.app.*;
import android.content.*;
import android.os.IBinder;
public final class WakeListener extends Service {
    @Override public int onStartCommand(Intent i,int flags,int id) {
        String channel="portrait_wake";
        NotificationManager manager=getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel(channel,"表盘亮屏监听",NotificationManager.IMPORTANCE_LOW));
        PendingIntent settings=PendingIntent.getActivity(this,0,new Intent(this,WakeSettings.class),PendingIntent.FLAG_IMMUTABLE);
        Notification notice=new Notification.Builder(this,channel).setSmallIcon(android.R.drawable.ic_menu_recent_history)
            .setContentTitle("艺术家 · 亮屏监听已开启").setContentText("表盘会在到期后亮屏时换脸").setContentIntent(settings)
            .setOngoing(true).setShowWhen(false).build();
        startForeground(1,notice);
        ((ArtistApp)getApplication()).listening=true;
        return START_STICKY;
    }
    @Override public void onDestroy() {
        ((ArtistApp)getApplication()).listening=false;
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent i){return null;}
}

