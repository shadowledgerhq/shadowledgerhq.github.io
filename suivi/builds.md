# SUIVI — 2 Builds — 2026-11-14
## Fait
- SPEC_ETAPE2 v1 (`docs/SPEC_ETAPE2.md`) : éléments par mode, format JSON Build, statuts, PowerPoint FR/EN, origine des données, 12 points [EN ATTENTE]
- HOTM : hunter_mode booléen (true = sans SJW), SJW non attendu sans SJW ; compétences SJW = 6 emplacements
## En cours
- Implémentation par la discussion 8 (export_pptx.py, builds, tests §7)
## À faire
- Contrôler les premiers builds et PowerPoint (§6)
- Régler seuil_icone / ecart_icone après essai sur 3 vidéos
- Compléter les règles POC et GB dans data/rules
## Besoin d'Alexis
- 1 capture 1080p par onglet de composition : BOT, POC, HOTM avec et sans SJW, GB
- Règles POC et GB de la semaine (SJW, ombres, successeur)
- Captures de l'écran de composition GB
- Décisions : stats obligatoires pour build_complet ? compétences des chasseurs dans le build ?
## Demandes de modif du skill
- Format Build (§3) : remplacer par SPEC_ETAPE2 §1.2
- Format Run : hunter_mode booléen ; gate entier
- data/rules : clé bot_season à renommer bot (v10 étape 1)
- Checklist Builds : « un PowerPoint par vidéo et par langue »
