#Requires -Version 7.2
<#
.SYNOPSIS
  Bascule de la Montée de Ceyreste vers le Grand Caunet. NON TESTÉ (écrit sans Windows ni le jeu).
    1. retire de <jeu>\acr\Content\Paks\~mods les conteneurs de la montée (ils restent dans l'atelier de la montée) ;
    2. remet les conteneurs du Grand Caunet mis de côté par bascule_vers_ceyreste.ps1 (sauvegarde la plus récente de
       <atelier>\bascule\, ou celle donnée par -Sauvegarde), en vérifiant leurs empreintes SHA-256 ; la sauvegarde
       est gardée. N'écrit rien d'autre ; ne reconstruit rien du Grand Caunet.
.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File pc\scripts\bascule_vers_grand_caunet.ps1 [-Sauvegarde <dossier>] [-Oui]
#>
param([string]$Jeu, [string]$Travail, [string]$Sauvegarde, [switch]$Oui)
. "$PSScriptRoot\commun.ps1"
$ErrorActionPreference = 'Stop'
if (-not $Jeu) { $Jeu = $script:JeuParDefaut }
if (-not $Travail) { $Travail = $script:TravailParDefaut }
Start-Journal $Travail 'bascule_vers_grand_caunet'
Assert-Jeu $Jeu
if (Test-JeuLance) { Echec "fermer le jeu d'abord" }
$mods = Join-Path (Get-Paks $Jeu) '~mods'
if (-not $Sauvegarde) {
    $Sauvegarde = Get-ChildItem (Join-Path $Travail 'bascule') -Directory -Filter 'grand_caunet_*' -ErrorAction SilentlyContinue |
        Sort-Object Name | Select-Object -Last 1 -ExpandProperty FullName
}
$b = if ($Sauvegarde) { Join-Path $Sauvegarde 'bascule.json' }
if (-not $b -or -not (Test-Path $b)) { Attention "aucune sauvegarde du Grand Caunet : seule la montée sera retirée" }

$cey = @(foreach ($n in $script:ConteneursCeyreste) { Get-ChildItem $mods "$n.*" -ErrorAction SilentlyContinue })
$cey | ForEach-Object { Write-Host "  à retirer : $($_.FullName)" }
if (-not (Confirmer "Retirer la montée et remettre le Grand Caunet ?" -Oui:$Oui)) { Echec "abandon à la demande" }
$cey | Remove-Item -Force
Ok "montée retirée de ~mods"
if ($b -and (Test-Path $b)) {
    $j = Get-Content $b -Raw | ConvertFrom-Json
    foreach ($f in $j.fichiers) {
        $src = Join-Path $Sauvegarde $f.nom
        if ((Get-FileHash -LiteralPath $src -Algorithm SHA256).Hash -ne $f.sha256) { Echec "sauvegarde altérée : $src" }
        $d = Join-Path $mods $f.nom
        Copy-Item -LiteralPath $src $d -Force
        if ((Get-FileHash -LiteralPath $d -Algorithm SHA256).Hash -ne $f.sha256) { Echec "copie altérée : $d" }
    }
    Ok "Grand Caunet remis à l'identique ($($j.fichiers.Count) fichiers) ; sauvegarde gardée : $Sauvegarde"
}
Stop-Journal
