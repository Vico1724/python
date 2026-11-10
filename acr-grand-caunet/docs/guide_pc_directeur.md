# Ce que le directeur peut faire sur son PC

*10 novembre 2026. Rien ici n'est urgent ; chaque point débloque une étape précise.*

## 1. Essayer « Chile BioBio »

C'est la référence choisie pour le projet : une spéciale originale, au rendu réaliste, jouable dans Assetto Corsa Rally.

1. Télécharger l'archive sur <https://sandorally.com/original-stages> (3,8 Go).
2. Fermer le jeu, extraire toute l'archive dans un dossier, lancer `Sando-Rally-Original-Stage-Manager.exe`.
3. Lancer le jeu et choisir la spéciale en Free Practice.

Ce que j'aimerais savoir ensuite :
- la spéciale se lance-t-elle, et votre avis sur le rendu (sol, végétation, bords de route) et sur le copilote ;
- la **liste des fichiers installés**, pour comprendre comment la spéciale est rangée dans le jeu. Dans PowerShell, en adaptant le chemin de Steam :

```powershell
Get-ChildItem -Recurse "C:\Program Files (x86)\Steam\steamapps\common\Assetto Corsa Rally\acr\Content\Paks" |
  Select-Object FullName, Length | Export-Csv "$HOME\Desktop\acr_paks.csv" -NoTypeInformation
```

Le fichier `acr_paks.csv` apparaît sur le Bureau ; il ne contient que des noms et des tailles de fichiers. Déposez-le dans la conversation.

La licence de BioBio autorise le jeu personnel, pas la modification ni la réutilisation sans accord. Je ne reprendrai donc aucun de ses fichiers : la liste sert seulement à comprendre l'organisation.

## 2. Le numéro de version du jeu

Les mods sont liés à la version exacte du jeu. Dans PowerShell :

```powershell
Select-String -Path "C:\Program Files (x86)\Steam\steamapps\appmanifest_3917090.acf" -Pattern '"buildid"'
```

Envoyez-moi la ligne affichée.

## 3. Les vidéos embarquées

Oui, téléchargez-les et déposez-les dans la conversation. Par ordre d'utilité (liens dans `references_videos.md`) :

1. la n° 1 (2025, Clio Rally5) : elle fixe les lignes de départ et d'arrivée ;
2. la n° 2 (2025, régularité) : le rythme lent permet de relever le décor ;
3. la n° 5 (2023, BMW M3) : à vitesse de course, pour le ressenti de la route.

Une qualité de 720p suffit. Si un fichier est trop lourd pour la conversation, des captures d'écran font l'affaire : le départ, l'arrivée, le carrefour du Lion d'Or, puis une toutes les 15 à 20 secondes.

## 4. Écrire à l'auteur de BioBio (facultatif, mais utile)

Sa méthode de fabrication n'est pas publiée. Son adresse figure en bas de <https://sandorally.com>. Deux questions suffisent : accepte-t-il de dire comment il assemble une spéciale (spéciale existante copiée, ou niveau neuf construit dans Unreal Engine) et comment il utilise les arbres et matériaux du jeu sans les redistribuer ? Une réponse ferait gagner plusieurs semaines d'essais.

## 5. Plus tard : laisser le projet travailler sur le PC

La construction du mod et les essais se feront sur ce PC. L'application Claude pour ordinateur peut partager un dossier du PC avec une session comme celle-ci (réglages : Claude Code, puis Remote Control). Aujourd'hui aucun dossier n'est partagé, et cette fonction n'est pas encore ouverte à tous les comptes : si elle ne vous est pas proposée, je vous fournirai des scripts à lancer vous-même.
