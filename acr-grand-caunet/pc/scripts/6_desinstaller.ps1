#Requires -Version 7.2
<#
.SYNOPSIS
  Désinstalle le mod d'essai : supprime nos 3 fichiers de Paks\~mods, et le dossier ~mods s'il a été créé par
  5_installer.ps1 et qu'il est vide. Ne touche à rien d'autre (ni à BioBio, ni aux archives d'origine). NON TESTÉ.
  Le jeu redevient alors exactement celui d'avant l'installation.

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File pc\scripts\6_desinstaller.ps1
#>
param([string]$Jeu, [string]$Travail, [switch]$Oui)
. "$PSScriptRoot\commun.ps1"
$ErrorActionPreference = 'Stop'
if (-not $Jeu) { $Jeu = $script:JeuParDefaut }
if (-not $Travail) { $Travail = $script:TravailParDefaut }
Start-Journal $Travail '6_desinstaller'
Assert-Jeu $Jeu                                   # chemin faux : ne rien conclure, ne rien effacer (pas même installation.json)
if (Test-JeuLance) { Echec "fermer le jeu d'abord" }
$mods = Join-Path (Get-Paks $Jeu) '~mods'
$a = @(Get-ChildItem $mods "$($script:NomConteneur).*" -ErrorAction SilentlyContinue)
if (-not $a) { Ok "rien à désinstaller dans $mods" }
else {
    $a | ForEach-Object { Write-Host "  $($_.FullName)" }
    if (-not (Confirmer "Supprimer ces fichiers ?" -Oui:$Oui)) { Echec "abandon à la demande" }
    $a | Remove-Item -Force
    Ok "fichiers supprimés"
}
$etat = Join-Path $Travail 'installation.json'
if ((Test-Path $etat) -and (Get-Content $etat -Raw | ConvertFrom-Json).dossier_mods_cree -and (Test-Path $mods) -and
    -not (Get-ChildItem $mods -Force)) {
    Remove-Item $mods
    Ok "dossier ~mods (créé par l'installation, vide) supprimé"
}
Remove-Item $etat -ErrorAction SilentlyContinue
Ok "jeu revenu à l'état d'avant l'installation"
Stop-Journal
