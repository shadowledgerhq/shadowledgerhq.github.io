# SUIVI — 8 Code — 2026-11-27 (fin session 19, message 15)
## Fait
- Détail archivé : `suivi/archives/code_2026-11-15_a_20.md`, `code_2026-11-22_a_26.md`, `code_2026-11-26_a_27.md` (sessions 17-19 : specs « état actuel » v42, horaires PC 19:30/21:30/23:30, gel 2026-11-19, midi v43, site privé).
- (27/11) `data/runs/index.json` (`donnees.mettre_a_jour_index`) ; Pages coupé (site 404) ; `pipeline/post_x.py` (Réseaux ; pas d'image sans ligne sûre) ; rendu vidéo dans `pipeline/video/` ; rotation : « phases incomplètes ».
- (27/11) Passage GitHub daily avancé à **18:00** (`daily.yml` 16:00Z/17:00Z, créneau 18:00-23:59) : Actions a 45 min de retard. Relance du soir indépendante de celle du weekly ; relance lancée > 2 h après son heure = annulée.
- (27/11) **SPEC_ETAPE2 v8 + v9** (top 10 mixte, classée rang 1-10 garde son build, `config.spec_version`) ; **SPEC_ETAPE1 v43** (texte POC : marque de mode, intervalle, palier + %, borne 0) ; **POC 2026-11-19 corrigé** (`pipeline/corriger_poc_v43.py`, titres seulement). 512 tests OK.
- (27/11 22:30) Anti-bot : sous-titres en 429 (formats OK) ; `tester_ytdlp` teste aussi les sous-titres ; test réel d'Alexis : AUCUN réglage ne passe (défaut, Chrome imité, cookies Firefox : 429 ; Edge : DPAPI ; Brave : absent). Adresse limitée.
## En cours
- **v10 de la SPEC_ETAPE2 PAS codée** (`spec_version` déjà 10) : `_zones_poc` validées ; zone `zones.poc.<onglet>.equipe.label` [0.35,0.90,0.44,0.96] (OCR « Team 1 »/« 1팀 »/« パーティ2 ») : image lue pour `runs_detail[i]` seulement si équipe = `team` (jamais de vote entre équipes) ; image de fondu écartée si netteté < 50 % de la meilleure du même onglet (cas 2AJljDc_nN4).
- Passages PC du 27/11 : 0 vidéo traitée (19:30 reporté, 20:00 et 22:00 anti-bot), 48 `en_cours`. Bilan v39/v40 (BOITE §1) et 28 rejets « mecharashi » (2026-11-12) : toujours à faire.
- Mes messages en attente : Classements (v43 codée, BOITE §1), Builds (v8/v9, BOITE §2), Tâche planifiée (BOITE §7), Réseaux/Theorycraft/Site (§3-5).
## À faire
- Anti-bot : vérifier si le passage continue vers les images (téléchargement vidéo) quand les sous-titres font 429 ; sinon l'ordre sous-titres → images bloque tout le passage.
- Relectures posées jamais faites (`3y8yRhcSq4Y`…), gel de 2026-11-26 le 03/12 01:15 (`pc.geler`), relance PC des builds 2026-11-12 (Alexis), vidéos verticales 608x1080 (accord donné, à régler sur une vraie vidéo).
- `pc.py` (2000+ lignes) : le scinder à la prochaine spec qui le touche.
## Besoin d'Alexis
- Attendre 1 à 2 h puis relancer `outils-pc\5_test_antibot.bat` (Firefox ouvert sur YouTube, connecté), puis `3_passage_complet.bat`.
## Demandes de modif du skill
- `SKILL.md` décrit encore BOT « deux classements » : à aligner sur la v10 (discussion 1).
