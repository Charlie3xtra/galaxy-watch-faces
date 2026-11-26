package local.artist.engine;
import android.content.*;
public final class Tap extends BroadcastReceiver {
    @Override public void onReceive(Context context,Intent intent) {
        if(!"local.artist.NEXT".equals(intent.getAction())) return;
        ArtistApp app=(ArtistApp)context.getApplicationContext();
        app.advance();
        app.requestUpdate();
    }
}
