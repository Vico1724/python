"""Étape 6 - Figures de contrôle : carte générale, profil en long, zooms départ/arrivée.

Sorties : figures/carte_generale.png, profil_en_long.png, zoom_depart.png, zoom_arrivee.png
"""
import csv
import io
import json

import matplotlib

matplotlib.use("Agg")
import matplotlib.patheffects as pe
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

from acr_geo import FIG, LAYER_ORTHO, OUT, l93, load_official, wms_tile

INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#fcfcfb"
BLUE, ORANGE = "#2a78d6", "#eb6834"
HALO = [pe.withStroke(linewidth=2.5, foreground="white")]
plt.rcParams.update({"font.size": 9, "axes.edgecolor": "#c3c2b7", "axes.labelcolor": INK2,
                     "xtick.color": MUTED, "ytick.color": MUTED, "figure.facecolor": SURFACE,
                     "axes.facecolor": SURFACE, "axes.spines.top": False, "axes.spines.right": False})


def load():
    off = load_official()
    with open(OUT / "profil_es.csv") as f:
        prof = {k: np.array([float(r[k]) for r in rows]) for rows in [list(csv.DictReader(f))]
                for k in ("pk_m", "x_l93", "y_l93", "z_chaussee_m", "pente_pct")}
    with open(OUT / "ouvrages_es.csv") as f:
        bridges = list(csv.DictReader(f))
    cal = json.loads((OUT / "calage_es.json").read_text(encoding="utf-8"))
    return off, prof, bridges, cal


def ortho(x0, y0, x1, y1, res):
    return Image.open(io.BytesIO(wms_tile(LAYER_ORTHO, x0, y0, x1, y1, res, fmt="image/jpeg")))


def at(prof, k):
    return np.interp(k, prof["pk_m"], prof["x_l93"]), np.interp(k, prof["pk_m"], prof["y_l93"])


def carte(off, prof, cal):
    L = off["longueur_officielle_km"] * 1000
    x0, x1 = prof["x_l93"].min() - 350, prof["x_l93"].max() + 350
    y0, y1 = prof["y_l93"].min() - 250, prof["y_l93"].max() + 250
    x0, y0, x1, y1 = (round(v / 10) * 10 for v in (x0, y0, x1, y1))
    fig, ax = plt.subplots(figsize=(13, 13 * (y1 - y0) / (x1 - x0) + 0.6))
    ax.imshow(ortho(x0, y0, x1, y1, 2.0), extent=(x0, x1, y0, y1))
    st = (prof["pk_m"] >= 0) & (prof["pk_m"] <= L)
    ax.plot(prof["x_l93"], prof["y_l93"], color="white", lw=1.2, ls=(0, (3, 2)), label="liaison (CH, point stop)")
    ax.plot(prof["x_l93"][st], prof["y_l93"][st], color="white", lw=4.5)
    ax.plot(prof["x_l93"][st], prof["y_l93"][st], color=ORANGE, lw=2.6, label="ES chronométrée (6,702 km)")
    for k in range(1000, int(L), 1000):
        x, y = at(prof, k)
        ax.plot(x, y, "o", ms=6, mfc="white", mec=INK, mew=1)
        ax.annotate(f"km {k // 1000}", (x, y), xytext=(6, 6), textcoords="offset points", color=INK,
                    fontsize=9, path_effects=HALO)
    for name, k in (("DÉPART", 0), ("ARRIVÉE", L)):
        x, y = at(prof, k)
        ax.plot(x, y, "s", ms=9, mfc=INK, mec="white", mew=1.5)
        ax.annotate(name, (x, y), xytext=(8, -14), textcoords="offset points", color=INK, fontsize=11,
                    weight="bold", path_effects=HALO)
    for p in off["points"]:
        if p["role"] in ("controle_horaire", "point_stop"):
            x, y = l93(p["lon"], p["lat"])
            ax.plot(x, y, "D", ms=6, mfc="white", mec=INK, mew=1)
            ax.annotate("CH" if p["role"] == "controle_horaire" else "STOP", (x, y),
                        xytext=(-28, 6) if p["role"] == "controle_horaire" else (7, 5),
                        textcoords="offset points", color=INK, fontsize=9, path_effects=HALO)
    for txt, k, dx, dy in (("D3D\nForêt de Font-Blanche", 1500, -150, 0), ("Le Lion d'Or\n(carrefour D3D / D1)", 3619, 20, 12),
                           ("D1 vers Roquefort-la-Bédoule", 5200, -60, 22)):
        x, y = at(prof, k)
        ax.annotate(txt, (x, y), xytext=(dx, dy), textcoords="offset points", color=INK, fontsize=9,
                    style="italic", path_effects=HALO, ha="left")
    ax.plot([x0 + 150, x0 + 650], [y0 + 120, y0 + 120], color="white", lw=5)
    ax.plot([x0 + 150, x0 + 650], [y0 + 120, y0 + 120], color=INK, lw=2.5)
    ax.text(x0 + 400, y0 + 150, "500 m", ha="center", color=INK, path_effects=HALO)
    ax.annotate("N", (x1 - 180, y1 - 330), xytext=(x1 - 180, y1 - 130), ha="center", color=INK, fontsize=12,
                weight="bold", path_effects=HALO, arrowprops=dict(arrowstyle="<-", color=INK, lw=1.8))
    ax.set_xlim(x0, x1), ax.set_ylim(y0, y1), ax.set_axis_off()
    ax.legend(loc="lower right", frameon=True, facecolor="white", framealpha=0.9, edgecolor="none")
    ax.set_title("ES Le Grand Caunet - Sainte-Baume Rallye 2026 - tracé reconstitué sur BD TOPO, fond BD ORTHO (IGN)",
                 color=INK, fontsize=12, loc="left")
    fig.savefig(FIG / "carte_generale.png", dpi=110, bbox_inches="tight")
    plt.close(fig)


