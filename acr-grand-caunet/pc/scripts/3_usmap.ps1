#Requires -Version 7.2
<#
.SYNOPSIS
  Produit le « fichier de correspondance » du jeu (.usmap) : la description des structures de données du jeu,
  sans laquelle leurs outils ne savent pas lire les fichiers du jeu. NON TESTÉ (écrit sans Windows).

  Méthode retenue (documentée par ACR Extra Stages, tools/acr-mappings/README.md, « Verified (ACR build 25170642) ») :
  leur outil acr-mappings lance le jeu par Steam, lit sa mémoire en lecture seule depuis l'extérieur (pas
  d'injection), écrit le fichier, puis ferme le jeu. Steam doit être ouvert ; le jeu démarre seul et se ferme
  (30 à 60 s). Le fichier est ensuite contrôlé (« validate ») sur les tables et la spéciale hôte.

  Méthode de secours (documentée, NON automatisée ici) : Dumper-7, voir pc\LISEZMOI.md.

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File pc\scripts\3_usmap.ps1
#>
param([string]$Jeu, [string]$Travail, [string]$Usmap, [switch]$Oui)
. "$PSScriptRoot\commun.ps1"
$ErrorActionPreference = 'Stop'
if (-not $Jeu) { $Jeu = $script:JeuParDefaut }
if (-not $Travail) { $Travail = $script:TravailParDefaut }
Start-Journal $Travail '3_usmap'
Assert-Jeu $Jeu
$src = Get-Source $Travail
$cible = Get-Usmap $Travail
New-Item -ItemType Directory -Force (Split-Path $cible) | Out-Null
if (-not (Test-Path (Join-Path $src 'mods\common\vanilla.ps1'))) { Echec "ACR Extra Stages absent de $src : lancer 2_recuperer_acrxs.ps1" }
. (Join-Path $src 'mods\common\vanilla.ps1')                 # leur fonction New-VanillaView

if ($Usmap) {
    # fichier fourni (par exemple produit par Dumper-7) : simplement copié puis contrôlé
    if (-not (Test-Path $Usmap)) { Echec "fichier introuvable : $Usmap" }
    Copy-Item $Usmap $cible -Force
    Ok "fichier fourni copié vers $cible"
}
elseif (Test-Path $cible) { Ok "fichier déjà produit : $cible" }
else {
    Etape "Production par acr-mappings (le jeu va démarrer puis se fermer)"
    $b = Get-BuildJeu $Jeu
    if ($b -ne $script:BuildJeu) { Attention "version du jeu $b et non $($script:BuildJeu) : acr-mappings refusera probablement (voir LISEZMOI)" }
    if (Test-JeuLance) { Echec "fermer le jeu d'abord (acr-mappings doit le lancer lui-même pour pouvoir le refermer)" }
    if (-not (Confirmer "Steam est ouvert et le jeu peut être lancé maintenant (hors ligne conseillé) ?" -Oui:$Oui)) { Echec "abandon à la demande" }
    $exe = Join-Path $src 'tools\acr-mappings\target\release\acr-mappings.exe'
    if (-not (Test-Path $exe)) { Echec "acr-mappings absent : lancer 2_recuperer_acrxs.ps1" }
    Lancer $exe @('dump', '--game', $Jeu, '--out', $cible, '--cache-dir', (Join-Path $Travail 'mappings\cache')) "production du fichier de correspondance"
    Ok "fichier produit : $cible"
}

Etape "Contrôle du fichier sur les tables du jeu et la spéciale hôte (acr-mappings validate)"
$vue = New-VanillaView $Jeu (Join-Path $Travail 'vanilla')        # liens physiques vers les seules archives d'origine
$exe = Join-Path $src 'tools\acr-mappings\target\release\acr-mappings.exe'
Lancer $exe @('validate', '--game', $Jeu, '--usmap', $cible, '--vanilla', $vue, '--tool', (Join-Path $Travail 'bin\acr-additive\acr-additive.exe'),
              '--cache-dir', (Join-Path $Travail 'mappings\cache')) "contrôle du fichier de correspondance"
Ok "fichier de correspondance valable. Étape suivante : 4_construire.ps1"
Stop-Journal
