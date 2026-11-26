package local.hermes.maritime;

import android.app.PendingIntent;
import android.content.Intent;
import android.support.wearable.complications.*;

public final class RaceProvider extends ComplicationProviderService {
    @Override public void onComplicationUpdate(int id,int type,ComplicationManager mgr){
        if(type!=ComplicationData.TYPE_RANGED_VALUE){mgr.noUpdateRequired(id);return;}
        Race r=new Race(this);String mode=r.mode();long left=r.remaining();
        long deadline=Math.floorDiv(System.currentTimeMillis()+left+999,1000);
        // Day and second-of-day each fit exactly into the protocol's float fields.
        float min=-Math.floorDiv(deadline,86400);
        float value=Math.floorMod(deadline,86400);
        float max=86400+r.minutes()*60;
        if(mode.equals("paused")){
            mode=left>=0?"paused":"overtime";value=(float)Math.ceil(Math.abs(left)/1000.0);
            min=-r.minutes()*60;max=Math.max(90000,value);
        }
        PendingIntent tap=PendingIntent.getActivity(this,0,new Intent(this,RaceControls.class),PendingIntent.FLAG_IMMUTABLE|PendingIntent.FLAG_UPDATE_CURRENT);
        mgr.updateComplicationData(id,new ComplicationData.Builder(type)
            .setMinValue(min).setMaxValue(max).setValue(value)
            .setShortText(ComplicationText.plainText(mode)).setContentDescription(ComplicationText.plainText(getString(R.string.face_name)))
            .setTapAction(tap).build());
    }
}
