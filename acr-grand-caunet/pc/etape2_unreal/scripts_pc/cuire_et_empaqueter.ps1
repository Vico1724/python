#Requires -Version 7
<#
.SYNOPSIS
  JAMAIS EXÉCUTÉ. Cuit le projet Unreal « acr » pour Windows, garde seulement NOS éléments (jamais les factices),
  et les empaquette avec retoc en un conteneur IoStore à déposer dans Paks\~mods. N'écrit rien dans le jeu.

  Chaîne : cuisson « par le livre » en fichiers séparés (.uasset/.uexp/.ubulk, comme la sortie « legacy » de
  retoc) -> tri -> retoc to-zen --version UE5_6 (la même commande que leur mods\stage\build.ps1, l.199).
  Documenté : retoc to-zen et ~mods (ACR Extra Stages, docs/load-proof.md, vérifié en jeu).
  Pratique courante, À VÉRIFIER (documentation Epic « Cooking content » sur le PC) : les options de la commande
  de cuisson ci-dessous, en particulier -unversioned (le jeu est cuit sans versions de propriétés :
  docs/acr-stage-anatomy.md d'ACR Extra Stages).

.PARAMETER Inclure  chemins sous Content à livrer (dossiers ou éléments sans extension), p. ex.
                    'GrandCaunet' ou 'Props/RallyProps/Gantries/T_RallyGantryWales_B'
.PARAMETER Cartes   niveaux à cuire (chemins /Game/...), p. ex. '/Game/GrandCaunet/Levels/GC_Essai'
.EXAMPLE
  pwsh -File cuire_et_empaqueter.ps1 -Essai e1a -Inclure 'Props/RallyProps/Gantries/T_RallyGantryWales_B'
#>
param(
    [Parameter(Mandatory)][string]$Essai,
    [Parameter(Mandatory)][string[]]$Inclure,
    [string[]]$Cartes = @(),
    [string]$UE = 'C:\Program Files\Epic Games\UE_5.6',
    [string]$Projet = 'Z:\acrxs\unreal\acr\acr.uproject',
    [string]$Retoc = 'Z:\acrxs\bin\retoc\bin\retoc.exe',
    [string]$Sortie = 'Z:\acrxs\unreal\dist'
)
$ErrorActionPreference = 'Stop'
$kit = Split-Path $PSScriptRoot
$journal = Join-Path $Sortie "cuisson_$Essai.log"
New-Item -ItemType Directory -Force $Sortie | Out-Null
Start-Transcript $journal | Out-Null

# 1. cuisson
$cmd = Join-Path $UE 'Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$a = @($Projet, '-run=cook', '-targetplatform=Windows', '-unversioned', '-unattended', '-nop4', '-utf8output')
if ($Cartes) { $a += "-map=$($Cartes -join '+')" }
foreach ($i in $Inclure) { $a += "-cookdir=$(Join-Path (Split-Path $Projet) "Content\$i")" }
Write-Host "> $cmd $($a -join ' ')"
& $cmd @a
if ($LASTEXITCODE -ne 0) { Stop-Transcript; throw "cuisson en échec ($LASTEXITCODE) : lire $journal" }

# 2. tri : seulement nos chemins, jamais un factice
$cuit = Join-Path (Split-Path $Projet) 'Saved\Cooked\Windows\acr\Content'
$factices = (Get-Content (Join-Path $kit 'factices.json') -Raw | ConvertFrom-Json).factices | ForEach-Object { $_.objet.Substring('/Game/'.Length) }
$tri = Join-Path $Sortie "tri_$Essai"
Remove-Item -Recurse -Force $tri -ErrorAction SilentlyContinue
$n = 0
foreach ($i in $Inclure) {
    $source = Join-Path $cuit $i
    $fichiers = if (Test-Path $source -PathType Container) { Get-ChildItem $source -Recurse -File }
                else { Get-ChildItem "$source.*" -File -ErrorAction SilentlyContinue }
    foreach ($f in $fichiers) {
        $rel = $f.FullName.Substring($cuit.Length + 1)
        $sansExt = ($rel -replace '\.[^.\\]+$', '') -replace '\\', '/'
        if ($factices -contains $sansExt) { Write-Host "  factice écarté : $rel"; continue }
        $d = Join-Path $tri "acr\Content\$rel"
        New-Item -ItemType Directory -Force (Split-Path $d) | Out-Null
        Copy-Item $f.FullName $d
        $n++
    }
}
if ($n -eq 0) { Stop-Transcript; throw "rien à empaqueter : vérifier -Inclure et le dossier $cuit" }
Write-Host "$n fichiers retenus"

# 3. empaquetage IoStore
$nom = "zz_gc_$($Essai.ToLower())_P"
Remove-Item (Join-Path $Sortie "$nom.*") -ErrorAction SilentlyContinue
& $Retoc to-zen --version UE5_6 $tri (Join-Path $Sortie "$nom.utoc")
if ($LASTEXITCODE -ne 0) { Stop-Transcript; throw "retoc to-zen en échec" }
Get-ChildItem $Sortie "$nom.*" | Format-Table Name, Length
Write-Host "À copier dans <jeu>\acr\Content\Paks\~mods\ (jeu fermé), puis à retirer après l'essai."
Stop-Transcript
