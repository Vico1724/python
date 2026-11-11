# Contrôle avant départ (session sur le PC du directeur)

*À faire en premier, avant toute installation. `pc\scripts\0_controle.ps1` vérifie automatiquement la plupart de ces points, sans rien modifier :*

```powershell
powershell -ExecutionPolicy Bypass -File pc\scripts\0_controle.ps1
```

1. **Version du jeu = 25170642.** Elle se lit dans `…\steamapps\appmanifest_3917090.acf`, ligne `"buildid"`. Si elle diffère, le jeu a été mis à jour : prévenir le directeur, refaire le `.usmap`, et s'attendre à des échecs (`docs/updating-after-a-patch.md` d'ACR Extra Stages).
2. **Chemin du jeu :** `Z:\Steamlibrary\steamapps\common\Assetto Corsa Rally`, avec `acr\Content\Paks\global.utoc` présent.
3. **Archives d'origine intactes :** les tailles correspondent à `data\reference\acr_paks_build_25170642.csv`. Seules les deux archives `pakchunk99-*` de BioBio, et éventuellement `~mods\`, s'y ajoutent. Noter le contenu de `Paks` avant l'essai (5_installer.ps1 le consigne aussi).
4. **Dossier de travail sur le même disque que le jeu** (`Z:\acrxs`, en NTFS), avec au moins 10 Go libres sur Z: et 10 Go sur C:.
5. **Jeu fermé, Steam ouvert et hors ligne.**
6. **Outils :**
   - `pwsh --version` doit donner 7.x ;
   - `git --version` ;
   - `dotnet --list-sdks` doit lister une version 10.x ;
   - `cargo --version` ;
   - les outils C++ : un `link.exe` est trouvé par Rust.
   Les manquants s'installent avec 1_prerequis.ps1, avec l'accord du directeur.
7. **ACR Extra Stages** dans `Z:\acrxs\acr-extrastages`, à la version `1324f07d35549a24bd7d2f7d11fe7faaf3e44265`, avec les trois retouches de `pc\patches` appliquées (`git -C Z:\acrxs\acr-extrastages diff --stat` montre 6 fichiers).
8. **Fichier de correspondance** `Z:\acrxs\mappings\acr_25170642.usmap` présent, et validé par `3_usmap.ps1`.
9. **Notre export** présent : `export\stage_ir\grand_caunet\stage.json` (identifiant `grand_caunet_rally_01_route_0`) et `collision.glb` (14 Mo). Si `objects_collision.glb` est présent, l'export contient des obstacles.
10. **BioBio :** avec les options par défaut, il peut rester installé ; avec `-Longueur`, il faut le retirer d'abord (LISEZMOI, § 6).

Si un seul de ces points n'est pas bon, s'arrêter et le dire au directeur, avant d'aller plus loin.
