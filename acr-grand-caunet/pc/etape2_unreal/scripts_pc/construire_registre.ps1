#Requires -Version 7
<#
.SYNOPSIS
  Construit le conteneur « registre » qui inscrit notre niveau d'essai dans les menus du jeu (essai E2a du
  protocole) : zz_gc_registre_P.utoc/.ucas/.pak dans <travail>\unreal\dist. N'écrit RIEN dans le jeu.

  EXÉCUTÉ sur le PC le 11/11/2026 (construction seulement ; jamais installé ni essayé en jeu).

  Chaîne, recopiée de mods\additive\build.ps1 d'ACR Extra Stages (l. 177-200 et suivantes) :
    retoc to-legacy --filter Data/Database/Main/   tables de menus d'origine (vue sans mods ni BioBio)
    acr-additive registry                          ajoute nos lignes (fiche JSON) aux tables
    retoc to-zen --version UE5_6                   empaquetage

  ATTENTION : ce conteneur livre les tables de menus EN ENTIER (DT_Levels, DT_Tracks, DT_TracksVariants...), comme le
  registre de BioBio (pakchunk99-SandoRegistry_2_P). Les deux ne cohabitent pas : avant de l'installer, mettre BioBio
  de côté avec l'accord du directeur (PROTOCOLE.md, E2a, « Écueil »).

.EXAMPLE
  pwsh -File pc\etape2_unreal\scripts_pc\construire_registre.ps1
#>
param(
    [string]$Fiche,
    [string]$Travail = 'Z:\acrxs',
    [string]$Nom = 'zz_gc_registre_P'
)
$ErrorActionPreference = 'Stop'
$kit = Split-Path $PSScriptRoot
if (-not $Fiche) { $Fiche = Join-Path $kit 'registre\gc_essai.json' }
$retoc = Join-Path $Travail 'bin\retoc\bin\retoc.exe'
$outil = Join-Path $Travail 'bin\acr-additive\acr-additive.exe'
$paks = Join-Path $Travail 'construction\vanilla\acr\Content\Paks'      # vue d'origine de l'étape 1 (liens physiques)
$usmap = Get-ChildItem (Join-Path $Travail 'mappings') -Filter 'acr_*.usmap' | Select-Object -First 1
foreach ($f in $retoc, $outil, $paks, $Fiche) { if (-not (Test-Path $f)) { throw "introuvable : $f (faire d'abord l'étape 1, pc\LISEZMOI.md)" } }
if (-not $usmap) { throw "fichier de correspondance absent de $Travail\mappings" }
$env:ACR_USMAP = $usmap.FullName
$env:ACR_GAME_DIR = Join-Path $Travail 'construction\vanilla'

$base = Join-Path $Travail 'unreal\registre'
$legacy = Join-Path $base 'legacy'
$mod = Join-Path $base 'mod'
$dist = Join-Path $Travail 'unreal\dist'
New-Item -ItemType Directory -Force $legacy, $dist | Out-Null
if (-not (Get-ChildItem (Join-Path $legacy 'acr\Content\Data\Database\Main') -Recurse -Filter *.uasset -ErrorAction SilentlyContinue)) {
    & $retoc to-legacy --version UE5_6 --no-shaders --filter 'Data/Database/Main/' $paks $legacy
    if ($LASTEXITCODE -ne 0) { throw "retoc to-legacy en échec" }
}
Remove-Item -Recurse -Force $mod -ErrorAction SilentlyContinue
& $outil registry --legacy $legacy --out $mod $Fiche
if ($LASTEXITCODE -ne 0) { throw "acr-additive registry en échec" }
Remove-Item (Join-Path $dist "$Nom.*") -ErrorAction SilentlyContinue
& $retoc to-zen --version UE5_6 $mod (Join-Path $dist "$Nom.utoc")
if ($LASTEXITCODE -ne 0) { throw "retoc to-zen en échec" }
Write-Host "paquets livrés :"
Get-ChildItem $mod -Recurse -File -Filter *.uasset | ForEach-Object { Write-Host "  $($_.FullName.Substring($mod.Length + 1))" }
Get-ChildItem $dist "$Nom.*" | ForEach-Object { Write-Host ("{0}  ({1:N0} octets)" -f $_.Name, $_.Length) }
Write-Host "Construit, NON installé. À copier dans <jeu>\acr\Content\Paks\~mods\ (jeu fermé, BioBio mis de côté) pour l'essai E2a."
