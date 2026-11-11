# commun.ps1 - réglages et fonctions partagés par les scripts du kit (à « dot-sourcer » : . "$PSScriptRoot\commun.ps1").
#
# NON TESTÉ : ces scripts ont été écrits sur un serveur Linux, sans Windows ni le jeu. Ils n'ont jamais été exécutés.
# Ils sont prudents : ils n'écrivent jamais dans les archives d'origine du jeu (seulement dans Paks\~mods, et seulement
# après confirmation), et ils consignent tout dans un journal.
#
# Compatible Windows PowerShell 5.1 (pour 1_prerequis.ps1, qui installe PowerShell 7) et PowerShell 7.

# --- valeurs par défaut (modifiables par paramètre dans chaque script) -----------------------------------------------
$script:JeuParDefaut = 'Z:\Steamlibrary\steamapps\common\Assetto Corsa Rally'   # jeu du directeur
# Dossier de travail : il DOIT être sur le même disque que le jeu (Z:), car leur outil crée des « liens physiques »
# (hard links) vers les archives du jeu au lieu de les copier, et un lien physique ne traverse pas les disques.
$script:TravailParDefaut = 'Z:\acrxs'
$script:DepotAcrXs = 'https://github.com/nitnerolf420/acr-extrastages'           # dépôt étudié (licences MIT / Apache-2.0)
$script:DepotAcrXsAmont = 'https://github.com/cherrymcgerry/acr-extrastages'     # dépôt d'origine, si le premier manque
$script:CommitAcrXs = '1324f07d35549a24bd7d2f7d11fe7faaf3e44265'                 # version exacte étudiée (31/10/2026)
$script:BuildJeu = '25170642'                                                    # version du jeu visée
$script:IdSpeciale = 'grand_caunet_rally_01_route_0'                             # identifiant du dossier d'échange
$script:NomConteneur = 'zz_acrxs_grandcaunet_P'                                  # nom des 3 fichiers du mod
$script:Projet = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path           # racine du dépôt acr-grand-caunet

# --- journal ----------------------------------------------------------------------------------------------------------
function Start-Journal([string]$Travail, [string]$Nom) {
    $dir = Join-Path $Travail 'journal'
    New-Item -ItemType Directory -Force $dir | Out-Null
    $script:Journal = Join-Path $dir ("{0}_{1}.log" -f $Nom, (Get-Date -Format 'yyyyMMdd_HHmmss'))
    Start-Transcript -Path $script:Journal -Append | Out-Null
    Write-Host "Journal : $script:Journal"
}

function Stop-Journal { try { Stop-Transcript | Out-Null } catch { } }

function Etape([string]$texte) { Write-Host ""; Write-Host "=== $texte ===" -ForegroundColor Cyan }
function Ok([string]$texte) { Write-Host "  OK   $texte" -ForegroundColor Green }
function Attention([string]$texte) { Write-Host "  ATTENTION  $texte" -ForegroundColor Yellow }
function Echec([string]$texte) { Write-Host "  ÉCHEC $texte" -ForegroundColor Red; Stop-Journal; throw $texte }

# Lance un programme, recopie sa sortie à l'écran et dans le journal, et s'arrête s'il échoue.
function Lancer([string]$exe, [string[]]$arguments, [string]$quoi) {
    Write-Host "  > $exe $($arguments -join ' ')" -ForegroundColor DarkGray
    # la sortie passe par l'hôte PowerShell, donc aussi par le journal (Start-Transcript)
    & $exe @arguments 2>&1 | ForEach-Object { "$_" } | Out-Host
    if ($LASTEXITCODE -ne 0) { Echec "$quoi (code de sortie $LASTEXITCODE ; voir le journal $script:Journal)" }
}

# Demande une confirmation explicite (o / n). -Oui sur la ligne de commande la donne d'avance.
function Confirmer([string]$question, [switch]$Oui) {
    if ($Oui) { return $true }
    $r = Read-Host "$question [o/n]"
    return $r -match '^(o|oui|y|yes)$'
}

function Test-Commande([string]$nom) { return [bool](Get-Command $nom -ErrorAction SilentlyContinue) }

# Le jeu tourne-t-il ? (mêmes noms de processus que leur lanceur, tools/launcher/Preflight.cs)
function Test-JeuLance { return (Get-Process -Name 'acr', 'acr-Win64-Shipping' -ErrorAction SilentlyContinue).Count -gt 0 }

# Version de construction du jeu, lue dans steamapps\appmanifest_3917090.acf (deux niveaux au-dessus du jeu).
function Get-BuildJeu([string]$Jeu) {
    $acf = Join-Path (Split-Path (Split-Path $Jeu)) 'appmanifest_3917090.acf'
    if (-not (Test-Path $acf)) { return $null }
    $m = Select-String -Path $acf -Pattern '"buildid"\s+"(\d+)"' | Select-Object -First 1
    if ($m) { return $m.Matches[0].Groups[1].Value } else { return $null }
}

function Get-Source([string]$Travail) { Join-Path $Travail 'acr-extrastages' }
function Get-Usmap([string]$Travail) { Join-Path $Travail "mappings\acr_$($script:BuildJeu).usmap" }
function Get-Paks([string]$Jeu) { Join-Path $Jeu 'acr\Content\Paks' }
