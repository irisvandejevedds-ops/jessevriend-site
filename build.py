"""Builds the site into dist/ from the files in content/ (which the CMS at /admin edits).
    python build.py"""
import html
import json
import pathlib
import re
import shutil

ROOT = pathlib.Path(__file__).resolve().parent
DIST = ROOT / "dist"
CSS = (ROOT / "style.css").read_text()


def esc(s):
    return html.escape(str(s if s is not None else ""), quote=True)


def safe_url(u):
    u = str(u or "").strip()
    return u if re.match(r"^(https?://|mailto:|/|#)", u) else ""


def inline(text):
    """Escapes first, then allows **bold**, *italic*, `code` and [text](link)."""
    t = esc(text)
    t = re.sub(r"\[([^\]]+)\]\(([^)\s]+)\)", lambda m: f'<a href="{esc(safe_url(html.unescape(m.group(2))))}">{m.group(1)}</a>' if safe_url(html.unescape(m.group(2))) else m.group(1), t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)
    t = re.sub(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])", r"<em>\1</em>", t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return t


def markdown(text):
    """Paragraphs, '- ' lists and the inline marks above. Nothing else, and never raw HTML."""
    out, para, items = [], [], []

    def flush():
        nonlocal para, items
        if para:
            out.append("<p>" + "<br>".join(inline(x) for x in para) + "</p>")
            para = []
        if items:
            out.append("<ul>" + "".join(f"<li>{inline(x)}</li>" for x in items) + "</ul>")
            items = []

    for line in str(text or "").replace("\r", "").split("\n"):
        s = line.strip()
        if not s:
            flush()
        elif re.match(r"^[-*] ", s):
            if para:
                flush()
            items.append(s[2:])
        else:
            if items:
                flush()
            para.append(s)
    flush()
    return "\n".join(out)


def links(items, cls="links"):
    ls = [(l.get("label"), safe_url(l.get("url"))) for l in (items or []) if isinstance(l, dict) and l.get("label") and safe_url(l.get("url"))]
    return f'<div class="{cls}">' + "".join(f'<a href="{esc(u)}">{esc(t)}</a>' for t, u in ls) + "</div>" if ls else ""


def load(path, default=None):
    p = ROOT / path
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return default


def load_dir(path, key):
    items = []
    for p in sorted((ROOT / path).glob("*.json")):
        try:
            d = json.loads(p.read_text())
        except ValueError:
            continue
        if isinstance(d, dict) and d.get("title"):
            items.append(d)
    return sorted(items, key=key)


def num(d):
    try:
        return float(d.get("order", 10))
    except (TypeError, ValueError):
        return 10.0