def profil(off, prof, bridges):
    L = off["longueur_officielle_km"] * 1000
    st = (prof["pk_m"] >= 0) & (prof["pk_m"] <= L)
    pk, z, sl = prof["pk_m"][st], prof["z_chaussee_m"][st], prof["pente_pct"][st]
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(13, 6.6), sharex=True, height_ratios=[2.4, 1],
                                 gridspec_kw={"hspace": 0.12})
    a1.fill_between(pk, z, z.min() - 12, color=BLUE, alpha=0.12, lw=0)
    a1.plot(pk, z, color=BLUE, lw=2)
    for p in off["points"]:
        k = p["pk_km"] * 1000
        if p["role"] == "intermediaire":
            zi = np.interp(k, pk, z)
            a1.plot([k, k], [z.min() - 12, zi], color=GRID, lw=1, zorder=0)
            a1.annotate(p["id"].replace("INTER", "I"), (k, zi), xytext=(0, 7), textcoords="offset points",
                        ha="center", color=INK2, fontsize=8)
    for name, k, ha in (("Départ", 0, "left"), ("Arrivée", L, "right")):
        zi = np.interp(k, pk, z)
        a1.plot(k, zi, "o", ms=8, mfc=BLUE, mec=SURFACE, mew=2)
        a1.annotate(f"{name} {zi:.0f} m", (k, zi), xytext=(8 if ha == "left" else -8, 8),
                    textcoords="offset points", ha=ha, color=INK, weight="bold")
    i = z.argmin()
    a1.annotate(f"point bas {z[i]:.0f} m\n(Le Lion d'Or)", (pk[i], z[i]), xytext=(70, -4), textcoords="offset points",
                ha="left", va="center", color=INK)
    bx = [(float(b["pk_debut_m"]) + float(b["pk_fin_m"])) / 2 for b in bridges
          if b["dans_es"] == "True" and float(b["hauteur_sous_tablier_m"]) >= 1]
    a1.plot(bx, np.interp(bx, pk, z) - 5, "^", ms=5, color=INK2, label=f"pont ou ponceau ({len(bx)})")
    a1.legend(loc="upper right", frameon=False)
    a1.set_ylabel("altitude de la chaussée (m)")
    a1.set_ylim(z.min() - 12, z.max() + 14)
    a1.grid(axis="y", color=GRID, lw=0.8)
    a1.set_title("ES Le Grand Caunet - profil en long (LiDAR HD IGN, 0,5 m)", color=INK, loc="left", fontsize=12)
    a2.axhline(0, color="#c3c2b7", lw=1)
    a2.fill_between(pk, sl, 0, color=BLUE, alpha=0.25, lw=0)
    a2.plot(pk, sl, color=BLUE, lw=1)
    a2.set_ylabel("pente (%)\n+ montée / - descente")
    a2.set_xlabel("distance depuis le départ (m)")
    a2.grid(axis="y", color=GRID, lw=0.8)
    a2.set_xlim(-60, L + 60)
    fig.savefig(FIG / "profil_en_long.png", dpi=120, bbox_inches="tight")
    plt.close(fig)


def zoom(off, prof, cal, name, ids, key, pk_line):
    pts = {p["id"]: l93(p["lon"], p["lat"]) for p in off["points"]}
    cx, cy = cal[key]["x_l93"], cal[key]["y_l93"]
    half = 130
    x0, y0, x1, y1 = (round(v) for v in (cx - half, cy - half, cx + half, cy + half))
    fig, ax = plt.subplots(figsize=(9, 9))
    ax.imshow(ortho(x0, y0, x1, y1, 0.2), extent=(x0, x1, y0, y1))
    ax.plot(prof["x_l93"], prof["y_l93"], color=ORANGE, lw=1.2, alpha=0.9, label="axe BD TOPO")
    for k in range(int(pk_line) - 150, int(pk_line) + 151, 25):
        x, y = at(prof, k)
        ax.plot(x, y, "o", ms=3, color="white")
        ax.annotate(f"{k}", (x, y), xytext=(4, 4), textcoords="offset points", color="white", fontsize=7,
                    path_effects=[pe.withStroke(linewidth=2, foreground=INK)])
    ax.plot(cx, cy, "s", ms=11, mfc=ORANGE, mec="white", mew=2, label=f"ligne calée sur les PK officiels (PK {pk_line:.0f})")
    for i in ids:
        ax.plot(*pts[i], "X", ms=11, mfc="white", mec=INK, mew=1.2)
        ax.annotate(f"{i} (coordonnée imprimée)", pts[i], xytext=(8, 8), textcoords="offset points",
                    color=INK, fontsize=9, path_effects=HALO)
    ax.set_xlim(x0, x1), ax.set_ylim(y0, y1), ax.set_axis_off()
    ax.legend(loc="lower left", facecolor="white", framealpha=0.9, edgecolor="none")
    ax.set_title(f"Zone {'du départ' if name == 'depart' else 'de l’arrivée'} - BD ORTHO 20 cm - graduations = PK en mètres", color=INK, loc="left", fontsize=11)
    fig.savefig(FIG / f"zoom_{name}.png", dpi=105, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    off, prof, bridges, cal = load()
    carte(off, prof, cal)
    profil(off, prof, bridges)
    zoom(off, prof, cal, "depart", ["CH", "DEPART"], "depart_cale", 0)
    zoom(off, prof, cal, "arrivee", ["ARRIVEE"], "arrivee_calee", off["longueur_officielle_km"] * 1000)
    print("figures écrites dans", FIG)
