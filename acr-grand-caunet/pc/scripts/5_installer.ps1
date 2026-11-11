#Requires -Version 7
<#
.SYNOPSIS
  Installe le mod construit par 4_construire.ps1 : copie ses 3 fichiers dans <jeu>\acr\Content\Paks\~mods (dossier
  créé s'il n'existe pas). Ne touche à aucun autre fichier du jeu. Demande confirmation. NON TESTÉ.
  Documenté par ACR Extra Stages : un conteneur placé dans Paks\~mods est chargé par le jeu et remplace les paquets
  du même nom (docs/decisions.md D4, vérifié en jeu par eux).

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File pc\scripts\5_installer.ps1
#>
param([string]$Jeu, [string]$Travail, [switch]$Oui)
. "$PSScriptRoot\commun.ps1"
if (-not $Jeu) { $Jeu = $script:JeuParDefaut }
if (-not $Travail) { $Travail = $script:TravailParDefaut }
Start-Journal $Travail '5_installer'
$paks = Get-Paks $Jeu
$dist = Join-Path $Travail 'construction\dist'
$fichiers = @(Get-ChildItem $dist "$($script:NomConteneur).*" -ErrorAction SilentlyContinue)
if ($fichiers.Count -ne 3) { Echec "le mod n'est pas construit ($dist) : lancer 4_construire.ps1" }
if (Test-JeuLance) { Echec "fermer le jeu d'abord" }

Etape "État actuel du dossier Paks (consigné dans le journal)"
Get-ChildItem $paks -Recurse -File | ForEach-Object { "{0,15:N0}  {1}" -f $_.Length, $_.FullName.Substring($paks.Length + 1) } | Out-Host

$mods = Join-Path $paks '~mods'
$etat = Join-Path $Travail 'installation.json'
Etape "Installation dans $mods"
foreach ($f in $fichiers) { Write-Host "  $($f.Name)  ($([math]::Round($f.Length / 1MB, 1)) Mo)" }
if (-not (Confirmer "Copier ces 3 fichiers dans $mods ?" -Oui:$Oui)) { Echec "abandon à la demande" }
$cree = -not (Test-Path $mods)
New-Item -ItemType Directory -Force $mods | Out-Null
foreach ($f in $fichiers) {
    $d = Join-Path $mods $f.Name
    if ((Resolve-Path (Split-Path $d)).Path -ne (Resolve-Path $mods).Path) { Echec "destination inattendue $d" }
    Copy-Item $f.FullName $d -Force
}
@{ jeu = $Jeu; dossier_mods_cree = $cree; fichiers = @($fichiers.Name); date = (Get-Date).ToString('s') } | ConvertTo-Json | Set-Content $etat
Ok "installé. Lancer le jeu (Steam hors ligne), Pays de Galles > Hafren South > variante 1/2, Free Practice."
Write-Host "Pour revenir en arrière : pwsh -ExecutionPolicy Bypass -File pc\scripts\6_desinstaller.ps1"
Stop-Journal