def render():
    site = load("content/site.json", {}) or {}
    bb = load("content/bb.json", {}) or {}
    projects = load_dir("content/projects", lambda d: (num(d), d.get("title", "")))
    pagers = load_dir("content/pagers", lambda d: (num(d), d.get("title", "")))
    writing = load_dir("content/writing", lambda d: str(d.get("date", "")))[::-1]
    name = site.get("name") or "Home"

    secs, nav = [], []

    def section(id_, label, body):
        nav.append((id_, label))
        secs.append(f'<section id="{id_}"><h2>{esc(label)}</h2>\n{body}\n</section>')

    if (site.get("about") or "").strip():
        section("about", "About", f'<div class="prose">{markdown(site["about"])}</div>')

    if bb.get("title"):
        head = f'<h3><a href="{esc(safe_url(bb.get("url")))}">{esc(bb["title"])}</a></h3>' if safe_url(bb.get("url")) else f'<h3>{esc(bb["title"])}</h3>'
        card = '<div class="card">' + head + (f'<p class="meta">{esc(bb["place"])}</p>' if bb.get("place") else "") + markdown(bb.get("description"))
        card += (f'<p>{inline(bb["role"])}</p>' if (bb.get("role") or "").strip() else "") + links(bb.get("links")) + "</div>"
        events = [e for e in (bb.get("events") or []) if isinstance(e, dict) and e.get("title")]
        lst = '<ul class="plain">' + "".join(f'<li>{esc(e["title"])}' + (f' <span>&mdash; {esc(e.get("text"))}</span>' if e.get("text") else "") + "</li>" for e in events) + "</ul>" if events else ""
        section("bb", "Being and Becoming", card + lst)

    if projects:
        cards = "".join('<div class="card"><h3>' + esc(p["title"]) + "</h3>" + (f'<p>{inline(p.get("summary"))}</p>' if p.get("summary") else "") + links(p.get("links")) + "</div>" for p in projects)
        section("projects", "Apps and projects", cards)

    if writing:
        items = "".join("<li>" + (f'<a href="{esc(safe_url(w.get("url")))}">{esc(w["title"])}</a>' if safe_url(w.get("url")) else esc(w["title"])) + (f' <span>{esc(str(w.get("date"))[:10])}</span>' if w.get("date") else "")
                        + (f'<br><span>{inline(w.get("summary"))}</span>' if w.get("summary") else "") + "</li>" for w in writing)
        section("writing", "Writing", f'<ul class="plain">{items}</ul>')

    if pagers:
        cards = ""
        for p in pagers:
            target = safe_url(p.get("file") or p.get("url"))
            title = f'<a href="{esc(target)}">{esc(p["title"])}</a>' if target else esc(p["title"])
            cards += f'<div class="card"><h3>{title}</h3>' + (f'<p>{inline(p.get("blurb"))}</p>' if p.get("blurb") else "") + (f'<div class="links"><a href="{esc(target)}">Open</a></div>' if target else "") + "</div>"
        section("pagers", "One-pagers", cards)

    elsewhere = [l for l in (site.get("elsewhere") or []) if isinstance(l, dict) and l.get("label") and safe_url(l.get("url"))]
    mail = (site.get("email") or "").strip()
    if elsewhere or mail:
        rows = "".join(f'<li><a href="{esc(safe_url(l["url"]))}">{esc(l["label"])}</a></li>' for l in elsewhere)
        if mail:
            rows += f'<li><a href="mailto:{esc(mail)}">{esc(mail)}</a></li>'
        section("links", "Elsewhere", f'<ul class="plain">{rows}</ul>')

    navhtml = "".join(f'<a href="#{i}">{esc(l)}</a>' for i, l in nav)
    tagline = f'<p class="sub">{inline(site["tagline"])}</p>' if (site.get("tagline") or "").strip() else ""
    robots = "" if site.get("public") else '<meta name="robots" content="noindex">'
    desc = esc((site.get("tagline") or "").strip() or f"{name}: Being and Becoming, small apps, and writing.")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(name)}</title>
<meta name="description" content="{desc}">
{robots}
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>{esc(name)}</h1>
    {tagline}
    <nav aria-label="Sections">{navhtml}</nav>
  </header>
{chr(10).join(secs)}
  <footer>&copy; {esc(name)}</footer>
</div>
</body>
</html>
""", bool(site.get("public"))


def main():
    page, public = render()
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    (DIST / "index.html").write_text(page)
    shutil.copytree(ROOT / "admin", DIST / "admin")
    if (ROOT / "static").exists():
        shutil.copytree(ROOT / "static", DIST, dirs_exist_ok=True)
    csp = "default-src 'self'; style-src 'unsafe-inline'; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'"
    headers = "/\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n  Content-Security-Policy: " + csp + "\n"
    headers += "" if public else "  X-Robots-Tag: noindex\n"
    headers += "/admin/*\n  X-Robots-Tag: noindex\n  Cache-Control: no-store\n"
    (DIST / "_headers").write_text(headers)
    (DIST / "robots.txt").write_text("User-agent: *\nAllow: /\n" if public else "User-agent: *\nDisallow: /\n")
    print("built", DIST, "(public)" if public else "(hidden from search engines)")


if __name__ == "__main__":
    main()
