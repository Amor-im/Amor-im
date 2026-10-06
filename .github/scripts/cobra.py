#!/usr/bin/env python3
"""Gera a cobrinha das contribuições (cresce a cada quadradinho comido).

Uso: GITHUB_TOKEN=... python3 cobra.py <usuario> <pasta_saida>
Sem token, usa dados de exemplo (para testar localmente).
"""
import json, os, random, sys, urllib.request

USER = sys.argv[1] if len(sys.argv) > 1 else "Amor-im"
OUT = sys.argv[2] if len(sys.argv) > 2 else "dist"

CELL, GAP = 11, 3
P = CELL + GAP
STEP = 0.07          # segundos por casa
PAUSE = 2.5          # pausa no fim antes de reiniciar
MAX_LEN = 60         # tamanho máximo do corpo (em casas)

THEMES = {
    "dark": dict(levels=["#161B18", "#1B3A26", "#2C6B43", "#47A86A", "#6BF19C"],
                 head="#C6FF3D", body="#6BF19C", eaten="#161B18"),
    "light": dict(levels=["#EBEDF0", "#C9F5D9", "#9AE9B7", "#6BF19C", "#2FB768"],
                  head="#0F0F0F", body="#1F5C3A", eaten="#EBEDF0"),
}
LEVEL = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}


def fetch():
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        random.seed(7)
        return [[random.choice([0, 0, 0, 1, 2, 3, 4]) if random.random() < .45 else 0 for _ in range(7)] for _ in range(53)]
    q = """query($u:String!){user(login:$u){contributionsCollection{contributionCalendar{weeks{contributionDays{weekday contributionLevel}}}}}}"""
    req = urllib.request.Request("https://api.github.com/graphql",
                                 data=json.dumps({"query": q, "variables": {"u": USER}}).encode(),
                                 headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"})
    data = json.load(urllib.request.urlopen(req))
    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = []
    for w in weeks:
        col = [None] * 7
        for d in w["contributionDays"]:
            col[d["weekday"]] = LEVEL.get(d["contributionLevel"], 0)
        grid.append(col)
    return grid


def build(grid, theme):
    t = THEMES[theme]
    cols = len(grid)
    # caminho em serpentina: desce numa coluna, sobe na próxima
    order = []
    for c in range(cols):
        rows = range(7) if c % 2 == 0 else range(6, -1, -1)
        order += [(c, r) for r in rows]
    n = len(order)
    T = n * STEP + PAUSE
    W, H = cols * P + 20, 7 * P + 20
    ox = oy = 10 + CELL / 2

    def xy(c, r):
        return ox + c * P, oy + r * P

    path = "M" + " L".join(f"{xy(c, r)[0]:.1f},{xy(c, r)[1]:.1f}" for c, r in order)
    move_dur = (n - 1) * STEP

    # células e o momento em que são comidas
    cells, eat_times = [], []
    for i, (c, r) in enumerate(order):
        lv = grid[c][r]
        if lv is None:
            continue
        x, y = xy(c, r)
        col = t["levels"][lv]
        if lv > 0:
            te = i * STEP
            eat_times.append(te)
            k = te / T
            anim = (f'<animate attributeName="fill" values="{col};{col};{t["eaten"]};{t["eaten"]}" '
                    f'keyTimes="0;{k:.5f};{min(k + 0.0005, 1):.5f};1" dur="{T:.2f}s" repeatCount="indefinite"/>')
        else:
            anim = ""
        cells.append(f'<rect x="{x - CELL/2:.1f}" y="{y - CELL/2:.1f}" width="{CELL}" height="{CELL}" rx="2.5" fill="{col}">{anim}</rect>')

    # cobra: cabeça + 1 casa de corpo por quadradinho comido (até MAX_LEN).
    # Cada casa é desenhada com 2 gomos (meio passo) pra o corpo ficar contínuo.
    SUB = 2
    segs = []
    ncells = min(len(eat_times), MAX_LEN)
    nseg = ncells * SUB
    for j in range(nseg, -1, -1):           # da cauda pra cabeça
        delay = j * STEP / SUB
        head = j == 0
        size = CELL + 1 if head else 8
        color = t["head"] if head else t["body"]
        op_base = 1 if head else max(1 - j / (nseg * 1.25 + 1), .35)
        need = (j + SUB - 1) // SUB          # quantos quadradinhos precisam ter sido comidos
        born = 0 if head else eat_times[need - 1]
        end = move_dur + delay
        kb, ke = born / T, min(end / T, 0.999)
        vis = (f'<animate attributeName="opacity" values="0;0;{op_base:.2f};{op_base:.2f};0;0" '
               f'keyTimes="0;{kb:.5f};{min(kb + 0.0005, ke):.5f};{ke:.5f};{min(ke + 0.0005, 1):.5f};1" '
               f'dur="{T:.2f}s" repeatCount="indefinite"/>')
        kt_start, kt_end = delay / T, min((move_dur + delay) / T, 0.9999)
        motion = (f'<animateMotion dur="{T:.2f}s" repeatCount="indefinite" calcMode="linear" '
                  f'keyPoints="0;0;1;1" keyTimes="0;{kt_start:.5f};{kt_end:.5f};1"><mpath href="#trilha" xlink:href="#trilha"/></animateMotion>')
        rx = 3 if head else 2.5
        segs.append(f'<rect x="{-size/2:.1f}" y="{-size/2:.1f}" width="{size:.1f}" height="{size:.1f}" rx="{rx}" fill="{color}" opacity="0">{vis}{motion}</rect>')

    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">'
            + f'<path id="trilha" d="{path}" fill="none"/>' + "".join(cells) + '<g>' + "".join(segs) + '</g></svg>')


def main():
    grid = fetch()
    os.makedirs(OUT, exist_ok=True)
    for theme in THEMES:
        with open(os.path.join(OUT, f"cobra-{theme}.svg"), "w") as f:
            f.write(build(grid, theme))
    print("ok", sum(1 for col in grid for v in col if v), "quadradinhos com contribuição")


if __name__ == "__main__":
    main()
