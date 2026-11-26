package local.artist.engine;

import java.util.Random;

/** Field order matches NTKAkitaMorphConfig. */
final class Morph {
    static final int[] FIRST = {16,8,6,2,7,6,4,8};
    private static boolean apart(int[] table, int a, int b) {
        return (table[a] & (1 << b)) != 0;
    }
    static int different(Random rng, int count, int previous) {
        int result;
        do { result = rng.nextInt(count); } while (result == previous);
        return result;
    }
    private static int accent(Random rng, int bg, int skin, int old, int other) {
        for (int n=0;; n++) {
            int c=1+rng.nextInt(18);
            if (n==20 || (c!=bg && c!=skin && c!=old && c!=other
                    && apart(Tables.BASE,c,bg) && apart(Tables.SHADOW,c,skin)
                    && (other<0 || apart(Tables.BASE,c,other)))) return c;
        }
    }
    static int[] next(Random rng, int[] old) {
        int[] c=new int[8];
        c[0]=different(rng,19,old[0]);
        for (int n=0;; n++) {
            int skin=6+rng.nextInt(8);
            if (n==20 || (skin!=c[0] && skin!=old[2] && apart(Tables.BASE,c[0],skin)
                    && apart(Tables.SHADOW,c[0],skin))) { c[2]=skin; break; }
        }
        int first=rng.nextInt(2)==0 ? 1 : 3;
        int second=4-first;
        c[first]=accent(rng,c[0],c[2],old[first],-1);
        c[second]=accent(rng,c[0],c[2],old[second],c[first]);
        int[] sizes={12,10,6,9};
        for (int i=0;i<sizes.length;i++) c[i+4]=different(rng,sizes[i],old[i+4]);
        return c;
    }
}
