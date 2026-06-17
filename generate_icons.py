"""Run once to generate the PWA PNG icons (price-tag glyph on green background)."""
from PIL import Image, ImageDraw

GREEN = (27, 94, 32)
ORANGE = (255, 111, 0)
WHITE = (255, 255, 255)


def draw_tag(size):
    img = Image.new('RGB', (size, size), GREEN)
    draw = ImageDraw.Draw(img)
    s = size / 512

    # Price tag shape: a pentagon-ish tag pointing right, with a hole near the tip.
    points = [
        (96 * s, 120 * s),
        (300 * s, 120 * s),
        (416 * s, 256 * s),
        (300 * s, 392 * s),
        (96 * s, 392 * s),
    ]
    draw.polygon(points, fill=ORANGE)

    # Punch hole near the tip.
    hole_r = 22 * s
    hole_cx, hole_cy = 330 * s, 256 * s
    draw.ellipse(
        [hole_cx - hole_r, hole_cy - hole_r, hole_cx + hole_r, hole_cy + hole_r],
        fill=GREEN,
    )

    # Small string loop on the left edge.
    draw.ellipse([72 * s, 232 * s, 112 * s, 280 * s], outline=WHITE, width=int(10 * s))

    return img


for size in (192, 512):
    draw_tag(size).save(f'static/icon-{size}.png')
    print(f'Generated static/icon-{size}.png')
