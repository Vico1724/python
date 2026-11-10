# Ce que le directeur peut faire sur son PC

*10 novembre 2026. Rien ici n'est urgent ; chaque point débloque une étape précise.*

## 1. Reçu

- La liste des fichiers du jeu avec BioBio installé, et le numéro de version (25170642). L'analyse est dans `01_etude_faisabilite.md`, § 4.
- Reste votre avis sur BioBio en jeu : rendu du sol, de la végétation, des bords de route, et copilote.

## 2. Les sommaires des deux archives de BioBio

Deux petits fichiers suffisent à savoir comment la spéciale est construite. Ils ne contiennent que la liste des éléments de l'archive, pas les éléments eux-mêmes. Dans le dossier `Z:\Steamlibrary\steamapps\common\Assetto Corsa Rally\acr\Content\Paks`, déposez dans la conversation :

- `pakchunk99-ChileBioBio_P.utoc` (1,4 Mo) ;
- `pakchunk99-SandoRegistry_2_P.utoc` (2 ko).

Si possible, ajoutez les sommaires du jeu lui-même, qui me donneront le catalogue des arbres, matériaux et surfaces que notre spéciale pourra référencer. Dans PowerShell :

```powershell
Compress-Archive -Path "Z:\Steamlibrary\steamapps\common\Assetto Corsa Rally\acr\Content\Paks\*.utoc" -DestinationPath "$HOME\Desktop\acr_utoc.zip"
```

Le fichier `acr_utoc.zip` (17 Mo avant compression) apparaît sur le Bureau.

## 3. Les vidéos embarquées

Les fichiers en 720p sont trop lourds pour la conversation. Par ordre de préférence :

1. **Un lien de partage** : déposez les vidéos sur Google Drive, OneDrive ou Dropbox, réglez le partage sur « toute personne disposant du lien » et collez le lien ici. Je les téléchargerai depuis le serveur du projet.
2. **Une qualité plus basse** : 360p suffit pour situer les lignes et relever le décor.
3. **Des captures d'écran** : le départ, l'arrivée, le carrefour du Lion d'Or, puis une toutes les 15 à 20 secondes.

Vidéos utiles, par ordre (liens dans `references_videos.md`) : la n° 1 (2025, Clio Rally5) pour les lignes de départ et d'arrivée, la n° 2 (2025, régularité) pour le décor, la n° 5 (2023, BMW M3) pour le ressenti de la route.

## 4. Écrire à l'auteur de BioBio (facultatif, mais utile)

Sa méthode de fabrication n'est pas publiée. Son adresse figure en bas de <https://sandorally.com>. Deux questions suffisent : accepte-t-il de dire comment il assemble une spéciale (spéciale existante copiée, ou niveau neuf construit dans Unreal Engine) et comment il utilise les arbres et matériaux du jeu sans les redistribuer ? Une réponse ferait gagner plusieurs semaines d'essais.

## 5. Plus tard : laisser le projet travailler sur le PC

La construction du mod et les essais se feront sur ce PC. L'application Claude pour ordinateur peut partager un dossier du PC avec une session comme celle-ci (réglages : Claude Code, puis Remote Control). Aujourd'hui aucun dossier n'est partagé, et cette fonction n'est pas encore ouverte à tous les comptes : si elle ne vous est pas proposée, je vous fournirai des scripts à lancer vous-même.
