"""Ajoute name.ja / name.ko aux ombres (data/db/shadows.json). Usage : python3 -I tools/apply_ja_ko_shadows.py
JA : gamewith.jp/sololeveling/447814 (liste des 15 ombres en jeu ; rapprochement par chapitre de déblocage). KO : forum Netmarble KR (post 19/6619),
post Netmarble Instagram (Beru), titre d'une vidéo FR/KO (Uros). Vérifié le 2026-11-15."""
import json
JA = {"igris": "イグリット", "blades": "双刀", "iron": "アイアン", "tank": "タンク", "cerbie": "ケルベロス", "bigrock": "イワオ", "tusk": "キバ",
      "kaisel": "カイセル", "beru": "ベル", "beste": "ベスティ", "skull": "スカル", "jima": "ガーナ", "uros": "ウロス", "brute": "ビッグ", "greed": "グリード"}
KO = {"igris": "이그리트", "blades": "쌍칼", "iron": "아이언", "tank": "탱크", "cerbie": "케르", "bigrock": "큰돌", "tusk": "어금니", "beru": "베르", "uros": "우로스"}
S_JA = "https://gamewith.jp/sololeveling/447814"  # liste d'ombres en jeu (site tiers) ; JA, à vérifier en jeu (Jima=ガーナ, Brute=ビッグ rapprochés par chapitre de déblocage)
S_KO = "https://forum.netmarble.com/slv_kr/view/19/6619 (Netmarble KR) ; Beru : post Netmarble Instagram ; Uros : titre de vidéo AKTUBE ; à vérifier en jeu"
d = json.load(open("data/db/shadows.json"))
for s in d:
    if s["id"] in JA: s["name"]["ja"] = JA[s["id"]]; s["name_ja_source"] = S_JA + " (vérifié le 2026-11-15)"
    if s["id"] in KO: s["name"]["ko"] = KO[s["id"]]; s["name_ko_source"] = S_KO + " (vérifié le 2026-11-15)"
json.dump(d, open("data/db/shadows.json", "w"), ensure_ascii=False, indent=2)
print(sum(1 for s in d if s["name"].get("ja")), sum(1 for s in d if s["name"].get("ko")), len(d))
