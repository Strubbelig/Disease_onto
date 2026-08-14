from pathlib import Path

from PIL import Image, ImageDraw


source = Path(".codex_tmp/compact_flow_render1")
pages = sorted(source.glob("page-*.png"), key=lambda p: int(p.stem.split("-")[1]))
thumb_width = 620
gap = 28
label_height = 34

for sheet_no, start in enumerate(range(0, len(pages), 4), 1):
    group = pages[start : start + 4]
    opened = [Image.open(path).convert("RGB") for path in group]
    ratio = thumb_width / opened[0].width
    thumb_height = round(opened[0].height * ratio)
    canvas = Image.new(
        "RGB",
        (thumb_width * 2 + gap * 3, (thumb_height + label_height) * 2 + gap * 3),
        "#b8b8b8",
    )
    draw = ImageDraw.Draw(canvas)
    for index, (path, page) in enumerate(zip(group, opened)):
        x = gap + (index % 2) * (thumb_width + gap)
        y = gap + (index // 2) * (thumb_height + label_height + gap)
        canvas.paste(page.resize((thumb_width, thumb_height)), (x, y + label_height))
        draw.text((x, y + 6), path.stem.replace("-", " ").title(), fill="black")
    canvas.save(source / f"contact-{sheet_no}.png")
