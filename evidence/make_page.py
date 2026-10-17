"""Build a self-contained results page: the <head> (styles) of stage2.template.html + a body file, images embedded.

  python evidence/make_page.py <body.html> <title> <output.html> [image.png ...]
Images are referenced in the body by file name (src="loss.png") and embedded as data URIs, so the page opens anywhere.
"""
import base64
import os
import sys

here = os.path.dirname(os.path.abspath(__file__))
body_file, title, out, *images = sys.argv[1:]
src = open(os.path.join(here, "stage2.template.html"), encoding="utf-8").read()
head = src[: src.index("<body>")]
head = head[: head.index("<title>")] + f"<title>{title}</title>" + head[head.index("</title>") + 8:]
html = head + open(body_file, encoding="utf-8").read()
for img in images:
    data = base64.b64encode(open(img, "rb").read()).decode()
    html = html.replace(f'src="{os.path.basename(img)}"', f'src="data:image/png;base64,{data}"')
open(out, "w", encoding="utf-8").write(html)
print(f"wrote {out} ({len(html) // 1024} KB)")
