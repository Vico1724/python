#Requires -Version 7.2
<#
.SYNOPSIS
  Bascule du Grand Caunet vers la Montée de Ceyreste. NON TESTÉ (écrit sans Windows ni le jeu).
  Les deux cartes remplacent la même variante hôte (Hafren South 1/2), la même table des variantes et la même cellule
  de décor : elles ne peuvent pas être installées ensemble (docs/ETAT.md). Ce script :
    1. met de côté les conteneurs du Grand Caunet présents dans <jeu>\acr\Content\Paks\~mods (zz_acrxs_grandcaunet_P,
       zz_acrxs_grandcaunet_table_9_P, zz_gc_gc_P) : COPIE dans <atelier>\bascule\grand_caunet_<date>\, contrôle des
       empreintes SHA-256, puis seulement alors retrait de ~mods ; un fichier bascule.json décrit la sauvegarde ;
    2. installe les conteneurs de la montée trouvés dans l'atelier de la montée (route physique et table :
       construction\dist ; décor : unreal\dist).
  Rien n'est jamais supprimé sans copie vérifiée. Retour : bascule_vers_grand_caunet.ps1.
.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File pc\scripts\bascule_vers_ceyreste.ps1 [-SansDecor] [-Oui]
#>
param([string]$Jeu, [string]$Travail, [switch]$SansDecor, [switch]$Oui)
. "$PSScriptRoot\commun.ps1"
$ErrorActionPreference = 'Stop'
if (-not $Jeu) { $Jeu = $script:JeuParDefaut }
if (-not $Travail) { $Travail = $script:TravailParDefaut }
Start-Journal $Travail 'bascule_vers_ceyreste'
Assert-Jeu $Jeu
if (Test-JeuLance) { Echec "fermer le jeu d'abord" }
$mods = Join-Path (Get-Paks $Jeu) '~mods'

Etape "Conteneurs de la montée à installer"
$sources = @((Join-Path $Travail 'construction\dist'), (Join-Path $Travail 'unreal\dist'))
$noms = if ($SansDecor) { $script:ConteneursCeyreste[0..1] } else { $script:ConteneursCeyreste }
$aPoser = @(foreach ($n in $noms) { foreach ($s in $sources) { Get-ChildItem $s "$n.*" -ErrorAction SilentlyContinue } })
if (-not ($aPoser | Where-Object { $_.BaseName -eq $script:NomConteneur })) { Echec "route physique de la montée absente : lancer 4_construire.ps1" }
$aPoser | ForEach-Object { Write-Host ("  {0}  ({1:N1} Mo)" -f $_.FullName, ($_.Length / 1MB)) }

Etape "Conteneurs du Grand Caunet à mettre de côté"
$gc = @(foreach ($n in $script:ConteneursGrandCaunet) { Get-ChildItem $mods "$n.*" -ErrorAction SilentlyContinue })
if (-not $gc) { Ok "aucun dans $mods" } else { $gc | ForEach-Object { Write-Host "  $($_.FullName)" } }
if (-not (Confirmer "Mettre de côté ces fichiers et installer la montée ?" -Oui:$Oui)) { Echec "abandon à la demande" }

if ($gc) {
    $dos = Join-Path $Travail ("bascule\grand_caunet_{0}" -f (Get-Date -Format 'yyyyMMdd_HHmmss'))
    New-Item -ItemType Directory -Force $dos | Out-Null
    $liste = @()
    foreach ($f in $gc) {
        $d = Join-Path $dos $f.Name
        Copy-Item -LiteralPath $f.FullName $d
        $h1 = (Get-FileHash -LiteralPath $f.FullName -Algorithm SHA256).Hash
        $h2 = (Get-FileHash -LiteralPath $d -Algorithm SHA256).Hash
        if ($h1 -ne $h2) { Echec "copie de $($f.Name) différente de l'original : rien n'est retiré" }
        $liste += @{ nom = $f.Name; sha256 = $h1; taille = $f.Length }
    }
    @{ de = $mods; date = (Get-Date).ToString('s'); fichiers = $liste } | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $dos 'bascule.json') -Encoding utf8
    Ok "copie vérifiée : $dos"
    $gc | Remove-Item -Force
    Ok "Grand Caunet retiré de ~mods (copie dans $dos)"
}
New-Item -ItemType Directory -Force $mods | Out-Null
foreach ($f in $aPoser) { Copy-Item -LiteralPath $f.FullName (Join-Path $mods $f.Name) -Force }
Ok "montée installée : $($aPoser.Name -join ', ')"
Ok "En jeu : Pays de Galles > Hafren South > variante 1/2 > Essais libres, Steam hors ligne, adhérence de départ « Optimale »."
Write-Host "Retour au Grand Caunet : pwsh -ExecutionPolicy Bypass -File pc\scripts\bascule_vers_grand_caunet.ps1"
Stop-Journal
