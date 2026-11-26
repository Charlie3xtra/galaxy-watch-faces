package local.artist.engine;
import android.app.*;
import local.artist.watchface.R;
import android.content.res.Configuration;
import android.content.*;
import android.os.IBinder;
public final class WakeListener extends Service {
    @Override public int onStartCommand(Intent i,int flags,int id) {
        updateNotification();
        ((ArtistApp)getApplication()).listening=true;
        return START_STICKY;
    }
    @Override public void onConfigurationChanged(Configuration config){
        super.onConfigurationChanged(config);
        updateNotification();
    }
    private void updateNotification(){
        String channel="portrait_wake";
        NotificationManager manager=getSystemService(NotificationManager.class);
        manager.createNotificationChannel(new NotificationChannel(channel,getString(R.string.face_name),NotificationManager.IMPORTANCE_LOW));
        PendingIntent settings=PendingIntent.getActivity(this,0,new Intent(this,WakeSettings.class),PendingIntent.FLAG_IMMUTABLE);
        Notification notice=new Notification.Builder(this,channel).setSmallIcon(android.R.drawable.ic_menu_recent_history)
            .setContentTitle(getString(R.string.face_name)).setContentText(getString(R.string.wake_notice)).setContentIntent(settings)
            .setOngoing(true).setShowWhen(false).build();
        startForeground(1,notice);
    }
    @Override public void onDestroy() {
        ((ArtistApp)getApplication()).listening=false;
        super.onDestroy();
    }
    @Override public IBinder onBind(Intent i){return null;}
}
