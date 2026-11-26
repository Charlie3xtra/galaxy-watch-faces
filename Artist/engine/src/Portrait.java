package local.artist.engine;

import android.content.Context;
import android.graphics.*;
import java.io.*;


/** Eight transition samples and the matching inactive outline occupy a 3 by 3 atlas. */
final class Portrait {
    static final int TILE=480;
    private final float[][][] curves=new float[7][][];
    Portrait(Context context) throws IOException {
        int[] sizes={10,10,10,12,6,9,9};
        try (DataInputStream in=new DataInputStream(context.getAssets().open("curves.bin"))) {
            for(int k=0;k<sizes.length;k++) {
                curves[k]=new float[sizes[k]][];
                for(int i=0;i<sizes[k];i++) {
                    float[] c=new float[8*in.readInt()];
                    for(int j=0;j<c.length;j++) c[j]=in.readFloat();
                    curves[k][i]=c;
                }
            }
        }
    }
    private int color(int[] cfg,int layer,boolean ambient) {
        if(layer>=4) return Tables.COLOR[ambient?cfg[2]:2];
        int c=Tables.COLOR[cfg[new int[]{2,3,2,1}[layer]]];
        return layer!=0 ? c : Color.rgb(Math.round(Color.red(c)*.9f),Math.round(Color.green(c)*.9f),Math.round(Color.blue(c)*.9f));
    }
    private static int mix(int a,int b,float t) {
        return Color.rgb(Math.round(Color.red(a)+(Color.red(b)-Color.red(a))*t),
            Math.round(Color.green(a)+(Color.green(b)-Color.green(a))*t),
            Math.round(Color.blue(a)+(Color.blue(b)-Color.blue(a))*t));
    }
    private static float[] collapsed(float[] shape) {
        float[] flat=shape.clone();
        for(int i=0;i<flat.length;i++) flat[i]=shape[i%2];
        return flat;
    }
    private void frame(Canvas cv,int tile,int[] from,int[] to,float t,boolean ambient) {
        cv.save();
        cv.translate((tile%3)*TILE,(tile/3)*TILE);
        cv.clipRect(0,0,TILE,TILE);
        cv.drawColor(ambient?Color.BLACK:mix(Tables.COLOR[from[0]],Tables.COLOR[to[0]],t));
        cv.scale(TILE/450f,TILE/450f);
        Paint paint=new Paint(Paint.ANTI_ALIAS_FLAG);
        paint.setStrokeJoin(Paint.Join.ROUND);
        paint.setStrokeCap(Paint.Cap.ROUND);
        int[] indexes={5,5,5,4,6,7,7};
        for(int k=0;k<7;k++) {
            int a=from[indexes[k]], b=to[indexes[k]];
            if(k==6 && ((a==8 && b==8) || (a==8 && t==0) || (b==8 && t==1))) continue;
            float[] p=curves[k][a],q=curves[k][b];
            if((p.length==0 && q.length==0) || (p.length==0 && t==0) || (q.length==0 && t==1)) continue;
            if(p.length==0 || (k==6 && a==8)) p=collapsed(q);
            if(q.length==0 || (k==6 && b==8)) q=collapsed(p);
            if(p.length!=q.length) throw new IllegalStateException("Unmatched morph curves");
            float[] v=new float[p.length];
            for(int i=0;i<v.length;i++) {
                float n=p[i]+(q[i]-p[i])*t;
                if(k==1 && i%2==1 && n>=1.04f) n+=0.18f;
                v[i]=(i%2==0)?225f+0.86f*(34+382*n-225f):225f+0.86f*(-1+457*n-225f);
            }
            if(v.length==0) continue;
            Path path=new Path();
            path.moveTo(v[0],v[1]);
            for(int i=0;i<v.length;i+=8)
                path.cubicTo(v[i+4],v[i+5],v[i+6],v[i+7],v[i+2],v[i+3]);
            if(k<4) path.close();
            int ink=mix(color(from,k,ambient),color(to,k,ambient),t);
            paint.setStyle(Paint.Style.FILL);
            if(k<4) {
                paint.setColor(ambient?Color.BLACK:ink);
                cv.drawPath(path,paint);
            }
            if(ambient || k>=4) {
                paint.setStyle(Paint.Style.STROKE);
                paint.setStrokeWidth(k<4?2.5f:5.25f);
                paint.setColor(ink);
                cv.drawPath(path,paint);
            }
        }
        cv.restore();
    }
    byte[] atlas(int[] old,int[] current,boolean forward) {
        Bitmap image=Bitmap.createBitmap(3*TILE,3*TILE,Bitmap.Config.ARGB_8888);
        try {
            Canvas cv=new Canvas(image);
            for(int i=0;i<8;i++) frame(cv,forward?i:7-i,old,current,i/7f,false);
            frame(cv,8,current,current,1,true);
            ByteArrayOutputStream stream=new ByteArrayOutputStream();
            image.compress(Bitmap.CompressFormat.PNG,100,stream);
            return stream.toByteArray();
        } finally {image.recycle();}
    }
}



