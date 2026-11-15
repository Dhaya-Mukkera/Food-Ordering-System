"""Generates illustrated food images (SVG) into static/images/foods/.
Run:  python tools/generate_images.py
Replace any file with your own photo (same name, or upload through the admin panel)."""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "static" / "images" / "foods"
OUT.mkdir(parents=True, exist_ok=True)


def wrap(c1, c2, body):
    return ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">'
            f'<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c1}"/>'
            f'<stop offset="1" stop-color="{c2}"/></linearGradient>'
            '<radialGradient id="sh"><stop offset="0" stop-color="#000" stop-opacity=".3"/>'
            '<stop offset="1" stop-color="#000" stop-opacity="0"/></radialGradient></defs>'
            '<rect width="400" height="300" fill="url(#g)"/>'
            '<circle cx="50" cy="40" r="95" fill="#fff" opacity=".10"/>'
            '<circle cx="370" cy="275" r="120" fill="#fff" opacity=".10"/>'
            f'{body}</svg>')


def plate():
    return ('<ellipse cx="200" cy="268" rx="125" ry="16" fill="url(#sh)"/>'
            '<circle cx="200" cy="165" r="114" fill="#fff"/><circle cx="200" cy="165" r="94" fill="#eef0f3"/>'
            '<circle cx="200" cy="165" r="88" fill="#fff"/>')


def dots(pts, color, r=4):
    return "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>' for x, y in pts)


def curry(a, b, g="#2f9e44"):
    return (plate() + f'<path d="M118 150h164a82 72 0 0 1-164 0z" fill="{a}"/>'
            f'<ellipse cx="200" cy="150" rx="82" ry="16" fill="{b}"/>'
            '<path d="M150 150q25-12 50 0t50 0" stroke="#fff" stroke-opacity=".7" stroke-width="6" fill="none"/>'
            + dots([(165, 146), (200, 152), (235, 146), (185, 140)], g, 5))


def rice(a, b, egg=True):
    s = plate() + '<path d="M104 205q6-95 96-102q90 7 96 102z" fill="#f6e7b4"/>'
    s += '<path d="M104 205q6-95 96-102q90 7 96 102z" fill="none" stroke="#e0c878" stroke-width="3"/>'
    pts = [(150, 170), (180, 150), (215, 165), (245, 185), (165, 195), (205, 190), (190, 125), (225, 140), (140, 190), (260, 200)]
    s += dots(pts[::2], a, 7) + dots(pts[1::2], b, 6)
    if egg:
        s += '<ellipse cx="252" cy="210" rx="26" ry="18" fill="#fff"/><ellipse cx="252" cy="210" rx="11" ry="9" fill="#ffc53d"/>'
    s += '<path d="M120 215q40 20 80 0t80 0" stroke="#2f9e44" stroke-width="7" fill="none" stroke-linecap="round"/>'
    return s


def skewer(a, b):
    cubes = "".join(f'<rect x="{110 + i * 42}" y="{148 - i * 6}" width="40" height="40" rx="9" fill="{a if i % 2 == 0 else b}" transform="rotate(-8 {130 + i * 42} 170)"/>' for i in range(5))
    return (plate() + '<line x1="95" y1="190" x2="320" y2="140" stroke="#a9742e" stroke-width="5" stroke-linecap="round"/>'
            + cubes + '<circle cx="300" cy="220" r="22" fill="#74c69d"/><circle cx="300" cy="220" r="14" fill="#52b788"/>')


def rolls(a, b):
    s = plate()
    for x, y, r in [(135, 150, -20), (190, 175, 8), (245, 150, 25)]:
        s += (f'<g transform="rotate({r} {x} {y})"><rect x="{x - 50}" y="{y - 20}" width="100" height="40" rx="20" fill="{a}"/>'
              f'<rect x="{x - 50}" y="{y - 20}" width="100" height="14" rx="7" fill="{b}" opacity=".55"/>'
              f'<ellipse cx="{x + 50}" cy="{y}" rx="9" ry="20" fill="#f3c969"/></g>')
    return s + '<circle cx="200" cy="228" r="20" fill="#d62828"/><circle cx="200" cy="228" r="13" fill="#f77f00"/>'


def bites(a, b):
    pts = [(150, 150), (190, 135), (230, 150), (170, 180), (210, 178), (250, 185), (135, 190), (195, 210), (235, 215)]
    s = plate()
    for x, y in pts:
        s += f'<circle cx="{x}" cy="{y}" r="22" fill="{a}"/><circle cx="{x - 6}" cy="{y - 6}" r="7" fill="{b}" opacity=".7"/>'
    return s + dots([(160, 128), (255, 160), (125, 165)], "#2f9e44", 6) + '<circle cx="270" cy="120" r="12" fill="#e63946"/>'


