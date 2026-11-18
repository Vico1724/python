#Requires -Version 7.2
<#
.SYNOPSIS
  Récupère ACR Extra Stages à la version exacte étudiée, applique nos retouches (pc\patches\*.patch), puis construit
  les outils nécessaires : acr-ref (le constructeur), acr-additive (exigé pour contrôler le fichier de
  correspondance), acr-mappings (production du fichier de correspondance) et retoc (lecture et écriture des
  archives du jeu). NON TESTÉ (écrit sans Windows).

  Documenté par ACR Extra Stages : les commandes de construction (CONTRIBUTING.md, tools/acr-mappings/README.md).
  Rien n'est installé dans le jeu ; tout va dans le dossier de travail (par défaut Z:\acrxs).

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File pc\scripts\2_recuperer_acrxs.ps1
#>
param([string]$Travail, [switch]$Oui)
. "$PSScriptRoot\commun.ps1"
$ErrorActionPreference = 'Stop'   # toute erreur d'une commande PowerShell arrête le script (comme leurs build.ps1)
if (-not $Travail) { $Travail = $script:TravailParDefaut }
New-Item -ItemType Directory -Force $Travail | Out-Null
Start-Journal $Travail '2_recuperer_acrxs'
$env:Path = "$HOME\.cargo\bin;$env:Path"
foreach ($t in 'git', 'dotnet', 'cargo') { if (-not (Test-Commande $t)) { Echec "$t absent : lancer d'abord 1_prerequis.ps1" } }

Etape "Récupération d'ACR Extra Stages, version $($script:CommitAcrXs)"
$src = Get-Source $Travail
if (-not (Test-Path (Join-Path $src '.git'))) {
    # core.autocrlf=false : garder les fins de ligne du dépôt, sinon nos retouches ne s'appliqueraient pas
    Lancer 'git' @('-c', 'core.autocrlf=false', 'clone', $script:DepotAcrXs, $src) "clonage de $($script:DepotAcrXs)"
}
& git -C $src cat-file -e "$($script:CommitAcrXs)^{commit}" 2>$null
if ($LASTEXITCODE -ne 0) {
    Attention "version absente de $($script:DepotAcrXs) ; essai sur le dépôt d'origine $($script:DepotAcrXsAmont)"
    Lancer 'git' @('-C', $src, 'fetch', $script:DepotAcrXsAmont, $script:CommitAcrXs) "récupération de la version étudiée"
}
$etat = (& git -C $src status --porcelain)
if ($etat -and -not ((& git -C $src rev-parse HEAD) -eq $script:CommitAcrXs)) {
    Echec "le dossier $src contient des modifications et n'est pas à la version étudiée : le renommer, puis relancer"
}
Lancer 'git' @('-C', $src, '-c', 'core.autocrlf=false', 'checkout', '--quiet', $script:CommitAcrXs) "passage à la version étudiée"
Ok "ACR Extra Stages à la version $((& git -C $src rev-parse HEAD))"

Etape "Nos retouches (pc\patches)"
# Git pour Windows convertit souvent les fichiers texte en fins de ligne Windows (CRLF) au clonage de notre dépôt ;
# le code d'ACR Extra Stages est en LF : on applique donc une copie LF de chaque retouche.
$patchesLf = Join-Path $Travail 'patches-lf'
New-Item -ItemType Directory -Force $patchesLf | Out-Null
foreach ($p in Get-ChildItem (Join-Path $script:Projet 'pc\patches') -Filter '*.patch' | Sort-Object Name) {
    $pf = Join-Path $patchesLf $p.Name
    [IO.File]::WriteAllText($pf, ((Get-Content -Raw $p.FullName) -replace "`r`n", "`n"))
    & git -C $src apply --reverse --check $pf 2>$null
    if ($LASTEXITCODE -eq 0) { Ok "$($p.Name) déjà appliquée"; continue }
    Lancer 'git' @('-C', $src, 'apply', '--check', $pf) "vérification de $($p.Name)"
    Lancer 'git' @('-C', $src, 'apply', $pf) "application de $($p.Name)"
    Ok "$($p.Name) appliquée"
}

Etape "Construction de acr-ref et acr-additive (kit .NET ; télécharge les bibliothèques depuis nuget.org)"
$bin = Join-Path $Travail 'bin'
Lancer 'dotnet' @('build', (Join-Path $src 'tools\acr-ref\AcrRef.csproj'), '-c', 'Release', '-o', (Join-Path $bin 'acr-ref'), '--nologo', '-v', 'q') "construction de acr-ref"
Lancer 'dotnet' @('publish', (Join-Path $src 'tools\acr-additive\AcrAdditive.csproj'), '-c', 'Release', '-o', (Join-Path $bin 'acr-additive'), '--nologo', '-v', 'q') "construction de acr-additive"
Ok "acr-ref et acr-additive construits dans $bin"

Etape "Construction de retoc (Rust ; plusieurs minutes la première fois)"
$retoc = Join-Path $bin 'retoc\bin\retoc.exe'
if (Test-Path $retoc) { Ok "retoc déjà présent" }
else {
    # Documenté (CONTRIBUTING.md) ; la version de retoc n'est pas figée par leur projet.
    # --locked : respecter le Cargo.lock de retoc. Sans lui, cargo prend la dernière version de la dépendance « jmap »
    # (0.2.0 au 11/11/2026), que retoc 0.1.5 refuse (« jmap = ^0.1.0 ») : constaté sur le PC du directeur.
    Lancer 'cargo' @('install', '--locked', '--git', 'https://github.com/trumank/retoc', 'retoc_cli', '--root', (Join-Path $bin 'retoc')) "construction de retoc"
}

Etape "Construction de acr-mappings (Rust)"
Lancer 'cargo' @('build', '--release', '--manifest-path', (Join-Path $src 'tools\acr-mappings\Cargo.toml')) "construction de acr-mappings"
Ok "outils prêts. Étape suivante : 3_usmap.ps1"
Stop-Journal
