# Réseaux — kit de lancement (discussion 4)

Version 2 — 2026-11-27 (v1 du 26/11 ; v2 : son de l'intro retiré, emplacements de l'écran de fin, lien Discord ; 27/11 : bannières). **Rien n'est publié ni posé avant le feu vert d'Alexis** (CONTEXTE §2). Ce kit se pose le jour du lancement, dans l'ordre de la section 7.

Limites de caractères : connues au 26/11/2026, **à revérifier** au moment de poser (les plateformes les changent).

## 1. Identité

- Nom affiché : **Shadow Ledger** · identifiant : **@shadowledger_hq** (partout).
- Couleurs : fond `#0B0D17`, violet `#7C5CFF`, bleu glace `#4FD1FF`, texte `#EDEBFF`. Police : Inter (libre, OFL).
- Visuels 100 % originaux : aucun personnage, logo ni capture du jeu (CONTEXTE §4, étape 5).
- Mention « fan project » partout : projet non affilié à Netmarble.

## 2. Logo et photo de profil

Trois pistes (dans `docs/reseaux/` : `logo-a-registre.svg`, `logo-b-sceau.svg`, `logo-c-podium.svg`, aperçu `pistes-logo.png`) :

| Piste | Idée | Lisible à 48 px |
| --- | --- | --- |
| A — Registre | Livre ouvert ; la page droite = barres de classement montantes | moyen (détails fins) |
| B — Sceau | « S » géométrique dans un hexagone dégradé, marque violette = signet du registre | **oui** |
| C — Podium d'ombre | Podium 2-1-3 et son ombre violette, étoile sur le 1er | moyen |

**Choix par défaut : B** pour la photo de profil (seule piste nette en rond de 48 px) ; A ou C réutilisables en bannière. Alexis peut refuser.

Photos de profil (piste B) prêtes dans `profil/` : `profil-youtube-800.png`, `profil-x-400.png`, `profil-instagram-320.png`, `profil-tiktok-200.png`, `profil-discord-512.png` (export `rsvg-convert -w <taille>` ; à refaire si une autre piste est choisie). Bannières (piste B) : `banniere-youtube.svg/.png` (2560 × 1440, texte dans la zone sûre 1546 × 423, vérifié) et `banniere-x.svg/.png` (1500 × 500, texte à droite car la photo de profil recouvre le bas à gauche). À refaire si Alexis choisit une autre piste.

## 3. Descriptions des comptes

**YouTube** (≤ 1 000 car. ; 928 au 27/11)
> FR — Chaque semaine, Shadow Ledger classe les meilleures runs YouTube de Solo Leveling: Arise (Power Of Calamity, Battlefield Of Time, Guild Boss, Hall Of The Monarchs), analyse les builds du top 10 et publie un guide par mode. Pistes audio français et anglais.
> Classements complets et builds : shadowledgerhq.github.io
> Les runs citées sont créditées et liées à leur auteur ; demande de retrait : shadowledgerhq.github.io/site/retrait.html
> Projet de fan, non affilié à Netmarble. Voix de synthèse.
>
> EN — Every week, Shadow Ledger ranks the best Solo Leveling: Arise runs on YouTube (POC, BOT, GB, HOTM), breaks down the top 10 builds and publishes a guide per mode. English and French audio tracks.
> Full rankings and builds: shadowledgerhq.github.io
> Featured runs are credited and linked to their creators; removal requests: shadowledgerhq.github.io/site/retrait.html
> Fan project, not affiliated with Netmarble. Synthetic voice.

**X** (≤ 160) : `Classements hebdo Solo Leveling: Arise (POC·BOT·GB·HOTM), builds du top 10 et guides. Weekly rankings, top 10 builds & guides. FR/EN · fan project` (146)

**Instagram** (≤ 150) : `Weekly Solo Leveling: Arise rankings, top 10 builds & guides 🇬🇧` / `Classements hebdo, builds et guides 🇫🇷` / `Fan project` (114, sur 3 lignes)

**TikTok** (≤ 80, voix EN) : `Weekly Solo Leveling: Arise rankings & builds · FR/EN` (53). Nom affiché : Shadow Ledger (CONTEXTE §9).

**Discord** (description du serveur, ≤ 120) : `Weekly Solo Leveling: Arise rankings, builds & guides. Classements hebdo, builds et guides. FR/EN` (97)

Lien unique dans chaque profil : le site (il renvoie vers tous les comptes).

**Lien d'invitation Discord** : `{{discord_invite}}` — **pas encore créé**. Alexis le crée le jour du lancement (serveur « Shadow Ledger » → Inviter → expiration « Jamais », utilisations illimitées, salon `annonces`) et le colle ici ; le site le reprend dans son pied de page. Avant le lancement, le site garde ce champ vide (aucune invitation publique).

## 4. Intro et outro (≤ 5 s, CONTEXTE §4)

Vidéo 1920 × 1080 et verticale 1080 × 1920, fond `#0B0D17`, sans musique sous licence (son original ou aucun).

**Intro — 2 s**
| t | Image | Son |
| --- | --- | --- |
| 0,0–0,6 s | Le contour hexagonal se trace (dégradé) | aucun |
| 0,6–1,2 s | Le « S » apparaît, signet violet | aucun |
| 1,2–2,0 s | « SHADOW LEDGER » + bandeau du mode (`BOT · Semaine du 26/11`) | aucun |

