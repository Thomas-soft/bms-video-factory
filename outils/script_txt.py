"""Sort un script de run en .txt lisible par un humain. Rien d'ajouté, rien d'inventé :
tout vient de script.json et de voice/timings.json."""
import json, pathlib, sys

run = pathlib.Path(sys.argv[1])
d = json.load(open(run / "script.json", encoding="utf-8"))
tim = json.load(open(run / "voice/timings.json", encoding="utf-8"))
durees = {s["id"]: s for s in tim["segments"]}
fr = d["lang"] == "fr"

def mmss(s):
    return f"{int(s) // 60:d}:{int(s) % 60:02d}"

L = []
titre = "SCRIPT — BMS Science FR" if fr else "SCRIPT — BMS Science EN"
L.append(titre)
L.append("=" * len(titre))
L.append("")
L.append(f"{'Langue' if fr else 'Language'} : {d['lang']}   ·   "
         f"{'Segments' if fr else 'Segments'} : {len(d['segments'])}   ·   "
         f"{'Mots' if fr else 'Words'} : {d['word_count']}")
L.append(f"{'Durée de la voix enregistrée' if fr else 'Recorded voice duration'} : "
         f"{mmss(tim['total_duration_s'])} ({tim['total_duration_s']:.1f} s)   ·   "
         f"{'Loudness' if fr else 'Loudness'} : {tim['loudness_lufs']} LUFS")
L.append(f"{'Voix' if fr else 'Voice'} : {tim['voice_id']}   ·   {'Moteur' if fr else 'Engine'} : {tim['engine']}")
sig = d.get("editorial_signature") or {}
if sig:
    L.append("")
    L.append(("ANGLE ÉDITORIAL : " if fr else "EDITORIAL ANGLE: ") + str(sig.get("angle", "")))
    for e in sig.get("elements_proprietaires", []):
        ligne = "    — "
        for mot in str(e).split():
            if len(ligne) + len(mot) + 1 > 78:
                L.append(ligne.rstrip()); ligne = "      "
            ligne += mot + " "
        L.append(ligne.rstrip())
L.append("")
L.append("-" * 78)
L.append("")
L.append(("ACCROCHE" if fr else "HOOK") + f"  [{d['hook']['type']}]")
L.append("")
L.append("    " + d["hook"]["text"])
L.append("")
L.append("-" * 78)
L.append("")

for s in d["segments"]:
    t = durees.get(s["id"])
    tete = f"{s['id'].upper()}  ·  {s['role']}"
    if t:
        tete += f"  ·  {mmss(t['start_s'])} → {mmss(t['end_s'])}  ({t['duration_s']:.1f} s)"
    L.append(tete)
    if s.get("on_screen_text"):
        L.append(("    À L'ÉCRAN : " if fr else "    ON SCREEN: ") + s["on_screen_text"])
    L.append("")
    # narration coupée à 78 colonnes, sans couper les mots
    ligne = "    "
    for mot in s["narration"].split():
        if len(ligne) + len(mot) + 1 > 78:
            L.append(ligne.rstrip())
            ligne = "    "
        ligne += mot + " "
    L.append(ligne.rstrip())
    if s.get("sources"):
        L.append("")
        L.append(("    SOURCES : " if fr else "    SOURCES: ") + " · ".join(str(x) for x in s["sources"]))
    if s.get("disclosure_spoken"):
        L.append("    " + ("[MENTION SPONSOR LUE À VOIX HAUTE]" if fr else "[SPONSOR DISCLOSURE READ ALOUD]"))
    L.append("")

if d.get("disclosure_lines"):
    L.append("-" * 78)
    L.append("")
    L.append(("MENTIONS" if fr else "DISCLOSURES"))
    L.append("")
    for x in d["disclosure_lines"]:
        L.append("    " + str(x))
    L.append("")

sortie = run / ("script-" + run.name + ".txt")
sortie.write_text("\n".join(L) + "\n", encoding="utf-8")
print(sortie, f"{sortie.stat().st_size} o")
