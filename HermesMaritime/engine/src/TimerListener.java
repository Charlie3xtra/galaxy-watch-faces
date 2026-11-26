package local.hermes.maritime;

import android.app.Notification;
import android.os.Bundle;
import android.os.SystemClock;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;
import android.view.*;
import android.widget.*;
import java.util.regex.*;

public final class TimerListener extends NotificationListenerService {
    private static final String TIMER="com.samsung.android.watch.timer";
    private static final Pattern TIME=Pattern.compile("([\\p{Nd}]+):([\\p{Nd}]{2}):([\\p{Nd}]{2})");
    private static boolean timer(StatusBarNotification s){return TIMER.equals(s.getPackageName()) && "1001".equals(s.getNotification().getChannelId());}
    @Override public void onListenerConnected(){
        StatusBarNotification[] notifications=getActiveNotifications();
        if(notifications!=null)for(StatusBarNotification s:notifications)if(timer(s)){read(s.getNotification());return;}
        new Race(this).reset();
    }
    @Override public void onNotificationPosted(StatusBarNotification s){if(timer(s))read(s.getNotification());}
    @Override public void onNotificationRemoved(StatusBarNotification s){if(timer(s))onListenerConnected();}
    @Override public void onListenerDisconnected(){new Race(this).reset();}
    private Chronometer clock(View v){
        if(v instanceof Chronometer)return (Chronometer)v;
        if(v instanceof ViewGroup){ViewGroup g=(ViewGroup)v;for(int i=0;i<g.getChildCount();i++){
            Chronometer c=clock(g.getChildAt(i));if(c!=null)return c;
        }}
        return null;
    }
    private void read(Notification n){
        Race state=new Race(this);
        try{
            Bundle display=n.extras.getBundle("customDisplayBundle");
            Bundle bar=display==null?null:display.getBundle("nowBarData");
            RemoteViews rv=bar==null?null:bar.getParcelable("cardChronometerRemoteView",RemoteViews.class);
            if(rv!=null && TIMER.equals(rv.getPackage())){
                Chronometer c=clock(rv.apply(this,new FrameLayout(this)));
                if(c!=null && c.isCountDown()){
                    // Samsung adds 1100 ms to the presentation base to round the Now Bar label up.
                    long left=c.getBase()-1100-SystemClock.elapsedRealtime();
                    if(left>0){state.run(left);return;}
                }else if(c!=null){
                    Matcher m=TIME.matcher(c.getText().toString());
                    if(m.matches()){
                        long seconds=Long.parseLong(m.group(1))*3600+Long.parseLong(m.group(2))*60+Long.parseLong(m.group(3));
                        if(seconds>0){state.pause(seconds*1000);return;}
                    }
                }
            }
        }catch(RuntimeException e){android.util.Log.w("MaritimeTimer","Unsupported timer notification layout",e);}
        state.reset();
    }
}