Son : **aucun** (décision v2 : pas de licence à gérer ; la voix commence après l'intro). Un son original pourra s'ajouter plus tard.

**Outro — 5 s** (exactement 5 s : sert aussi de support à l'écran de fin YouTube, éléments placés sur les 5 dernières secondes)
| t | Image |
| --- | --- |
| 0–5 s | Logo à gauche ; à droite 2 emplacements vides pour l'écran de fin YouTube (vidéo suivante + vidéo du même mode) ; en bas : `@shadowledger_hq` · `shadowledgerhq.github.io` · « Classement complet sur le site / Full ranking on the website » |

Emplacements (1920 × 1080) : 2 cadres de 420 × 236 px à x 900 et x 1380, y 230 (repris du gabarit `docs/GABARIT_VIDEO.md`) : **retenus**. Tailles exactes des éléments YouTube **à vérifier** dans l'éditeur d'écran de fin au 1er envoi en « Privé » ; corriger le gabarit si un élément déborde. Le bouton « S'abonner » de YouTube se place sur le logo, à gauche.

Verticale (TikTok, Shorts, Reels) : outro de 3 s, même texte en haut de l'écran (zone sûre : rien dans les 20 % du bas ni le bord droit).

Génération : script ffmpeg à écrire par la discussion 8 quand la 1re vidéo (discussion 3) sera prête à monter ; texte FR ou EN selon la piste.

## 5. Post X du mercredi

**Contenu** : 4 images dans un seul post (maximum autorisé par X) — POC, BOT, GB, HOTM. Image HOTM : 3 colonnes, une par porte (un classement par porte, CONTEXTE §3). Gabarit : `gabarit-x-mode.svg` (1600 × 900, champs `{{…}}`), aperçu `apercu-post-x.png` (données fictives).

**Données** : seulement les lignes `confidence: sur` avec un `rank` (data/runs/<semaine>/). Moins de 3 lignes sûres → « — » à la place. Nom affiché = nom de la chaîne YouTube (crédit). Unités : POC = Rank Score (SPEC_ETAPE1 v42 §9), BOT = chrono `m:ss.mmm`, GB = RC, HOTM = points. Pas de score `a_verifier` dans l'image.

**Texte** (223 car. sur 280 ; URL comptée 23) :
```
🏆 Classement de la semaine · Weekly ranking — Solo Leveling: Arise
Top 3 POC · BOT · GB · HOTM 👇
Quasi définitif, reset jeudi 01h (Paris) · Final at Thursday reset
Complet / Full: shadowledgerhq.github.io
#SoloLevelingArise
```
Texte alternatif de chaque image (accessibilité) : `<MODE> top 3, semaine du <date> : 1 <chaîne> <score>, 2 …, 3 …`.

Génération des images : `python3 pipeline/post_x.py [semaine]` (Code, 27/11) → `exports/<semaine>/x/` (poc, bot, gb, hotm .png + texte.txt + alt.txt ; non versionné). Rangs ex aequo affichés tels quels (1-1-3) ; pied d'image court « Quasi définitif · Near-final » (ou « Classement définitif · Final ranking ») ; noms tronqués à 28 caractères (20 en HOTM). Contrôlé sur 2026-11-12. Classement sans ligne sûre : pas d'image (retouche demandée à Code). Même image postée dans le salon Discord « classement-de-la-semaine ».

## 6. Calendrier type (après lancement, heure de Paris)

| Jour | Heure | Quoi | Où |
| --- | --- | --- | --- |
| Jeudi | 01h00 | Reset, classement figé | pipeline |
| Vendredi | 18h00 | Vidéo BOT (refaite chaque semaine) | YouTube |
| Samedi | 18h00 | Clip vertical BOT (1-3 min) | TikTok, Shorts, (Reels) |
| Dimanche | 18h00 | Vidéo POC ou GB (selon changement de boss) | YouTube |
| Lundi | 18h00 | Clip vertical de la vidéo de dimanche | TikTok, Shorts |
| Mardi | 18h00 | Vidéo HOTM ou mode restant | YouTube |
| Mercredi | 23h30 | Post X top 3 + Discord | X, Discord |
| Mercredi | 18h00 | 4e vidéo de la semaine | YouTube |

Mercredi 23h30 (Tâche planifiée, 27/11) : le passage PC de 21h15 peut être relancé jusqu'à ~22h15 ; contrôle du mercredi de 23h00 à 23h15, post à 23h30, avant le reset de 01h. Contrôle en erreur → post retenu, Alexis prévenu. Heure révisable quand Code aura donné la durée maximale d'un passage. Heures de vidéo = choix par défaut, à ajuster selon les statistiques après 4 semaines.

## 7. Jour du lancement — ordre de pose

1. Créer le lien d'invitation Discord permanent (section 3) et le mettre dans le site.
2. Photo de profil (piste retenue) sur les 5 comptes.
3. Descriptions (section 3) et lien du site.
4. Discord : salons `annonces`, `classement-de-la-semaine`, `builds`, `discussion-fr`, `discussion-en`, `retrait` (demandes de retrait : preuve = mot « ShadowLedger » dans la description de la chaîne, retrait sous 7 jours, règles de `site/retrait.html`) ; description du serveur.
5. YouTube : bannière, cocher « contenu modifié ou synthétique » sur chaque vidéo, piste audio FR + EN.
6. Premier post X le mercredi suivant le lancement.