def burger():
    return ('<ellipse cx="200" cy="262" rx="110" ry="14" fill="url(#sh)"/>'
            '<path d="M95 215h210a10 10 0 0 1 0 22q-105 20-210 0a10 10 0 0 1 0-22z" fill="#e9a23b"/>'
            '<rect x="90" y="192" width="220" height="26" rx="13" fill="#5b2c1a"/>'
            '<path d="M92 192h216l-10 14-18-12-18 14-18-14-18 14-18-14-18 14-18-14-18 14-18-14-18 14-10-12z" fill="#ffc53d"/>'
            '<path d="M88 182q20 12 40 0t40 0 40 0 40 0 40 0 24 0v14H88z" fill="#74c69d"/>'
            '<path d="M95 182q-5-95 105-95t105 95z" fill="#f0a63c"/>'
            '<path d="M120 130q40-35 100-33" stroke="#fff" stroke-opacity=".35" stroke-width="8" fill="none" stroke-linecap="round"/>'
            + "".join(f'<ellipse cx="{x}" cy="{y}" rx="7" ry="3.5" fill="#fff3d6" transform="rotate({r} {x} {y})"/>' for x, y, r in [(160, 120, -25), (200, 108, 5), (240, 120, 30), (180, 145, -10), (225, 148, 15)]))


def pizza():
    return ('<ellipse cx="200" cy="265" rx="120" ry="14" fill="url(#sh)"/>'
            '<path d="M200 252L88 90q112-60 224 0z" fill="#f4c27a"/>'
            '<path d="M200 238L105 98q95-48 190 0z" fill="#ffd166"/>'
            '<path d="M88 90q112-60 224 0" stroke="#d9993f" stroke-width="12" fill="none" stroke-linecap="round"/>'
            + dots([(160, 120), (240, 120), (200, 160), (180, 195)], "#c1121f", 14)
            + dots([(200, 125), (225, 150), (175, 150)], "#2f9e44", 6))


def fries():
    sticks = "".join(f'<rect x="{128 + i * 19}" y="{70 + (i % 3) * 10}" width="14" height="{110 - (i % 3) * 10}" rx="5" fill="#ffc53d" transform="rotate({(i - 4) * 4} {135 + i * 19} 170)"/>' for i in range(8))
    return ('<ellipse cx="200" cy="268" rx="100" ry="13" fill="url(#sh)"/>' + sticks +
            '<path d="M118 165h164l-14 100H132z" fill="#d62828"/><path d="M122 190h156l-3 22H125z" fill="#fff" opacity=".9"/>'
            '<path d="M118 165h164" stroke="#a4161a" stroke-width="6"/>')


def jamun(a):
    s = plate() + '<path d="M115 160h170a85 62 0 0 1-170 0z" fill="#fff"/><path d="M120 165h160a80 54 0 0 1-160 0z" fill="#f4a261"/>'
    for x, y in [(165, 160), (205, 150), (245, 162), (185, 185), (225, 182)]:
        s += f'<circle cx="{x}" cy="{y}" r="23" fill="{a}"/><circle cx="{x - 7}" cy="{y - 8}" r="7" fill="#fff" opacity=".3"/>'
    return s + dots([(190, 128), (215, 132)], "#d62828", 5)


def cake():
    return (plate() + '<rect x="120" y="130" width="160" height="80" rx="12" fill="#4a2511"/>'
            '<rect x="120" y="130" width="160" height="22" rx="11" fill="#6b3a1d"/>'
            '<path d="M120 150q15 24 30 0t30 0 30 0 30 0 30 0v-16H120z" fill="#2b140a"/>'
            '<rect x="120" y="170" width="160" height="8" fill="#e8c9a0"/>'
            '<circle cx="200" cy="120" r="14" fill="#c1121f"/><path d="M200 108q4-18 18-22" stroke="#2f9e44" stroke-width="4" fill="none"/>'
            + dots([(150, 195), (190, 200), (240, 192)], "#8d5a35", 5))


def sundae():
    return ('<ellipse cx="200" cy="268" rx="90" ry="12" fill="url(#sh)"/>'
            '<rect x="192" y="195" width="16" height="55" fill="#e5e7eb"/><ellipse cx="200" cy="252" rx="48" ry="10" fill="#e5e7eb"/>'
            '<path d="M110 120h180q-4 70-90 80-86-10-90-80z" fill="#ffffff" opacity=".85"/>'
            '<path d="M120 132h160q-4 50-80 60-76-10-80-60z" fill="#f8c8dc"/>'
            '<circle cx="165" cy="108" r="36" fill="#fff3c4"/><circle cx="235" cy="108" r="36" fill="#ff8fab"/><circle cx="200" cy="85" r="36" fill="#6f4e37"/>'
            '<path d="M170 100q30 20 60 0" stroke="#3b1f0f" stroke-width="9" fill="none" stroke-linecap="round"/>'
            '<circle cx="200" cy="45" r="12" fill="#c1121f"/>')


