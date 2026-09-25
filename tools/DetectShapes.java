/* DetectShapes - recover node geometry from the original PNG.
 *
 *   java DetectShapes <original.png> [modelWidth]
 *
 * Line-art diagrams enclose every node in a stroked outline, so each node interior is a
 * white region that is NOT reachable from the image border. Flood the background, label
 * what white is left, and each sizeable component is a node interior. The ratio of the
 * component's area to its bounding box tells us the shape:
 *   ~1.00 rectangle   ~0.93 rounded rectangle   ~0.50 diamond   ~0.79 circle
 *
 * Prints measured pixel geometry and the same in model units, so the drawing can be
 * built from measurements instead of from eyeballing.
 */
import javax.imageio.ImageIO;
import java.awt.*;
import java.awt.image.BufferedImage;
import java.io.File;
import java.util.*;

public class DetectShapes {

    public static void main(String[] args) throws Exception {
        BufferedImage src = ImageIO.read(new File(args[0]));
        int W = src.getWidth(), H = src.getHeight();
        double modelW = args.length > 1 ? Double.parseDouble(args[1]) : 1480.0;
        double s = modelW / W;

        BufferedImage flat = new BufferedImage(W, H, BufferedImage.TYPE_INT_RGB);
        Graphics2D g = flat.createGraphics();
        g.setColor(Color.WHITE); g.fillRect(0, 0, W, H);
        g.drawImage(src, 0, 0, Color.WHITE, null); g.dispose();

        boolean[] ink = new boolean[W * H];
        for (int y = 0; y < H; y++)
            for (int x = 0; x < W; x++) {
                int c = flat.getRGB(x, y);
                int l = (((c >> 16) & 255) * 299 + ((c >> 8) & 255) * 587 + (c & 255) * 114) / 1000;
                ink[y * W + x] = l < 128;
            }

        // 1. flood the background (white reachable from the border)
        boolean[] bg = new boolean[W * H];
        ArrayDeque<Integer> q = new ArrayDeque<>();
        for (int x = 0; x < W; x++) { push(q, bg, ink, x, 0, W, H); push(q, bg, ink, x, H - 1, W, H); }
        for (int y = 0; y < H; y++) { push(q, bg, ink, 0, y, W, H); push(q, bg, ink, W - 1, y, W, H); }
        while (!q.isEmpty()) {
            int p = q.poll(), x = p % W, y = p / W;
            if (x > 0) push(q, bg, ink, x - 1, y, W, H);
            if (x < W - 1) push(q, bg, ink, x + 1, y, W, H);
            if (y > 0) push(q, bg, ink, x, y - 1, W, H);
            if (y < H - 1) push(q, bg, ink, x, y + 1, W, H);
        }

        // 2. label the enclosed white regions
        boolean[] seen = new boolean[W * H];
        java.util.List<int[]> shapes = new ArrayList<>();
        for (int y0 = 0; y0 < H; y0++)
            for (int x0 = 0; x0 < W; x0++) {
                int i0 = y0 * W + x0;
                if (ink[i0] || bg[i0] || seen[i0]) continue;
                int minx = x0, maxx = x0, miny = y0, maxy = y0, area = 0;
                ArrayDeque<Integer> r = new ArrayDeque<>();
                r.add(i0); seen[i0] = true;
                while (!r.isEmpty()) {
                    int p = r.poll(), x = p % W, y = p / W;
                    area++;
                    if (x < minx) minx = x; if (x > maxx) maxx = x;
                    if (y < miny) miny = y; if (y > maxy) maxy = y;
                    int[][] nb = {{x - 1, y}, {x + 1, y}, {x, y - 1}, {x, y + 1}};
                    for (int[] n : nb) {
                        int nx = n[0], ny = n[1];
                        if (nx < 0 || ny < 0 || nx >= W || ny >= H) continue;
                        int j = ny * W + nx;
                        if (!ink[j] && !bg[j] && !seen[j]) { seen[j] = true; r.add(j); }
                    }
                }
                if (area >= 1500) shapes.add(new int[]{minx, miny, maxx - minx + 1, maxy - miny + 1, area});
            }

        shapes.sort((p, r) -> p[1] != r[1] ? Integer.compare(p[1], r[1]) : Integer.compare(p[0], r[0]));
        System.out.printf("%-4s %26s %10s %26s   %s%n", "#", "pixel x,y,w,h", "fill", "model x,y,w,h", "shape");
        int i = 1;
        for (int[] c : shapes) {
            double fill = c[4] / (double) (c[2] * c[3]);
            String kind = fill > 0.97 ? "rectangle"
                    : fill > 0.86 ? "rounded-rect"
                    : fill > 0.70 ? "circle/ellipse"
                    : fill > 0.40 ? "diamond" : "other";
            System.out.printf("%-4d %6d %6d %6d %6d %9.2f %6.0f %6.0f %6.0f %6.0f   %s%n",
                    i++, c[0], c[1], c[2], c[3], fill,
                    c[0] * s, c[1] * s, c[2] * s, c[3] * s, kind);
        }
        System.out.printf("%ndetected %d shapes; scale %.5f (model width %.0f from %d px)%n",
                shapes.size(), s, modelW, W);
    }

    static void push(ArrayDeque<Integer> q, boolean[] bg, boolean[] ink, int x, int y, int W, int H) {
        int i = y * W + x;
        if (!ink[i] && !bg[i]) { bg[i] = true; q.add(i); }
    }
}
