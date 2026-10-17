"""Build docs/progress.html from progress.template.html with the drawings embedded, so the file works anywhere."""
import base64, os, re
here = os.path.dirname(os.path.abspath(__file__))
html = open(os.path.join(here, "progress.template.html"), encoding="utf-8").read()
def embed(m):
    data = base64.b64encode(open(os.path.join(here, m.group(1)), "rb").read()).decode()
    return f'src="data:image/png;base64,{data}"'
html = re.sub(r'src="([\w-]+\.png)"', embed, html)
open(os.path.join(here, "progress.html"), "w", encoding="utf-8").write(html)
print("wrote progress.html", len(html) // 1024, "KB")
