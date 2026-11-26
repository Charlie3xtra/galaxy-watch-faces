package local.artist.engine;
import android.app.PendingIntent;
import android.content.Intent;
import android.graphics.drawable.Icon;
import android.support.wearable.complications.*;

public final class PortraitService extends ComplicationProviderService {
    private String cachedKey="";
    private byte[] cachedAtlas;
    private Portrait painter;
    @Override public void onComplicationUpdate(int id,int type,ComplicationManager manager) {
        if(type!=ComplicationData.TYPE_LONG_TEXT) { manager.noUpdateRequired(id); return; }
        ArtistApp app=(ArtistApp)getApplication();
        app.prepare();
        String prev=app.previous(), next=app.current();
        boolean forward=app.forward();
        String key=prev+next+forward;
        try {
            if(!key.equals(cachedKey)) {
                if(painter==null) painter=new Portrait(this);
                cachedAtlas=painter.atlas(ArtistApp.decode(prev),ArtistApp.decode(next),forward);
                cachedKey=key;
            }
        } catch(java.io.IOException err) { throw new IllegalStateException(err); }
        PendingIntent tap=PendingIntent.getBroadcast(this,0,new Intent(this,Tap.class).setAction("local.artist.NEXT"),
                PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        Icon image=Icon.createWithData(cachedAtlas,0,cachedAtlas.length);
        manager.updateComplicationData(id,new ComplicationData.Builder(type)
            .setLongText(ComplicationText.plainText(forward?"A":"B"))
            .setContentDescription(ComplicationText.plainText("艺术家，点按生成人像"))
            .setSmallImage(image).setImageStyle(ComplicationData.IMAGE_STYLE_PHOTO)
            .setBurnInProtectionSmallImage(image).setTapAction(tap).build());
    }
    @Override public void onComplicationDeactivated(int id) { ((ArtistApp)getApplication()).deactivate(); }
}
