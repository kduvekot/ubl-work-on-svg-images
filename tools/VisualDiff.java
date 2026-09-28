/* VisualDiff - pixel-level validation of candidate artwork against the original PNG.
 *
 *   java VisualDiff <original.png> <candidate.png> <diff-out.png> [radius] [--ghost]
 *
 * The original PNG is the source of truth. Both images are composited onto white and
 * reduced to ink / no-ink. A candidate pixel counts as matching if the original has
 * ink within `radius` pixels (and vice versa), which absorbs anti-aliasing and
 * sub-pixel placement without hiding real differences.
 *
 *   white  = agrees
 *   RED    = ink in the ORIGINAL that the candidate is missing
 *   BLUE   = ink in the CANDIDATE that the original does not have
 *
 * A clean run writes an all-white image and exits 0. Any colour exits 1.
 */
import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferInt;
import java.io.File;

public class VisualDiff {

    static boolean[] ink(BufferedImage src, int W, int H) {
        BufferedImage n = new BufferedImage(W, H, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = n.createGraphics();
        g.setColor(Color.WHITE);
        g.fillRect(0, 0, W, H);
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
        g.drawImage(src, 0, 0, W, H, Color.WHITE, null);   // composites any alpha onto white
        g.dispose();
        return binarize(n, W, H);
    }

    /** `n` is always a TYPE_INT_RGB image made here, so its pixels are read from
     *  the raster's own int array: the same values getRGB returns, without a method
     *  call and a colour-model lookup per pixel, which was most of this tool's time */
    static boolean[] binarize(BufferedImage n, int W, int H) {
        int[] px = ((DataBufferInt) n.getRaster().getDataBuffer()).getData();
        boolean[] b = new boolean[W * H];
        for (int i = 0; i < W * H; i++) {
            int rgb = px[i];
            int lum = (((rgb >> 16) & 255) * 299 + ((rgb >> 8) & 255) * 587 + (rgb & 255) * 114) / 1000;
            b[i] = lum < 128;
        }
        return b;
    }

    /** x0,y0,x1,y1 of the inked area (exclusive upper bound) */
    static int[] bbox(boolean[] b, int W, int H) {
        int x0 = W, y0 = H, x1 = 0, y1 = 0;
        for (int y = 0; y < H; y++)
            for (int x = 0; x < W; x++)
                if (b[y * W + x]) {
                    if (x < x0) x0 = x; if (x >= x1) x1 = x + 1;
                    if (y < y0) y0 = y; if (y >= y1) y1 = y + 1;
                }
        return new int[]{x0, y0, x1, y1};
    }

    /** Draw B onto an A-sized canvas so that B's ink bounding box lands exactly on A's.
     *  Removes global translation / scale / aspect drift, which would otherwise swamp
     *  the diff when the candidate was drawn independently rather than re-rendered. */
    static boolean[] inkAligned(BufferedImage B, int[] bb, int[] ba, int W, int H, double[] reportScale) {
        double sx = (ba[2] - ba[0]) / (double) (bb[2] - bb[0]);
        double sy = (ba[3] - ba[1]) / (double) (bb[3] - bb[1]);
        reportScale[0] = sx; reportScale[1] = sy;
        BufferedImage n = new BufferedImage(W, H, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = n.createGraphics();
        g.setColor(Color.WHITE);
        g.fillRect(0, 0, W, H);
        g.setRenderingHint(RenderingHints.KEY_INTERPOLATION, RenderingHints.VALUE_INTERPOLATION_BILINEAR);
        g.translate(ba[0], ba[1]);
        g.scale(sx, sy);
        g.translate(-bb[0], -bb[1]);
        g.drawImage(B, 0, 0, Color.WHITE, null);
        g.dispose();
        return binarize(n, W, H);
    }

    /** OR-pool down by factor f (a cell is inked if any pixel in it is) */
    static boolean[] pool(boolean[] b, int W, int H, int f) {
        int w = W / f, h = H / f;
        boolean[] o = new boolean[w * h];
        for (int y = 0; y < H; y++) {
            int cy = y / f; if (cy >= h) continue;
            for (int x = 0; x < W; x++) {
                int cx = x / f; if (cx >= w) continue;
                if (b[y * W + x]) o[cy * w + cx] = true;
            }
        }
        return o;
    }

    /** count of pixels where A and B-shifted-by-(dx,dy) are both inked */
    static long overlap(boolean[] A, boolean[] B, int W, int H, int dx, int dy) {
        long n = 0;
        for (int y = Math.max(0, -dy); y < Math.min(H, H - dy); y++)
            for (int x = Math.max(0, -dx); x < Math.min(W, W - dx); x++)
                if (A[y * W + x] && B[(y + dy) * W + x + dx]) n++;
        return n;
    }

    static boolean[] translate(boolean[] b, int W, int H, int dx, int dy) {
        boolean[] o = new boolean[W * H];
        for (int y = 0; y < H; y++) {
            int sy = y - dy; if (sy < 0 || sy >= H) continue;
            for (int x = 0; x < W; x++) {
                int sx = x - dx; if (sx < 0 || sx >= W) continue;
                o[y * W + x] = b[sy * W + sx];
            }
        }
        return o;
    }

    /** summed-area table so a radius-r neighbourhood test is O(1) per pixel */
    static int[] sat(boolean[] b, int W, int H) {
        int[] s = new int[(W + 1) * (H + 1)];
        for (int y = 0; y < H; y++)
            for (int x = 0; x < W; x++)
                s[(y + 1) * (W + 1) + x + 1] = (b[y * W + x] ? 1 : 0)
                        + s[y * (W + 1) + x + 1] + s[(y + 1) * (W + 1) + x] - s[y * (W + 1) + x];
        return s;
    }

    static boolean near(int[] s, int W, int H, int x, int y, int r) {
        int x0 = Math.max(0, x - r), y0 = Math.max(0, y - r);
        int x1 = Math.min(W, x + r + 1), y1 = Math.min(H, y + r + 1);
        int v = s[y1 * (W + 1) + x1] - s[y0 * (W + 1) + x1] - s[y1 * (W + 1) + x0] + s[y0 * (W + 1) + x0];
        return v > 0;
    }

    public static void main(String[] a) throws Exception {
        if (a.length < 3) { System.err.println("usage: VisualDiff orig.png cand.png out.png [radius] [--ghost]"); System.exit(2); }
        int radius = 2;
        boolean ghost = false, align = true;
        for (int i = 3; i < a.length; i++) {
            if (a[i].equals("--ghost")) ghost = true;
            else if (a[i].equals("--no-align")) align = false;
            else if (a[i].startsWith("--")) { /* handled below */ }
            else radius = Integer.parseInt(a[i]);
        }
        BufferedImage A = ImageIO.read(new File(a[0]));
        BufferedImage B = ImageIO.read(new File(a[1]));
        int W = A.getWidth(), H = A.getHeight();

        int coarse = 0, local = 0, localSearch = 48;
        boolean shift = false;
        for (int i = 3; i < a.length; i++) {
            if (a[i].startsWith("--coarse=")) coarse = Integer.parseInt(a[i].substring(9));
            if (a[i].equals("--shift")) shift = true;
            if (a[i].startsWith("--local=")) local = Integer.parseInt(a[i].substring(8));
        }

        boolean[] ia = ink(A, W, H), ib;
        if (align) {
            boolean[] ibRaw = ink(B, B.getWidth(), B.getHeight());
            int[] ba = bbox(ia, W, H), bb = bbox(ibRaw, B.getWidth(), B.getHeight());
            double[] sc = new double[2];
            ib = inkAligned(B, bb, ba, W, H, sc);
            System.out.printf("  aligned on ink bounds: scale x %.4f, y %.4f%s%n", sc[0], sc[1],
                    Math.abs(sc[0] - sc[1]) / sc[0] > 0.02 ? "   <-- aspect differs by >2%" : "");
        } else {
            ib = ink(B, W, H);
        }
        // Optional rigid-translation search: find the (dx,dy) that maximises ink overlap.
        // Tells you how much of a difference is a plain shift rather than real divergence.
        if (shift) {
            int f = 4;                                   // search on a 1/4-scale copy first
            int w4 = W / f, h4 = H / f;
            boolean[] a4 = pool(ia, W, H, f), b4 = pool(ib, W, H, f);
            int bestX = 0, bestY = 0; long best = -1;
            for (int dy = -24; dy <= 24; dy++)
                for (int dx = -24; dx <= 24; dx++) {
                    long ov = overlap(a4, b4, w4, h4, dx, dy);
                    if (ov > best) { best = ov; bestX = dx; bestY = dy; }
                }
            int cx = bestX * f, cy = bestY * f;
            int fx = cx, fy = cy; long fbest = -1;
            for (int dy = cy - f; dy <= cy + f; dy++)
                for (int dx = cx - f; dx <= cx + f; dx++) {
                    long ov = overlap(ib, ia, W, H, -dx, -dy);   // note: measure on full res
                    if (ov > fbest) { fbest = ov; fx = dx; fy = dy; }
                }
            System.out.printf("  best rigid shift: dx %+d px, dy %+d px%n", fx, fy);
            ib = translate(ib, W, H, fx, fy);
        }

        // Local (elastic) alignment: shift each tile independently onto its best match.
        // A hand-redrawn diagram has per-element placement error that no single shift can
        // remove, so this absorbs "drawn a bit lower" while still exposing content that has
        // no counterpart at all. Reports the spread of shifts it had to apply.
        if (local > 1) {
            int R = localSearch;
            boolean[] nb = new boolean[W * H];
            int tilesX = (W + local - 1) / local, tilesY = (H + local - 1) / local;
            int maxAbs = 0; long used = 0, tiles = 0;
            for (int ty = 0; ty < tilesY; ty++)
                for (int tx = 0; tx < tilesX; tx++) {
                    int x0 = tx * local, y0 = ty * local;
                    int x1 = Math.min(W, x0 + local), y1 = Math.min(H, y0 + local);
                    long tot = 0;
                    for (int y = y0; y < y1; y++) for (int x = x0; x < x1; x++) if (ia[y * W + x]) tot++;
                    int bx = 0, by = 0;
                    if (tot > 0) {
                        long best = -1;
                        for (int dy = -R; dy <= R; dy += 2)
                            for (int dx = -R; dx <= R; dx += 2) {
                                long ov = 0;
                                for (int y = y0; y < y1; y++) {
                                    int sy = y + dy; if (sy < 0 || sy >= H) continue;
                                    for (int x = x0; x < x1; x++) {
                                        int sx = x + dx; if (sx < 0 || sx >= W) continue;
                                        if (ia[y * W + x] && ib[sy * W + sx]) ov++;
                                    }
                                }
                                if (ov > best) { best = ov; bx = dx; by = dy; }
                            }
                        maxAbs = Math.max(maxAbs, Math.max(Math.abs(bx), Math.abs(by)));
                        used += Math.abs(bx) + Math.abs(by); tiles++;
                    }
                    for (int y = y0; y < y1; y++) {
                        int sy = y + by; if (sy < 0 || sy >= H) continue;
                        for (int x = x0; x < x1; x++) {
                            int sx = x + bx; if (sx < 0 || sx >= W) continue;
                            nb[y * W + x] = ib[sy * W + sx];
                        }
                    }
                }
            ib = nb;
            System.out.printf("  local align: %dpx tiles, search +-%dpx, max shift %dpx, mean |shift| %.1fpx%n",
                    local, R, maxAbs, tiles == 0 ? 0 : (double) used / tiles / 2);
        }

        // Coarse mode: compare ink OCCUPANCY on an NxN grid instead of pixel for pixel.
        // Independently redrawn artwork never matches glyph for glyph, but a missing box,
        // a dropped arrow or a moved lane still shows up as an empty/occupied cell.
        if (coarse > 1) {
            int cw = (W + coarse - 1) / coarse, ch = (H + coarse - 1) / coarse;
            int[] ca = new int[cw * ch], cb = new int[cw * ch];
            for (int y = 0; y < H; y++)
                for (int x = 0; x < W; x++) {
                    int c = (y / coarse) * cw + x / coarse;
                    if (ia[y * W + x]) ca[c]++;
                    if (ib[y * W + x]) cb[c]++;
                }
            int need = Math.max(1, (int) (coarse * coarse * 0.06));   // >=6% coverage = occupied
            boolean[] na = new boolean[W * H], nb = new boolean[W * H];
            for (int y = 0; y < H; y++)
                for (int x = 0; x < W; x++) {
                    int c = (y / coarse) * cw + x / coarse;
                    na[y * W + x] = ca[c] >= need;
                    nb[y * W + x] = cb[c] >= need;
                }
            ia = na; ib = nb;
            System.out.printf("  coarse mode: %dx%d cells of %dpx, occupied at >=%d ink px%n", cw, ch, coarse, need);
        }

        int[] sa = sat(ia, W, H), sb = sat(ib, W, H);

        BufferedImage out = new BufferedImage(W, H, BufferedImage.TYPE_INT_RGB);
        int[] outPx = ((DataBufferInt) out.getRaster().getDataBuffer()).getData();
        int inkA = 0, inkB = 0, missing = 0, extra = 0;
        for (int y = 0; y < H; y++)
            for (int x = 0; x < W; x++) {
                boolean pa = ia[y * W + x], pb = ib[y * W + x];
                if (pa) inkA++;
                if (pb) inkB++;
                int rgb = 0xFFFFFF;
                if (pa && !near(sb, W, H, x, y, radius))      { rgb = 0xD40000; missing++; }
                else if (pb && !near(sa, W, H, x, y, radius)) { rgb = 0x0060D0; extra++; }
                else if (ghost && (pa || pb))                  rgb = 0xEDEDED;
                outPx[y * W + x] = rgb;          // the raster itself, as setRGB would
            }
        ImageIO.write(out, "png", new File(a[2]));

        int diff = missing + extra;
        System.out.printf("  size %dx%d  radius %d%n", W, H, radius);
        System.out.printf("  ink: original %d   candidate %d%n", inkA, inkB);
        System.out.printf("  MISSING (red)  %7d  = %.4f%% of original ink%n", missing, 100.0 * missing / Math.max(1, inkA));
        System.out.printf("  EXTRA   (blue) %7d  = %.4f%% of original ink%n", extra, 100.0 * extra / Math.max(1, inkA));
        System.out.println(diff == 0 ? "  RESULT: CLEAN - diff image is blank" : "  RESULT: DIFFERENCES - inspect " + a[2]);
        System.exit(diff == 0 ? 0 : 1);
    }
}
