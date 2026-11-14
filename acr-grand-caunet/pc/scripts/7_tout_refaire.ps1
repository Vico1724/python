#Requires -Version 7.2
<#
.SYNOPSIS
  Refait tout d'un trait, des données au décor cuit : étapes Python, route physique, chaîne Unreal, relecture.
  N'écrit RIEN dans le jeu : à la fin, les fichiers sont dans Z:\acrxs\construction\dist (route physique, table) et
  Z:\acrxs\unreal\dist (décor) ; l'installation reste une étape à part (jeu fermé).

  Ordre, et pourquoi :
    1. scripts\tout_lancer.py --seulement 8 11 12 10 9 13, puis 11 14 150 16 (la seconde passe reprend 11 après 12) ;
    2. pc\scripts\4_construire.ps1 -Asphalte (route physique ; refusée si le jeu tourne : la chaîne continue sans elle
       et le signale) puis outils\relever_placement.py : le décor se pose dans le repère de la route physique, il faut
       donc ce relevé AVANT la pose. Si le placement a bougé, il est simplement repris par la pose qui suit ;
    3. pc\etape2_unreal\scripts_pc\chaine_decor.ps1 -SansPaquet (55 à 75 minutes).
  À lancer après scripts\07b_regulariser_chaussee.py si la route a changé. Journal : -Journal.

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File pc\scripts\7_tout_refaire.ps1 -Journal C:\tmp\v8.log
#>
param([string]$Journal = (Join-Path $env:TEMP 'grand_caunet_tout_refaire.log'))
$ErrorActionPreference = 'Continue'
$env:PYTHONIOENCODING = 'utf-8'
$racine = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $racine
$t0 = Get-Date
function Court([string]$l, [int]$n = 240) { $l.Substring(0, [Math]::Min($n, $l.Length)) }
"=== première passe" | Set-Content $Journal -Encoding utf8
python scripts\tout_lancer.py --seulement 8 11 12 10 9 13 --sans-rendus *>> $Journal
if ($LASTEXITCODE -ne 0) { "DONNÉES EN ÉCHEC (première passe) : voir $Journal"; "FIN"; exit 1 }
"=== seconde passe" | Add-Content $Journal -Encoding utf8
python scripts\tout_lancer.py --seulement 11 14 150 16 *>> $Journal
if ($LASTEXITCODE -ne 0) { "DONNÉES EN ÉCHEC (seconde passe) : voir $Journal"; "FIN"; exit 1 }
Select-String -Path $Journal -Pattern 'Traceback|rocaille :|herbes :|bord de route :|fourré|bords ouverts|arbres :|parois rocheuses|falaises des versants|versants :|"instances":|obstacles :|attention :' |
    Select-Object -Last 16 | ForEach-Object { Court $_.Line }
"données : $([int]((Get-Date) - $t0).TotalMinutes) min"
if (Get-Process -Name 'acr', 'acr-Win64-Shipping' -ErrorAction SilentlyContinue) {
    "ROUTE PHYSIQUE NON CONSTRUITE : le jeu tourne (à refaire jeu fermé : pc\scripts\4_construire.ps1 -Asphalte)"
} else {
    $j1 = [IO.Path]::ChangeExtension($Journal, '.etape1.log')
    pwsh -ExecutionPolicy Bypass -Command "& 'pc\scripts\4_construire.ps1' -Noms -Ciel -Asphalte -CellulesDecor '1LS8FPM8JIMX697U3QIPKC01K' -ExclureVisuels 'Z:\acrxs\unreal\hybride\zones_complet.json'" *> $j1
    "route physique : code $LASTEXITCODE ; lignes FAIL : $((Select-String -Path $j1 -Pattern '^FAIL|ÉCHEC' | Measure-Object).Count)"
    Select-String -Path $j1 -Pattern 'notre conteneur passe devant|autres identiques|^FAIL|ÉCHEC' | Select-Object -Last 4 | ForEach-Object { Court $_.Line }
    python pc\etape2_unreal\outils\relever_placement.py 2>&1 | Select-Object -Last 2 | ForEach-Object { Court "$_" }
}
pwsh -ExecutionPolicy Bypass -File pc\etape2_unreal\scripts_pc\chaine_decor.ps1 -SansPaquet 2>&1
"durée de tout : $([int]((Get-Date) - $t0).TotalMinutes) min"
"FIN"
