#Requires -Version 7.2
<#
.SYNOPSIS
  Construit le mod d'essai à partir de notre dossier d'échange (export\stage_ir\grand_caunet), avec le constructeur
  d'ACR Extra Stages retouché, puis le contrôle hors du jeu. N'écrit RIEN dans le jeu (voir 5_installer.ps1).
  NON TESTÉ (écrit sans Windows ni le jeu).

  Voie retenue : celle de leur script mods\stage\build.ps1 (« remplacement » de la variante 1/2 de Hafren South,
  Pays de Galles), reproduite ici étape par étape parce que ce script ne sait pas agrandir le monde physique
  (--bounds) ; nos options :
    --bounds 1          agrandit la zone physique de l'hôte (notre route la dépasse de ~45 m)  [déduit du code]
    --keep-variants 1   ne livre pas la table de menus DT_TracksVariants (retouche 0001) : pas de conflit avec BioBio
    --objects ...       nos parapets, murets et balisage (s'il y en a dans stage.json)
    --scenery ...       cache le décor de Hafren South (sauf avec -GarderDecor)
  Ce que fait chaque étape est cité de mods\stage\build.ps1 (lignes indiquées).

.PARAMETER Textures   sol et route avec les matériaux texturés de Hafren (gravier gallois) au lieu des couleurs unies
.PARAMETER Noms       renomme la variante en « Le Grand Caunet » (table de textes ST_Track, livrée en entier)
.PARAMETER Longueur   écrit 6,74 km dans le menu (livre DT_TracksVariants : INCOMPATIBLE avec BioBio installé)
.PARAMETER Ciel       ciel réglé sur la latitude de Monte-Carlo (section [france] de leur config\sky.toml)
.PARAMETER GarderDecor  ne cache pas le décor gallois
.PARAMETER SansObstacles  n'ajoute pas les parapets / balisage

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File pc\scripts\4_construire.ps1
#>
param(
    [string]$Jeu, [string]$Travail, [string]$Ir,
    [string[]]$CellulesDecor = @(),
    [switch]$Textures, [switch]$Noms, [switch]$Longueur, [switch]$Ciel, [switch]$GarderDecor, [switch]$SansObstacles
)
. "$PSScriptRoot\commun.ps1"
$ErrorActionPreference = 'Stop'
if (-not $Jeu) { $Jeu = $script:JeuParDefaut }
if (-not $Travail) { $Travail = $script:TravailParDefaut }
if (-not $Ir) { $Ir = Join-Path $script:Projet 'export\stage_ir\grand_caunet' }
Start-Journal $Travail '4_construire'
Assert-Jeu $Jeu
$src = Get-Source $Travail
$bin = Join-Path $Travail 'bin'
$acrRef = Join-Path $bin 'acr-ref\acr-ref.exe'
$retoc = Join-Path $bin 'retoc\bin\retoc.exe'
$usmap = Get-Usmap $Travail
foreach ($f in $acrRef, $retoc) { if (-not (Test-Path $f)) { Echec "$f absent : lancer 2_recuperer_acrxs.ps1" } }
if (-not (Test-Path $usmap)) { Echec "fichier de correspondance absent ($usmap) : lancer 3_usmap.ps1" }
if (Test-JeuLance) { Echec "fermer le jeu d'abord" }
$env:ACR_USMAP = $usmap
$env:ACR_GAME_DIR = $Jeu
if (-not (Test-Path (Join-Path $src 'mods\common\vanilla.ps1'))) { Echec "ACR Extra Stages absent de $src : lancer 2_recuperer_acrxs.ps1" }
. (Join-Path $src 'mods\common\vanilla.ps1')

Etape "Notre dossier d'échange"
foreach ($f in 'stage.json', 'collision.glb') { if (-not (Test-Path (Join-Path $Ir $f))) { Echec "$f absent de $Ir" } }
$stage = Get-Content (Join-Path $Ir 'stage.json') -Raw | ConvertFrom-Json
if ($stage.id -ne $script:IdSpeciale) { Echec "identifiant inattendu : $($stage.id)" }
$irTravail = Join-Path $src "work\ir\$($script:IdSpeciale)"
Remove-Item -Recurse -Force $irTravail -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $irTravail | Out-Null
Copy-Item (Join-Path $Ir '*') $irTravail -Recurse
$obstacles = (-not $SansObstacles) -and ($null -ne $stage.objects)
Ok ("{0} : {1:N0} m chronométrés, {2} portes, {3} notes, {4}" -f $stage.name, $stage.length_m, $stage.gates.Count,
    $stage.pacenotes.tokens.Count, $(if ($obstacles) { "$($stage.objects.instances.Count) obstacles" } else { "sans obstacles" }))

Etape "Vue « d'origine » des archives du jeu (liens physiques ; les mods, BioBio compris, sont laissés de côté)"
# build.ps1 l.102-105 : toutes les lectures du jeu passent par cette vue
$work = Join-Path $Travail 'construction'
$vanilla = New-VanillaView $Jeu (Join-Path $work 'vanilla')
$paks = Join-Path $vanilla 'acr\Content\Paks'

Etape "Extraction des paquets de la spéciale hôte (retoc to-legacy)"
# build.ps1 l.112-134 : mêmes paquets, même filtre
$hote = [ordered]@{
    baked      = 'acr\Content\Environments\WalesS4HafrenSouth\DataAssets\DA_WalesS4HafrenSouthBakedData'
    cell       = 'acr\Content\Levels\WalesS4HafrenSouth\_Generated_\22VG0QIP9ATUQI633K86KWPFP'
    variants   = 'acr\Content\Data\Database\Main\TrackSelection\DT_TracksVariants'
    pacenote   = 'acr\Content\Data\Pacenote\Tables\DT_PacenoteHafrenSouthForward'
    persistent = 'acr\Content\Levels\WalesS4HafrenSouth'
    strings    = 'acr\Content\Data\Localization\ContentTexts\ST_Track'
}
$filtre = @{ persistent = 'WalesS4HafrenSouth.umap' }
$legacy = Join-Path $work 'legacy-vanilla'
if (-not (Test-VanillaStamp $legacy)) { Remove-Item -Recurse -Force $legacy -ErrorAction SilentlyContinue }
foreach ($k in $hote.Keys) {
    if (Test-Path (Join-Path $legacy "$($hote[$k]).uexp")) { continue }
    Assert-VanillaPaks $paks
    $f = if ($filtre[$k]) { $filtre[$k] } else { Split-Path $hote[$k] -Leaf }
    Lancer $retoc @('to-legacy', '--version', 'UE5_6', '--no-shaders', '--filter', $f, $paks, $legacy) "extraction de $k"
}
Write-VanillaStamp $legacy $paks
Ok "paquets extraits dans $legacy"

Etape "Registre des surfaces du jeu et contrôle de leur table des surfaces"
# build.ps1 l.138-143
$registre = Join-Path $legacy 'DA_PhysMaterialsMappingCommon.json'
if (-not (Test-Path $registre)) {
    Lancer $acrRef @('export', 'acr/Content/Data/Gameplay/PhysicalMaterials/DA_PhysMaterialsMappingCommon.uasset', '--game', $vanilla, '--usmap', $usmap, '--out', $registre) "lecture du registre des surfaces"
}
Lancer $acrRef @('surface-map-check', '--map', (Join-Path $src 'config\surface-map.toml'), '--registry', $registre, '--usmap', $usmap) "contrôle de config\surface-map.toml"

Etape "Construction (acr-ref stage-build)"
$mod = Join-Path $work 'mod'
$rapport = Join-Path $work 'stage-grandcaunet.report.json'
Remove-Item -Recurse -Force $mod -ErrorAction SilentlyContinue
$cfg = Join-Path $src 'config'
$a = @('stage-build', '--ir', $irTravail, '--legacy', $legacy, '--out', $mod, '--report', $rapport, '--surface-registry', $registre,
       '--game', $vanilla, '--usmap', $usmap,
       '--bounds', '1',                                                             # monde agrandi (Bounds.cs)
       '--pacenote-map', (Join-Path $cfg 'pacenote-map.toml'), '--pacenote-report', (Join-Path $work 'notes-grandcaunet.md'),
       '--respawn', 'relay',                                                        # build.ps1 l.165 (v1.3+)
       '--visuals', (Join-Path $cfg 'visuals.toml'), '--visuals-host', 'start', '--visuals-retarget', '1',
       '--visuals-vegetation', 'none', '--visuals-canopies', 'apex')               # build.ps1 l.173-181
if (-not $Longueur) { $a += @('--keep-variants', '1') }
if ($obstacles) { $a += @('--objects', (Join-Path $cfg 'object-collision.toml')) }
if (-not $GarderDecor) {
    $scenery = Join-Path $cfg 'scenery.toml'
    if ($CellulesDecor) {
        # Voie hybride (pc\etape2_unreal\PROTOCOLE.md § 0 quater) : ces cellules de Hafren restent chargées dans la
        # variante aller. Leur contenu gallois est remplacé par notre décor, cuit par Unreal au même chemin et livré
        # dans un conteneur à part (zz_gc_*_P). Sans ce conteneur, elles montreraient le terrain et les arbres gallois.
        $garder = @('22VG0QIP9ATUQI633K86KWPFP') + $CellulesDecor | ForEach-Object { "`"$_`"" }
        $texte = (Get-Content $scenery -Raw) -replace '(?m)^keep = \[[^\]]*\]', "keep = [$($garder -join ', ')]"
        if ($texte -notmatch [regex]::Escape($CellulesDecor[0])) { Echec "ligne « keep » introuvable dans $scenery" }
        $scenery = Join-Path $work 'scenery-hybride.toml'
        New-Item -ItemType Directory -Force $work | Out-Null
        Set-Content $scenery $texte -Encoding utf8
        Ok "cellules gardées pour notre décor : $($CellulesDecor -join ', ')"
    }
    $a += @('--scenery', $scenery, '--scenery-actor-hidden', '1')                                                   # build.ps1 l.168-171
}
if ($Textures) { $a += @('--visuals-textured', '1') }
if ($Noms) { $a += @('--names', (Join-Path $script:Projet 'pc\config\noms-grand-caunet.toml')) }
if ($Ciel) { $a += @('--sky', (Join-Path $cfg 'sky.toml'), '--sky-section', 'france') }
Push-Location $src
try { Lancer $acrRef $a "construction (stage-build) ; ses contrôles hors jeu sont dans le journal" } finally { Pop-Location }
Ok "construction terminée : rapport $rapport"

Etape "Empaquetage (retoc to-zen)"
# build.ps1 l.197-199
$dist = Join-Path $work 'dist'
New-Item -ItemType Directory -Force $dist | Out-Null
Remove-Item (Join-Path $dist "$($script:NomConteneur).*") -ErrorAction SilentlyContinue
Lancer $retoc @('to-zen', '--version', 'UE5_6', $mod, (Join-Path $dist "$($script:NomConteneur).utoc")) "empaquetage"
Get-ChildItem $dist "$($script:NomConteneur).*" | ForEach-Object { Ok ("{0} ({1:N1} Mo)" -f $_.Name, ($_.Length / 1MB)) }

Etape "Contrôle hors jeu du mod empaqueté"
# build.ps1 l.201-227 : relecture par CUE4Parse avec le jeu d'origine + notre mod, puis contrôles sur un aller-retour retoc
$check = Join-Path $work 'controle'
$checkPaks = Join-Path $check 'acr\Content\Paks'
Remove-Item -Recurse -Force $check -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force $checkPaks | Out-Null
Copy-Item (Join-Path $paks 'global.*') $checkPaks
Copy-Item (Join-Path $dist "$($script:NomConteneur).*") $checkPaks
$full = Join-Path $check 'full\acr\Content\Paks'
New-Item -ItemType Directory -Force $full | Out-Null
Get-ChildItem $paks -File | ForEach-Object { New-Item -ItemType HardLink -Path (Join-Path $full $_.Name) -Target $_.FullName | Out-Null }
Copy-Item (Join-Path $dist "$($script:NomConteneur).*") $full
$v = @('stage-verify', '--game', (Join-Path $check 'full'), '--ir', $irTravail, '--usmap', $usmap, '--out', (Join-Path $check 'verify-cue4parse.txt'))
if (-not $GarderDecor) { $v += @('--hidden-actors', '1') }
if (-not $Longueur) { $v += @('--keep-variants', '1') }
# pas de --sky ici : leur stage-verify compare le ciel à la section [nz] de sky.toml (StageVerify.cs, cfg.Num("nz", ...)),
# il signalerait FAIL pour notre section [france] ; le ciel n'est donc contrôlé que par le rapport de stage-build.
& $acrRef @v 2>&1 | Out-Host
$codeVerif = $LASTEXITCODE
if (Test-Path (Join-Path $check 'verify-cue4parse.txt')) { Get-Content (Join-Path $check 'verify-cue4parse.txt') | Out-Host }
$rt = Join-Path $check 'roundtrip'
Lancer $retoc @('to-legacy', '--version', 'UE5_6', '--no-shaders', $checkPaks, $rt) "aller-retour retoc"
& $acrRef stage-check --legacy $rt --ir $irTravail --report $rapport --out (Join-Path $check 'verify-roundtrip.txt') 2>&1 | Out-Host
$codeCheck = $LASTEXITCODE
if (Test-Path (Join-Path $check 'verify-roundtrip.txt')) { Get-Content (Join-Path $check 'verify-roundtrip.txt') | Out-Host }
$fails = @(Select-String -Path (Join-Path $check 'verify-*.txt') -Pattern '^FAIL').Count
if ($codeVerif -ne 0 -or $codeCheck -ne 0 -or $fails -gt 0) {
    Attention "contrôles : $fails ligne(s) FAIL (codes $codeVerif / $codeCheck). Ne pas installer avant d'avoir lu ces lignes ; les transmettre."
} else { Ok "contrôles hors jeu : aucune ligne FAIL. Étape suivante : 5_installer.ps1" }
Stop-Journal
