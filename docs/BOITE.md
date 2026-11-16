# Boîte aux lettres entre discussions

Messages écrits par les discussions 8 (Code) et 9 (Base de données) pour les discussions 1 à 7, qui ne lisent pas le dépôt en continu. Une section par destinataire ; la discussion destinataire lit sa section au démarrage, traite les messages `[à traiter]` puis passe leur statut à `[traité]` (avec la date).

Format d'une ligne : `- [à traiter] AAAA-MM-JJ — de Code — message`  (ou `de Base de données`)

## 1 — Étape 1 — Classements

- [traité 2026-11-16] 2026-11-16 — de Code — SPEC v27 écrite dans `docs/SPEC_ETAPE1.md` (§3.1 BOT, §8) et codée (réponse à ma question sur le RESULT BOT japonais). (1) Lecture par zone du temps de jeu et de chaque ligne de phase (`config.bot.zones_lecture`, 16:9) sur un écran candidat, vote entre prétraitements (accord ≥ 2, format strict) ; temps de jeu lu et cohérent avec la dernière phase → règle v26, `sûr` possible. (2) Repli : titre `RESULT`/`結果` + ≥ 2 temps (ou 2 phases lues par zone) → `a_verifier`, note « BOT ja : temps de jeu non lu ». (3) Anti-animation : temps lu sur ≥ 2 images distinctes (par `t`, idempotent), sinon `a_verifier` + « temps instable (animation ?) » ; lecture instable de même 1re phase qu'une lecture stable = écartée. (4) `信行時間` et `結果` ajoutés. (5) Essai vrai tesseract : 2e capture 4,734 / 15,212 / 29,224, temps de jeu 29 → `sûr` après 2 images ; 1re capture 9,095 / 14,910 / 19,558, temps de jeu masqué par le décor → `a_verifier` ; passage complet simulé (boucle `traiter_images`) idem. Choix de Code à valider : le boss n'est pas lu en mode zone (`stage` vide, l'OCR du titre était du bruit) ; la règle des 2 images ne vaut que pour le mode zone/repli (le chemin v26 avec chrono du bandeau reste `sûr` sur 1 image). Zones calées sur 2 captures : le premier vrai passage du PC tranche.
- [traité 2026-11-16 : SPEC v27] 2026-11-16 — de Code — Question SPEC v26 (RESULT BOT japonais) : j'ai passé le VRAI tesseract (jpn+eng) sur les 2 captures `docs/essais/composition/bot_results*_ja.png`. Image entière, psm 6 : `Phase1` est lu « Men 4 », `進行時間` est lu `信行時間`, le temps de jeu `00:29` est illisible ; l'écran n'est reconnu « bot » que sur certains prétraitements (psm 11, agrandissement 2,5×), jamais sur la 1re capture. La règle v26 (titre + 2 temps sans temps de jeu = pas un BOT, pour ne jamais lire un écran en animation) est donc rarement satisfaite sur l'OCR réel. Je n'ai rien changé (contraire à la SPEC). Proposition à trancher : accepter RESULT + ≥ 2 temps `mm:ss.mmm` + « Phase » comme `a_verifier` (jamais `sûr`), ou lire le temps de jeu par zone recadrée. Les frames étant nombreuses par vidéo, une partie sera détectée de toute façon ; l'essai réel du PC tranchera.
- [traité 2026-11-16] 2026-11-16 — de Code — Critère de gel n° 3 codé : (1) `data/runs/<semaine>/_rapport_pc.md` = un bloc daté par passage PC, jamais effacé (le même passage remplace seulement son bloc) ; le passage GitHub ne le modifie pas et recopie le dernier bloc en tête de `_rapport.md` (« Dernier passage du PC »). (2) Tout échec écrit son bloc « Passage complet : non » + cause : git, JSON abîmé, crash, verrou refusé, ET passage précédent mort (PC éteint / fenêtre fermée, détecté au passage suivant par le verrou périmé). MISE À JOUR 16/11 d'après `logs\\pc.log` (vu par Alexis) : 3 passages le 15/11 (00:32 daily, 02:32 daily relance, 20:30 daily) ; le journal se termine sur un CRASH du passage de 20:30 : `JSONDecodeError: Expecting property name enclosed in double quotes: line 427 column 1 (char 9062)` dans `donnees.lire` (ancien code, le PC n'avait pas les dernières versions) = un fichier JSON de data/ abîmé (virgule en trop) ; l'ancien code ne l'a pas signalé dans le rapport. Désormais `JsonAbime` nomme le fichier et un bloc « Passage complet : non » est écrit. Cause du 02:32 (journal) : la tâche de relance lançait `pc.py daily relance` et argparse répondait `unrecognized arguments: relance` : la relance n'a JAMAIS tourné (bug de ma part, corrigé : le mot nu `relance` est accepté, test). Le passage de 00:32 s'était terminé en « passage incomplet : anti-bot ; relance programmée 02:32 » (429, 42 vidéos reportées pour les images, 51 en_cours). Hypothèses d'origine (avant ce journal) [À VÉRIFIER, `logs\\pc.log` est sur le PC d'Alexis, pas dans le dépôt] : erreur git dans `Git.tirer` avant toute écriture (nous l'avons revue le 16/11 : « local changes would be overwritten »), ou arrêt brutal ; le commit « reprise » de 21:39 est `Git.tirer` commitant `processed.json` laissé par un passage tué. (3) Conflit git sur data/ : fusion automatique, distant pour les fichiers GitHub, PC pour `_rapport_pc.md`/builds/cartes, fusion par vidéo pour `processed.json` et `_lectures.json`, bloc noté « Conflit git résolu automatiquement ». À valider au prochain passage PC réel.
- [traité 2026-11-16 : SPEC v23, réponse via Alexis] 2026-11-15 — de Code — Relance des 6 vidéos GB faite par Alexis (code v19, 29 min, résolution 1920×1080 pour les 6). Bilan sur main : `docs/essais/ocr/_resume_6videos.json`. Résultats (RC / Final Score / confiance) : awb-GlVIa7Q 189 / 64 299 126 429 862 / a_verifier (somme des groupes ≠ Final, Hunter Rank non décroissants) ; nh2D7xZ7dOQ 167 + 165 = 332, sûr (Total Score du Personal Record incohérent, noté) ; T5dR6iJAn-Y 156 / 7 907 273 299 084 / sûr ; Oj_-5x6700s 137 / 3 096 765 357 626 / sûr (écart HUD 0,077 %) ; vYtRCpFtSOk 162 / 12 859 482 380 262 / a_verifier ; MJ2iz5TFmvM 160 / 10 661 037 770 748 / a_verifier (conflits player_score et hunter_rank_3 ; Points HUD 10 375 798 059 160, écart 2,7 %, non rejetés car dans [1e9 ; 1e14]). À contrôler : les notes « écart titre/écran : titre 159 » (T5dR) et « groupes inconnus : 2e run non additionnée » (Oj_) ne figurent pas dans ce bilan (peut-être seulement dans le classement) ; Points HUD de MJ2 à rejeter ou non ; règles 17 ; décision `pc.geler` (reste false). Suite : vérifie ces points, puis donne la spec ou la décision.

## 2 — Étape 2 — Builds

(aucun message)

## 3 — Étape 3 — Theorycraft & vidéos

(aucun message)

## 4 — Étape 4 — Réseaux

(aucun message)

## 5 — Étape 5 — Site

(aucun message)

## 6 — Prompt

(aucun message)

## 7 — Tâche planifiée

(aucun message)
