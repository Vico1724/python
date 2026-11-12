#Requires -Version 7.2
<#
.SYNOPSIS
  Installe dans <jeu>\acr\Content\Paks\~mods l'une des versions du décor gardées dans Z:\acrxs\unreal\dist :
    sol_jeu    sol habillé par le matériau de terrain du jeu, herbes et glissières du jeu (12/11/2026)
    sol_photo  sol portant la photo aérienne, nos glissières, pas d'herbes (version vue en jeu le 11/11/2026,
               sur le tracé régularisé)
  Sans -Decor : liste les versions disponibles et dit laquelle est installée. Ne touche qu'aux trois fichiers
  zz_gc_gc_P.* de ~mods ; le mod de l'étape 1 (route physique) reste en place, il est le même pour les deux versions.
  Jeu fermé obligatoirement.

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File pc\etape2_unreal\scripts_pc\choisir_decor.ps1
  pwsh -ExecutionPolicy Bypass -File pc\etape2_unreal\scripts_pc\choisir_decor.ps1 -Decor sol_photo
#>
param([string]$Decor, [string]$Jeu, [string]$Dist = 'Z:\acrxs\unreal\dist', [string]$Nom = 'zz_gc_gc_P', [switch]$Oui)
. "$PSScriptRoot\..\..\scripts\commun.ps1"
$ErrorActionPreference = 'Stop'
if (-not $Jeu) { $Jeu = $script:JeuParDefaut }
Assert-Jeu $Jeu
$mods = Join-Path (Get-Paks $Jeu) '~mods'

$versions = @(Get-ChildItem $Dist -Directory | Where-Object { @(Get-ChildItem $_.FullName "$Nom.*").Count -eq 3 })
$installe = Get-Item (Join-Path $mods "$Nom.ucas") -ErrorAction SilentlyContinue
Etape "Versions du décor disponibles dans $Dist"
foreach ($v in $versions) {
    $u = Get-Item (Join-Path $v.FullName "$Nom.ucas")
    $ici = $installe -and $installe.Length -eq $u.Length -and $installe.LastWriteTime -eq $u.LastWriteTime
    Write-Host ("  {0,-10} {1,6:N0} Mo, du {2:dd/MM/yyyy HH:mm}{3}" -f $v.Name, ($u.Length / 1MB), $u.LastWriteTime, $(if ($ici) { '   <- installée' } else { '' }))
}
if (-not $installe) { Write-Host "  aucun décor n'est installé dans $mods" }
if (-not $Decor) { return }

$choix = $versions | Where-Object Name -eq $Decor
if (-not $choix) { Echec "version inconnue : $Decor (disponibles : $($versions.Name -join ', '))" }
if (Test-JeuLance) { Echec "fermer le jeu d'abord" }
if (-not (Confirmer "Installer le décor « $Decor » dans $mods ?" -Oui:$Oui)) { Echec "abandon à la demande" }
New-Item -ItemType Directory -Force $mods | Out-Null
foreach ($f in Get-ChildItem $choix.FullName "$Nom.*") { Copy-Item $f.FullName (Join-Path $mods $f.Name) -Force }
Ok "décor « $Decor » installé. Lancer le jeu (Steam hors ligne), Pays de Galles > Hafren South, Free Practice."
