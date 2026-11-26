package local.hermes.maritime;

import android.app.Activity;
import local.hermes.maritime.R;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.*;
import android.view.Gravity;
import android.widget.*;
import com.google.wear.Sdk;
import com.google.wear.services.watchfaces.watchfacepush.*;
import java.io.*;
import java.nio.charset.StandardCharsets;
import java.nio.file.*;
import java.util.function.Consumer;

public final class Setup extends Activity {
    private WatchFacePushManager manager;
    private static final String ACTIVATE="com.google.wear.permission.SET_PUSHED_WATCH_FACE_AS_ACTIVE";
    private String slot;
    private ParcelFileDescriptor upload;
    private void closeUpload(){if(upload!=null){try{upload.close();}catch(IOException ignored){} upload=null;}}
    private TextView status;
    private Button apply;
    private <T,E extends Throwable> OutcomeReceiver<T,E> callback(Consumer<T> ok) {
        return new OutcomeReceiver<T,E>() {
            public void onResult(T value){ok.accept(value);}
            public void onError(E err){fail(err);}
        };
    }
    private void fail(Throwable err) {
        closeUpload();android.util.Log.e("MaritimePush","Watch face registration",err);
        status.setText(R.string.setup_error);
        apply.setVisibility(android.view.View.VISIBLE);apply.setText(R.string.retry);apply.setEnabled(true);
    }
    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        LinearLayout panel=new LinearLayout(this);panel.setOrientation(1);panel.setGravity(Gravity.CENTER);
        int pad=Math.round(getResources().getDisplayMetrics().density*22);panel.setPadding(pad,0,pad,0);
        status=new TextView(this);status.setGravity(Gravity.CENTER);status.setText(R.string.face_name);panel.addView(status);
        apply=new Button(this);
        apply.setVisibility(android.view.View.GONE);
        panel.addView(apply);
        setContentView(panel);
        apply.setOnClickListener(b->{
            apply.setVisibility(android.view.View.GONE);
            register();
        });
        
        manager=Sdk.getWearManager(this,WatchFacePushManager.class);
        register();
    }
    private void register() {
        apply.setEnabled(false);
        if(manager==null){fail(new IllegalStateException("Watch Face Push unavailable"));return;}
        if(getPackageManager().resolveService(new Intent("com.google.wear.ACTION_PUSH_WATCH_FACES"),PackageManager.MATCH_SYSTEM_ONLY)==null){fail(new IllegalStateException("System watch face service unavailable"));return;}
        manager.listWatchFaceSlots(getMainExecutor(),callback((ListWatchFaceSlotsResponse response)->{
            for(WatchFaceSlot face:response.getInstalledWatchFaceSlots()){
                if(face.getPackageName().equals(getPackageName()+".watchfacepush.maritime") && face.getVersionCode()>=8){ready(face);return;}
                if(face.getPackageName().equals(getPackageName()+".watchfacepush.maritime")){

                    push(face.getSlotId());return;
                }
            }
            push(null);
        }));
    }
    private void push(String id) {
        try {
            File file=new File(getCacheDir(),"maritime.apk");
            try(InputStream in=getAssets().open("maritime.wff")){Files.copy(in,file.toPath(),StandardCopyOption.REPLACE_EXISTING);}
            String token;
            try(BufferedReader in=new BufferedReader(new InputStreamReader(getAssets().open("push-token.txt"),StandardCharsets.UTF_8))){token=in.readLine().trim();}
            { upload=ParcelFileDescriptor.open(file,ParcelFileDescriptor.MODE_READ_ONLY);
                if(id==null)manager.addWatchFace(upload,token,getMainExecutor(),callback(this::ready));
                else manager.updateWatchFace(id,upload,token,getMainExecutor(),callback(this::ready));
            }
        }catch(Exception err){fail(err);}
    }
    private void ready(WatchFaceSlot face) {
        closeUpload();slot=face.getSlotId();android.util.Log.i("MaritimePush","Registered "+face.getPackageName());
        manager.isWatchFaceActive(face.getPackageName(),getMainExecutor(),callback(active->{
            if(active){finish();return;}
            if(getPreferences(0).getBoolean("activationUsed",false)){
                manualSelection();return;
            }
            if(checkSelfPermission(ACTIVATE)==PackageManager.PERMISSION_GRANTED){activate();return;}
            if(getPreferences(0).getBoolean("permissionRequested",false)){manualSelection();return;}
            getPreferences(0).edit().putBoolean("permissionRequested",true).apply();
            requestPermissions(new String[]{ACTIVATE},1);
        }));
    }
    private void manualSelection(){status.setText(getString(R.string.manual_selection,getString(R.string.face_name)));}
    private void activate(){
        manager.setWatchFaceAsActive(slot,getMainExecutor(),new OutcomeReceiver<Void,WatchFacePushManager.SetActiveException>(){
            public void onResult(Void unused){
                getPreferences(0).edit().putBoolean("activationUsed",true).apply();finish();
            }
            public void onError(WatchFacePushManager.SetActiveException err){
                android.util.Log.w("MaritimePush","System activation",err);manualSelection();
            }
        });
    }
    @Override public void onRequestPermissionsResult(int req,String[] permissions,int[] results) {
        super.onRequestPermissionsResult(req,permissions,results);
        if(req==1 && results.length>0 && results[0]==PackageManager.PERMISSION_GRANTED)activate();
        else manualSelection();
    }
}
