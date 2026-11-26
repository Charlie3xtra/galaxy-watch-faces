package local.artist.engine;

import android.app.*;
import android.content.*;
import android.os.PowerManager;
import java.util.Random;

public final class ArtistApp extends Application {
    private SharedPreferences prefs;
    boolean listening;
    private final Random rng=new java.security.SecureRandom();

    static final long HOUR=3600000L;
    static String encode(int[] cfg) {
        StringBuilder b=new StringBuilder();
        for(int value:cfg) b.append((char)('A'+value));
        return b.toString();
    }
    static int[] decode(String key) {
        int[] cfg=new int[8];
        for(int i=0;i<cfg.length;i++) cfg[i]=key.charAt(i)-'A';
        return cfg;
    }
    @Override public void onCreate() {
        super.onCreate();
        prefs=getSharedPreferences("morph",MODE_PRIVATE);
        registerReceiver(new BroadcastReceiver(){
            @Override public void onReceive(Context c,Intent i) {
                if(prefs.getBoolean("active",false) && expired()) {
                    android.util.Log.i("ArtistMorph","expired wake"); advance(); requestUpdate();
                }
            }
        },new IntentFilter(Intent.ACTION_SCREEN_ON),Context.RECEIVER_NOT_EXPORTED);
    }
    private boolean expired() {
        long now=android.os.SystemClock.elapsedRealtime();
        int boot=android.provider.Settings.Global.getInt(getContentResolver(),"boot_count",-1);
        if(boot!=prefs.getInt("boot",boot)) return true;
        long deadline=prefs.getLong("deadline",Long.MAX_VALUE);
        return now>deadline;
    }
    void prepare() {
        prefs.edit().putBoolean("active",true).apply();
        if(!prefs.contains("deadline")) markDeadline(prefs.edit()).apply();
        // Only a wake notification or a tap advances the current portrait.
    }
    void deactivate() { prefs.edit().putBoolean("active",false).apply(); }
    String current() { return prefs.getString("current",encode(Morph.FIRST)); }
    String previous() { return prefs.getString("previous",current()); }
    boolean forward() { return prefs.getBoolean("forward",false); }
    private SharedPreferences.Editor markDeadline(SharedPreferences.Editor edit) {
        return edit.putLong("deadline",android.os.SystemClock.elapsedRealtime()+HOUR)
            .putInt("boot",android.provider.Settings.Global.getInt(getContentResolver(),"boot_count",-1));
    }
    void advance() {
        String old=current();
        markDeadline(prefs.edit()).putString("previous",old)
            .putString("current",encode(Morph.next(rng,decode(old))))
            .putBoolean("forward",!forward()).commit();
    }
    void requestUpdate() {
        String prefix="android.support.wearable.complications.";
        Intent refresh=new Intent(prefix+"ACTION_REQUEST_UPDATE_ALL").setPackage("com.google.android.wearable.app");
        refresh.putExtra(prefix+"EXTRA_PROVIDER_COMPONENT",new ComponentName(this,PortraitService.class));
        PendingIntent identity=PendingIntent.getBroadcast(this,1,new Intent(this,Tap.class).setAction("identity"),
            PendingIntent.FLAG_IMMUTABLE);
        refresh.putExtra(prefix+"EXTRA_PENDING_INTENT",identity);
        sendBroadcast(refresh);
    }
}





