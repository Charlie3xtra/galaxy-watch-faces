package local.hermes.maritime;

import android.app.Activity;
import android.os.Bundle;
import android.view.Gravity;
import android.widget.*;

public final class RaceControls extends Activity {
    Race race; LinearLayout panel;
    @Override public void onCreate(Bundle state){super.onCreate(state);race=new Race(this);render();}
    void button(int label,Runnable action){Button b=new Button(this);b.setText(label);panel.addView(b);b.setOnClickListener(v->action.run());}
    void render(){
        ScrollView scroll=new ScrollView(this);scroll.setFillViewport(true);
        panel=new LinearLayout(this);panel.setOrientation(1);panel.setGravity(Gravity.CENTER);
        int w=getResources().getDisplayMetrics().widthPixels;
        panel.setPadding(w/7,w/12,w/7,w/12);scroll.addView(panel);setContentView(scroll);
        if(race.mode().equals("idle")){
            TextView title=new TextView(this);title.setText(R.string.minutes);panel.addView(title);
            NumberPicker picker=new NumberPicker(this);picker.setMinValue(1);picker.setMaxValue(60);picker.setValue(race.minutes());
            picker.setDescendantFocusability(NumberPicker.FOCUS_BLOCK_DESCENDANTS);panel.addView(picker,-1,w/3);
            button(R.string.start,()->{int n=picker.getValue();race.run(n*60000L,n);finish();});
        }else if(race.mode().equals("running")){
            button(R.string.pause,()->{race.pause();finish();});
            if(race.remaining()>0)button(R.string.sync,()->{race.run(Math.round(race.remaining()/60000.0)*60000L,race.minutes());finish();});
        }else{
            button(R.string.resume,()->{race.run(race.remaining(),race.minutes());finish();});
            button(R.string.reset,()->{race.reset();finish();});
        }
    }
}
