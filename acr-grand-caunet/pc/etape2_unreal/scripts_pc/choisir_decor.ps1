#Requires -Version 7.2
<#
.SYNOPSIS
  Installe dans <jeu>\acr\Content\Paks\~mods l'une des versions du décor gardées dans Z:\acrxs\unreal\dist :
    sol_jeu              version courante (sixième du 13/11/2026) : parois rocheuses relues sur la reconnaissance,
                         rocaille en pierres calcaires, feuillages verts, accotement d'herbe, pins de bord de route ;
                         jamais vue en jeu
    sol_jeu_cycle5_du_13_11  cinquième version : carrefour du Lion d'Or repris, versants boisés, roche sur les
                         falaises, spéciale classée en asphalte ; seul le menu (pneus asphalte) en a été vu en jeu
    sol_jeu_vu_le_13_11_ter  quatrième version, vue en jeu le 13/11/2026 au soir : lignes blanches rétablies, bords
                         d'enrobé nets, arbres du bord choisis d'après leur forme mesurée, roche à l'échelle du jeu
    sol_jeu_vu_le_13_11_bis  troisième version, vue en jeu le 13/11/2026 après-midi : parois rocheuses sur le relief,
                         versants lointains verts ; lignes blanches absentes, bords en zigzag, arbres qui débordent
    sol_jeu_cycle1_du_13_11  première version faite après l'essai du 13/11/2026 au matin ; jamais vue en jeu
    sol_jeu_vu_le_13_11  celle que le directeur a vue en jeu le 13/11/2026 : falaises du massif, rochers de bord de
                         route, panneaux routiers, lisses en bois, rubalises et panneaux du rallye (12/11/2026, nuit)
    sol_jeu_releve_reco  bords repris d'après la vidéo des reconnaissances (glissières, parapets, murs, parois
                         rocheuses, 96 poteaux relevés, arbres de bord ; 12/11/2026, 17 h) ; jamais vue en jeu
    sol_jeu_avant_releve_reco  la suivante, plus les poteaux estimés et leurs câbles, les panneaux du rallye, les
                         barrières, la haie et les murs de l'ancien relevé (12/11/2026, 16 h) ; jamais vue en jeu
    sol_jeu_sans_mobilier  chaussée corrigée aux ponts, parapets bas en pierre et en béton, sol éclairci, lointain
                         éclairci (12/11/2026, 15 h) ; jamais vue en jeu
    sol_jeu_vu_le_12_11  celle que le directeur a vue en jeu le 12/11/2026 au matin, avec ses défauts
    sol_photo_plus       la même que la précédente, mais avec l'ancien sol portant la photo aérienne
    sol_photo            sol en photo, nos glissières, pas d'herbes (décor vu en jeu le 11/11/2026, tracé régularisé)
  Sans -Decor : liste les versions disponibles et dit laquelle est installée. Chaque version est gardée avec le mod
  de l'étape 1 (route physique) qui va avec elle : le script installe les deux conteneurs ensemble, pour que route
  visible et route physique restent superposées. Jeu fermé obligatoirement.

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
$lot = @(Get-ChildItem $choix.FullName 'zz_*_P.*')          # le décor et, s'il est rangé avec lui, le mod de l'étape 1
foreach ($f in $lot) { Copy-Item $f.FullName (Join-Path $mods $f.Name) -Force }
if (-not ($lot.Name -like 'zz_acrxs_*')) { Attention "cette version n'a pas de mod de l'étape 1 rangé avec elle : celui en place est gardé" }
Ok "décor « $Decor » installé ($($lot.Count) fichiers). Lancer le jeu (Steam hors ligne), Pays de Galles > Hafren South, Free Practice."