def glass(a, b, garnish="#2f9e44"):
    return ('<ellipse cx="200" cy="268" rx="75" ry="11" fill="url(#sh)"/>'
            '<path d="M138 70h124l-14 190h-96z" fill="#fff" opacity=".35"/>'
            f'<path d="M146 108h108l-10 148h-88z" fill="{a}"/><path d="M146 108h108l-3 36h-102z" fill="{b}" opacity=".7"/>'
            '<rect x="165" y="140" width="34" height="34" rx="7" fill="#fff" opacity=".45" transform="rotate(12 182 157)"/>'
            '<rect x="208" y="175" width="34" height="34" rx="7" fill="#fff" opacity=".35" transform="rotate(-10 225 192)"/>'
            '<line x1="215" y1="30" x2="195" y2="200" stroke="#e63946" stroke-width="7" stroke-linecap="round"/>'
            f'<circle cx="262" cy="78" r="20" fill="{garnish}"/><circle cx="262" cy="78" r="12" fill="#fff" opacity=".35"/>'
            '<path d="M138 70h124l-14 190h-96z" fill="none" stroke="#fff" stroke-width="5" opacity=".85"/>')


def cup():
    return ('<ellipse cx="200" cy="262" rx="120" ry="15" fill="url(#sh)"/>'
            '<ellipse cx="200" cy="235" rx="115" ry="26" fill="#fff"/><ellipse cx="200" cy="232" rx="95" ry="19" fill="#e5e7eb"/>'
            '<path d="M130 120h140q0 100-70 108-70-8-70-108z" fill="#fff"/>'
            '<path d="M268 140q42-4 36 32t-50 36" stroke="#fff" stroke-width="14" fill="none" stroke-linecap="round"/>'
            '<ellipse cx="200" cy="120" rx="70" ry="14" fill="#c68642"/><ellipse cx="200" cy="120" rx="56" ry="9" fill="#e0a96d"/>'
            '<path d="M175 90q-14-22 0-40t0-30M215 90q-14-22 0-40t0-30" stroke="#fff" stroke-opacity=".8" stroke-width="6" fill="none" stroke-linecap="round"/>')


ITEMS = {
    "paneer-tikka": ("#ff9f1c", "#e85d04", skewer("#ffe8b0", "#f08c00")),
    "spring-rolls": ("#ffb703", "#fb8500", rolls("#f2a93b", "#ffd166")),
    "chicken-65": ("#e63946", "#9d0208", bites("#c1440e", "#ff7b00")),
    "butter-chicken": ("#f77f00", "#d62828", curry("#e85d04", "#ff9f1c")),
    "paneer-masala": ("#fcbf49", "#f77f00", curry("#f28c28", "#ffd166", "#2f9e44")),
    "dal-tadka": ("#ffd166", "#e09f3e", curry("#e9b824", "#ffe08a", "#d62828")),
    "chicken-biryani": ("#f4a261", "#e76f51", rice("#e76f51", "#f4a261")),
    "veg-biryani": ("#80b918", "#2b9348", rice("#ff9f1c", "#2f9e44", egg=False)),
    "mutton-biryani": ("#bc6c25", "#6f1d1b", rice("#8d3b1a", "#e9c46a")),
    "cheese-burger": ("#ffbe0b", "#fb5607", burger()),
    "margherita-pizza": ("#ef476f", "#d00000", pizza()),
    "french-fries": ("#ffd60a", "#ff9e00", fries()),
    "gulab-jamun": ("#ff6b9d", "#c9184a", jamun("#6b2d1a")),
    "brownie": ("#a98467", "#6f4e37", cake()),
    "sundae": ("#f72585", "#7209b7", sundae()),
    "mango-lassi": ("#ffd60a", "#ff9e00", glass("#ffb703", "#ffe066", "#fb8500")),
    "masala-chai": ("#c68642", "#7f4f24", cup()),
    "lime-soda": ("#80ed99", "#2d6a4f", glass("#b7e4c7", "#d8f3dc", "#52b788")),
    "cold-coffee": ("#8d6e63", "#3e2723", glass("#6d4c41", "#d7b899", "#3e2723")),
    "default": ("#adb5bd", "#6c757d", plate() + '<circle cx="200" cy="165" r="40" fill="#dee2e6"/>'),
}

for slug, (c1, c2, body) in ITEMS.items():
    (OUT / f"{slug}.svg").write_text(wrap(c1, c2, body), encoding="utf-8")
print(f"Generated {len(ITEMS)} images in {OUT}")
