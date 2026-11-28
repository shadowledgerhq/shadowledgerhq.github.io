# Contrôle automatique des passages (discussion 7)

Tâche planifiée Claude « Contrôle SLA quotidien », chaque jour à 08:21 (Paris), après les passages de la veille. Un rapport par jour : `docs/controle/AAAA-MM-JJ.md` (date du contrôle). Zone de la discussion 7 : rien d'autre n'est modifié.

## Horaires contrôlés (27/11/2026)
- GitHub daily : 18:00 Paris ; weekly : jeudi 01:00.
- PC (Planificateur) : quotidien 19:30, 21:30, 23:30 ; hebdomadaire jeudi 01:15 ; relance ponctuelle (anti-bot, une par soir ; relance manquée de plus de 2 h = annulée).
- Mercredi, après le lancement public : contrôle 23:30, post 23:45 (retenu si problème).

## Points contrôlés (semaine en cours, et semaine écoulée si non gelée)
1. Passage GitHub de la veille fait (`_meta.json` `passages.daily`) et avant le 1er passage PC.
2. Blocs PC de la veille (`_rapport_pc.md`) : un bloc « Lancement : planificateur » à 19:30, 21:30, 23:30 ; aucun à une autre heure ; relances et reports cohérents.
3. Anti-bot : nombre de passages incomplets, vidéos traitées, `en_cours` restantes, candidates au top 10 restantes (évolution sur 3 jours).
4. Critère de gel n° 3 : seuls les passages planifiés sur semaine non vide comptent ; état avant le jeudi.
5. Classements publiés (`poc.json`, `bot.json`, `gb.json` ; HOTM arrêté le 28/11) : checklist Classements du skill (tri, une ligne par chaîne, `rank` seulement sur `sur`, écarts improbables) ; POC : ordre palier, Goal Progress, Rank Score (CONTEXTE §3).
6. Erreurs bloquantes, JSON abîmés, conflits git notés dans les rapports.

## Sortie
- Rapport court (20 lignes max) : OK / alerte par point, avec fichier et ligne.
- Problème qui relève d'une autre discussion : message dans sa boîte (`claude/BOITE.md` pour 1-6, `docs/BOITE.md` §8-9) et ligne « Messages posés ».
- `suivi/tache-planifiee.md` mis à jour.
