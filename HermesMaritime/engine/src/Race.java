package local.hermes.maritime;

import android.content.*;
import android.os.SystemClock;
import android.provider.Settings;
import android.app.PendingIntent;

/** Positive remaining seconds count down, negative ones measure time since the start gun. */
final class Race {
    final Context ctx;
    final SharedPreferences p;
    Race(Context ctx){this.ctx=ctx; p=ctx.getSharedPreferences("system_timer",0);}
    String mode(){return p.getString("mode","idle");}
    int minutes(){return p.getInt("minutes",5);}
    long remaining(){
        if(!mode().equals("running")) return p.getLong("paused",minutes()*60000L);
        if(p.getInt("boot",-1)==Settings.Global.getInt(ctx.getContentResolver(),"boot_count",-2))
            return p.getLong("elapsed",0)-SystemClock.elapsedRealtime();
        return p.getLong("wall",0)-System.currentTimeMillis();
    }
    void run(long left){
        if(mode().equals("running") && Math.abs(left-remaining())<500)return;
        save(p.edit().putString("mode","running")
            .putLong("elapsed",SystemClock.elapsedRealtime()+left).putLong("wall",System.currentTimeMillis()+left)
            .putInt("boot",Settings.Global.getInt(ctx.getContentResolver(),"boot_count",-2)));
    }
    void pause(long left){if(mode().equals("paused") && remaining()==left)return;save(p.edit().putLong("paused",left).putString("mode","paused"));}
    void reset(){if(mode().equals("idle"))return;save(p.edit().putString("mode","idle").remove("paused"));}
    private void save(SharedPreferences.Editor e){
        e.apply();
        String prefix="android.support.wearable.complications.";
        Intent update=new Intent(prefix+"ACTION_REQUEST_UPDATE_ALL").setPackage("com.google.android.wearable.app");
        update.putExtra(prefix+"EXTRA_PROVIDER_COMPONENT",new ComponentName(ctx,RaceProvider.class));
        update.putExtra(prefix+"EXTRA_PENDING_INTENT", PendingIntent.getActivity(ctx,1,new Intent(ctx,Setup.class),PendingIntent.FLAG_IMMUTABLE));
        ctx.sendBroadcast(update);
    }
}
