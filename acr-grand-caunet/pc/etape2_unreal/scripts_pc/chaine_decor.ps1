#Requires -Version 7.2
<#
.SYNOPSIS
  Chaîne complète du décor : paquet -> factices -> import et pose dans Unreal -> cuisson -> relecture.
  N'écrit RIEN dans le jeu : le conteneur cuit reste dans Z:\acrxs\unreal\dist (zz_gc_gc_P.*), à installer ensuite
  avec la route physique (pc\scripts\4_construire.ps1 -Asphalte, puis copie dans ~mods, jeu fermé).

  Étapes :
    1. scripts\16_paquet_unreal.py (sauf -SansPaquet : le paquet vient d'être fabriqué par tout_lancer.py) ;
    2. outils\liste_factices.py puis scripts_editeur\creer_factices.py (matériaux et maillages du jeu, en factices) ;
    3. dossiers Road, Bridges, Props, FarRing, Terrain, Junctions du projet Unreal vidés, cellule du niveau supprimée :
       tout le décor est réimporté ;
    4. scripts_editeur\construire_niveau.py dans l'éditeur (import, variantes, pose, instances) ;
    5. scripts_pc\cuire_et_empaqueter.ps1 ;
    6. outils\relire_decor.py : doit finir par « RELECTURE CONFORME ».
  Durée : 55 à 75 minutes. À ne pas lancer deux fois en même temps, ni refaire le paquet pendant qu'elle tourne.

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File pc\etape2_unreal\scripts_pc\chaine_decor.ps1 -SansPaquet
#>
param([switch]$SansPaquet, [switch]$PrioriteBasse,
      [string]$Projet = 'Z:\acrxs\unreal\acr', [string]$Moteur = 'C:\Program Files\Epic Games\UE_5.6\Engine\Binaries\Win64',
      [string]$Cellule = '1LS8FPM8JIMX697U3QIPKC01K')
$ErrorActionPreference = 'Continue'
if ($PrioriteBasse) { (Get-Process -Id $PID).PriorityClass = 'BelowNormal' }
$env:PYTHONIOENCODING = 'utf-8'
$kit = Split-Path $PSScriptRoot -Parent
$racine = Split-Path (Split-Path $kit -Parent) -Parent
Set-Location $racine
$rep = $racine -replace '\\', '/'
$t0 = Get-Date
function Court([string]$l, [int]$n = 240) { $l.Substring(0, [Math]::Min($n, $l.Length)) }

if (-not $SansPaquet) {
    python scripts\16_paquet_unreal.py 2>&1 | Select-String -Pattern 'Traceback|Error|File "|rocaille|bord de route|fourré|bords ouverts|arbres :|parois rocheuses|"erreurs"|"instances":' |
        ForEach-Object { Court $_.Line }
    if ($LASTEXITCODE -ne 0) { "PAQUET EN ÉCHEC"; "FIN DE LA CHAÎNE"; exit 1 }
}
python pc\etape2_unreal\outils\liste_factices.py 2>&1 | Select-Object -Last 1
if ($LASTEXITCODE -ne 0) { "LISTE DES FACTICES EN ÉCHEC"; "FIN DE LA CHAÎNE"; exit 1 }
& "$Moteur\UnrealEditor-Cmd.exe" "$Projet\acr.uproject" -run=pythonscript "-script=$rep/pc/etape2_unreal/scripts_editeur/creer_factices.py" -unattended -nosplash -nop4 -nullrhi 2>&1 | Out-Null
"creer_factices : code $LASTEXITCODE"
foreach ($d in 'Road', 'Bridges', 'Props', 'FarRing', 'Terrain', 'Junctions') {
    $p = "$Projet\Content\Environments\GrandCaunet\$d"
    if (Test-Path $p) { [IO.Directory]::Delete($p, $true) }
}
$rapport = "$Projet\Saved\GrandCaunet\construire_niveau_complet.json"
foreach ($f in "$Projet\Content\Levels\WalesS4HafrenSouth\_Generated_\$Cellule.umap", $rapport) { if (Test-Path $f) { [IO.File]::Delete($f) } }
& "$Moteur\UnrealEditor.exe" "$Projet\acr.uproject" "-ExecutePythonScript=$rep/pc/etape2_unreal/scripts_editeur/construire_niveau.py --manifeste $rep/paquet_unreal/manifeste.json --etendue complet --parent jeu --placement $rep/pc/etape2_unreal/releves/placement_etape1.json --niveau /Game/Levels/WalesS4HafrenSouth/_Generated_/$Cellule --sans-eclairage --quitter" -unattended -nosplash -nop4 2>&1 | Out-Null
"éditeur : code $LASTEXITCODE"
if (-not (Test-Path $rapport)) { "PAS DE RAPPORT DE CONSTRUCTION"; "FIN DE LA CHAÎNE"; exit 1 }
$r = Get-Content $rapport -Raw -Encoding utf8 | ConvertFrom-Json
"construction : $($r.maillages) maillages, $($r.variantes) variantes, $($r.acteurs) acteurs, $($r.instances) instances ; bornes différentes : $(@($r.verdicts_bornes.differents).Count) ; alertes : $(@($r.alertes).Count)"
@($r.alertes) | Select-Object -First 12 | ForEach-Object { "  alerte : " + (Court "$_") }
pwsh -Command "& '$kit\scripts_pc\cuire_et_empaqueter.ps1' -Essai gc -Versionne -Inclure 'Environments/GrandCaunet','Levels/WalesS4HafrenSouth' -Cartes '/Game/Levels/WalesS4HafrenSouth/_Generated_/$Cellule'" 2>&1 | Select-Object -Last 4
python pc\etape2_unreal\outils\relire_decor.py 2>&1 | Select-String -Pattern '"erreurs"|RELECTURE' -Context 0, 6 |
    ForEach-Object { $_.Line; $_.Context.PostContext } | Select-Object -Last 16 | ForEach-Object { Court "$_" 300 }
"durée totale : $([int]((Get-Date) - $t0).TotalMinutes) min"
"FIN DE LA CHAÎNE"
