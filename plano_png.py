import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, generar as G
e = G.estructura(); c, t = G.caja()
hojas = dict(G.laminas_estructura(e)); hojas['cajas'] = G.lamina_cajas(c, t)
for nom, col in hojas.items():
    fig, ax = plt.subplots(figsize=(15, 10), dpi=70)
    ax.add_patch(plt.Rectangle((0, 0), 1830, 1220, fill=False, ec='gray'))
    for n, g, gr, *_ in col:
        for r in [g.exterior, *g.interiors]: ax.plot(*r.xy, 'r', lw=0.5)
        for q in gr: ax.plot(*q.exterior.xy, 'b', lw=0.5)
        if n: ax.text(*g.representative_point().coords[0], n, fontsize=6, color='g')
    ax.set_aspect('equal'); ax.invert_yaxis(); ax.set_title(nom); plt.tight_layout(); plt.savefig(f'plano {nom}.png'); plt.close()
