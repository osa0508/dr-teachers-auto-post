"""
家庭教師ライフカラー（@dr._teachers）アイキャッチ画像ジェネレーター

使い方:
    from generate_eyecatch import make_image
    make_image(kicker="家庭教師ライフカラー コラム", title="記事タイトル", footer="@dr._teachers｜岐阜の家庭教師", out_path="out.jpg")

Instagram推奨サイズ（正方形 1080x1080）で書き出す。
"""
from PIL import Image, ImageDraw, ImageFont
import textwrap

W, H = 1080, 1080
FONT_BOLD = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
FONT_MED = "/usr/share/fonts/opentype/noto/NotoSansCJK-Medium.ttc"
FONT_REG = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

# ブランドカラー（濃紺 + 黄色アクセント）。変更したい場合はここを直す。
BRAND_BG_TOP = (30, 58, 95)
BRAND_BG_BOTTOM = (15, 33, 58)
BRAND_ACCENT = (255, 196, 61)


def _wrap_title(title: str, width: int = 13):
    """日本語タイトルを大まかに折り返す（厳密な文字幅計算はしていない簡易版）"""
    return textwrap.wrap(title, width=width)


def make_image(
    title: str,
    out_path: str,
    kicker: str = "家庭教師ライフカラー コラム",
    footer: str = "@dr._teachers｜岐阜の家庭教師",
    bg_top=BRAND_BG_TOP,
    bg_bottom=BRAND_BG_BOTTOM,
    accent=BRAND_ACCENT,
):
    img = Image.new("RGB", (W, H), bg_top)
    draw = ImageDraw.Draw(img)

    for y in range(H):
        t = y / H
        r = int(bg_top[0] + (bg_bottom[0] - bg_top[0]) * t)
        g = int(bg_top[1] + (bg_bottom[1] - bg_top[1]) * t)
        b = int(bg_top[2] + (bg_bottom[2] - bg_top[2]) * t)
        draw.line([(0, y), (W, y)], fill=(r, g, b))

    draw.rectangle([(80, 120), (80 + 90, 120 + 10)], fill=accent)

    kicker_font = ImageFont.truetype(FONT_MED, 34)
    draw.text((80, 150), kicker, font=kicker_font, fill=accent)

    title_font = ImageFont.truetype(FONT_BOLD, 76)
    wrapped = _wrap_title(title)
    y = 240
    for line in wrapped:
        draw.text((80, y), line, font=title_font, fill=(255, 255, 255))
        bbox = draw.textbbox((0, 0), line, font=title_font)
        y += (bbox[3] - bbox[1]) + 28

    footer_font = ImageFont.truetype(FONT_MED, 32)
    draw.text((80, H - 130), footer, font=footer_font, fill=(210, 220, 230))
    draw.line([(80, H - 160), (W - 80, H - 160)], fill=(70, 90, 115), width=2)

    img.save(out_path, "JPEG", quality=92)
    return out_path


if __name__ == "__main__":
    make_image(
        title="SNSの視聴時間と学力・人間関係",
        out_path="eyecatch_sample.jpg",
    )
    print("done")
