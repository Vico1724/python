#Requires -Version 7.2
<#
.SYNOPSIS
  Classe la spéciale en asphalte (pneus asphalte, 6,74 km au menu) en livrant la table des variantes du jeu
  (DT_TracksVariants) dans un petit conteneur à part : <dist>\zz_acrxs_grandcaunet_table_9_P.{pak,ucas,utoc}.
  N'écrit RIEN dans le jeu : 5_installer.ps1 ou choisir_decor.ps1 copient ensuite les fichiers dans ~mods.

  Pourquoi un conteneur à part, et ce « _9_ » dans son nom. Une table du jeu est remplacée en entier par le dernier
  mod qui la livre. Sur le PC du directeur, un mod « registre » installé dans le dossier Paks du jeu
  (pakchunk99-SandoRegistry_2_P) la livre déjà, avec les lignes de la spéciale BioBio. Constat du 13/11/2026 : notre
  table, livrée dans zz_acrxs_grandcaunet_P, restait sans effet (spéciale toujours « terre », pneus terre). Le moteur
  classe les conteneurs dont le nom finit par _<nombre>_P d'après ce nombre (FPakPlatformFile : 100 x (nombre + 1)) ;
  sans nombre, le nôtre valait 1, le registre 2. Avec 9, le nôtre passe devant.

  Pour ne pas casser BioBio, notre table PART DE CELLE DU REGISTRE (autorisation du directeur, 13/11/2026, par exception
  à la règle « aucun fichier BioBio réutilisé ») : seule notre ligne (WelesS4HafrenSouthFullForward) y est modifiée,
  par pneus_asphalte.py. Sans registre installé, on part de la table du jeu.
  À REFAIRE si le registre est mis à jour ou retiré : notre copie figerait sinon son ancienne table.

  Rallye propre (demande du directeur, 17/11/2026 ; docs/19_rallye_propre.md) : le même conteneur livre aussi les
  tables des spéciales et des lieux (DT_Tracks, DT_TracksLocations, logos et fonds), où acr-ref rally-tables ajoute le
  lieu « Le Grand Caunet » et sa spéciale, d'après pc\scripts\rallye_grand_caunet.json ; notre variante quitte
  Hafren Sud (pays de Galles). Les lignes modèles sont celles de BioBio : sans le registre, -SansRallye.

.EXAMPLE
  pwsh -ExecutionPolicy Bypass -File pc\scripts\6_table_asphalte.ps1 -LongueurKm 6.738
#>
param([string]$Jeu, [string]$Travail, [double]$LongueurKm = 6.738, [string]$Ligne = 'WelesS4HafrenSouthFullForward',
      [string]$Meteo = 'Alsace', [switch]$SansRallye,   # Alsace depuis le build 23 (météo d'été ; MonteCarlo = hiver : docs/18)
      [string]$Rallye = (Join-Path $PSScriptRoot 'rallye_grand_caunet.json'))   # configuration météo de la ligne (Wales d'origine : 4 °C, essai de la 17) ; '' pour la garder
. "$PSScriptRoot\commun.ps1"
$ErrorActionPreference = 'Stop'
if (-not $Jeu) { $Jeu = $script:JeuParDefaut }
if (-not $Travail) { $Travail = $script:TravailParDefaut }
Assert-Jeu $Jeu
$acrRef = Join-Path $Travail 'bin\acr-ref\acr-ref.exe'
$retoc = Join-Path $Travail 'bin\retoc\bin\retoc.exe'
$usmap = Get-Usmap $Travail
$env:DOTNET_SYSTEM_GLOBALIZATION_INVARIANT = '1'
$work = Join-Path $Travail 'construction'
$paks = Get-Paks $Jeu
$vanilla = Join-Path $work 'vanilla\acr\Content\Paks'
$table = 'acr/Content/Data/Database/Main/TrackSelection/DT_TracksVariants.uasset'
$nom = 'zz_acrxs_grandcaunet_table_9_P'

function New-Vue([string]$racine, [System.IO.FileInfo[]]$fichiers) {
    if (Test-Path $racine) { [IO.Directory]::Delete($racine, $true) }
    $d = Join-Path $racine 'acr\Content\Paks'
    New-Item -ItemType Directory -Force $d | Out-Null
    foreach ($f in $fichiers) { New-Item -ItemType HardLink -Path (Join-Path $d $f.Name) -Target $f.FullName | Out-Null }
    return $d
}
function Read-Ligne([string]$racineJeu, [string]$sortie) {
    & $acrRef export $table --game $racineJeu --usmap $usmap --out $sortie 2>&1 | Out-Null
    if (-not (Test-Path $sortie)) { return $null }
    return (Get-Content $sortie -Raw | ConvertFrom-Json)[0].Rows
}

Etape "Table de départ"
# conteneurs présents dans le dossier Paks du jeu et absents de la vue d'origine : des mods installés hors de ~mods
$origine = @(Get-ChildItem $vanilla -File | ForEach-Object Name)
$autres = @(Get-ChildItem $paks -File -Filter '*.utoc' | Where-Object { $_.Name -notin $origine })
$global = @(Get-ChildItem $vanilla -File -Filter 'global.*')
$source = $null
foreach ($u in $autres) {
    $lot = @(Get-ChildItem $paks -File -Filter "$($u.BaseName).*")
    $vue = New-Vue (Join-Path $work 'vue_registre') ($global + $lot)
    $rows = Read-Ligne (Join-Path $work 'vue_registre') (Join-Path $work 'vue_registre\table.json')
    if ($rows -and $rows.$Ligne) { $source = $u.BaseName; break }
}
if ($source) {
    Ok "table livrée par le mod $source : on part d'elle ($(@($rows.PSObject.Properties).Count) lignes)"
} else {
    $vue = New-Vue (Join-Path $work 'vue_registre') @(Get-ChildItem $vanilla -File)
    $rows = Read-Ligne (Join-Path $work 'vue_registre') (Join-Path $work 'vue_registre\table.json')
    Ok "aucun mod installé ne livre la table : on part de celle du jeu ($(@($rows.PSObject.Properties).Count) lignes)"
}
$noms = @($rows.PSObject.Properties.Name)
$rang = [array]::IndexOf($noms, $Ligne)
if ($rang -lt 0) { Echec "ligne $Ligne absente de la table de départ" }
$suivante = if ($rang + 1 -lt $noms.Count) { $noms[$rang + 1] } else { $null }
$avant = $rows.$Ligne
Ok "notre ligne au départ : pneus $($avant.TireCompounds.Row), longueur $($avant.Length) km ; ligne suivante : $suivante"

Etape "Extraction et correction de la table"
$legacy = Join-Path $work 'table_legacy'
$mod = Join-Path $work 'table_mod'
foreach ($d in $legacy, $mod) { if (Test-Path $d) { [IO.Directory]::Delete($d, $true) } }
$tables = @('DT_TracksVariants')
if (-not $SansRallye) { $tables += @('DT_Tracks', 'DT_TracksLocations', 'DT_TracksLocationsLogos', 'DT_TracksLocationsBackgrounds') }
Lancer $retoc @('to-legacy', '--version', 'UE5_6', '--no-shaders', '--filter', 'TrackSelection/DT_Tracks', $vue, $legacy) "extraction des tables"
$rel = 'acr\Content\Data\Database\Main\TrackSelection'
New-Item -ItemType Directory -Force (Join-Path $mod $rel) | Out-Null
foreach ($t in $tables) {
    foreach ($e in 'uasset', 'uexp') {
        $f = Join-Path $legacy "$rel\$t.$e"
        if (-not (Test-Path $f)) { Echec "$f absent après extraction" }
        Copy-Item $f (Join-Path $mod "$rel\$t.$e")
    }
}
$p = @((Join-Path $PSScriptRoot 'pneus_asphalte.py'), $mod, '--ligne', $Ligne, '--longueur-km', $LongueurKm.ToString([cultureinfo]::InvariantCulture),
       '--longueur-d-origine-km', ([double]$avant.Length).ToString([cultureinfo]::InvariantCulture))
if ($suivante) { $p += @('--suivante', $suivante) }
if ($Meteo) { $p += @('--meteo', $Meteo) }
Lancer 'python' $p "classement de la ligne en asphalte"
if (-not $SansRallye) {
    Lancer $acrRef @('rally-tables', '--game', (Join-Path $work 'vue_registre'), '--usmap', $usmap, '--legacy', $mod, '--config', $Rallye,
                     '--out', (Join-Path $work 'rallye.json')) "rallye propre (lieu, spéciale, logo, fond)"
}

Etape "Empaquetage"
$dist = Join-Path $work 'dist'
New-Item -ItemType Directory -Force $dist | Out-Null
Remove-Item (Join-Path $dist "$nom.*") -ErrorAction SilentlyContinue
Lancer $retoc @('to-zen', '--version', 'UE5_6', $mod, (Join-Path $dist "$nom.utoc")) "empaquetage"

Etape "Relecture : le jeu, ses mods installés hors de ~mods, et notre conteneur"
# référence : la même vue sans notre conteneur (les textes et les renvois d'une table ne se lisent pareil que dans des
# vues complètes ; comparer à la vue réduite de l'étape 1 donnait toutes les lignes pour changées)
New-Vue (Join-Path $work 'vue_table') @(Get-ChildItem $paks -File) | Out-Null
$rows = Read-Ligne (Join-Path $work 'vue_table') (Join-Path $work 'vue_table\table_avant.json')
$noms = @($rows.PSObject.Properties.Name)
$tout = @(Get-ChildItem $paks -File) + @(Get-ChildItem $dist -File -Filter "$nom.*")
New-Vue (Join-Path $work 'vue_table') $tout | Out-Null
$apres = Read-Ligne (Join-Path $work 'vue_table') (Join-Path $work 'vue_table\table.json')
$l = $apres.$Ligne
$surf = @($l.SurfaceTypes | ForEach-Object { $_.Key.Row }) -join ','
$sect = @($l.Sectors | ForEach-Object { $_.SurfaceType.Row }) -join ','
$etat = "surface $surf ; réglages $($l.CarSetupDefaultSurfaceType.Row) ; pneus $($l.TireCompounds.Row) ; secteurs $sect ; météo $($l.WeatherConfig.Row) ; longueur $($l.Length) km"
$meteoOk = (-not $Meteo) -or ($l.WeatherConfig.Row -eq $Meteo)
$n0, $n1 = @($rows.PSObject.Properties).Count, @($apres.PSObject.Properties).Count
# les autres lignes doivent être celles de la table de départ, à l'identique
$autresChangees = @($noms | Where-Object { $_ -ne $Ligne -and (($rows.$_ | ConvertTo-Json -Depth 12 -Compress) -ne ($apres.$_ | ConvertTo-Json -Depth 12 -Compress)) })
if ($surf -eq 'Tarmac' -and $l.CarSetupDefaultSurfaceType.Row -eq 'Tarmac' -and $l.TireCompounds.Row -eq 'TarmacSnow' -and $sect -eq 'Tarmac,Tarmac,Tarmac' -and $meteoOk -and
    $n0 -eq $n1 -and $autresChangees.Count -eq 0) {
    Ok "notre conteneur passe devant : $etat"
    Ok "$n1 lignes, les $($n1 - 1) autres identiques à la table de départ, sauf le renvoi à la spéciale de notre ligne"
    Get-ChildItem $dist "$nom.*" | ForEach-Object { Ok ("{0} ({1:N0} octets)" -f $_.Name, $_.Length) }
} else {
    Echec "relecture non conforme : $etat ; lignes $n0 -> $n1 ; autres lignes changées : $($autresChangees -join ', ')"
}
if (-not $SansRallye) {
    $cfg = Get-Content $Rallye -Raw -Encoding utf8 | ConvertFrom-Json
    $lieu, $spe = $cfg.location.row, $cfg.track.row
    function Read-Table([string]$nomTable, [string]$racine, [string]$sortie) {
        & $acrRef export "acr/Content/Data/Database/Main/TrackSelection/$nomTable.uasset" --game $racine --usmap $usmap --out $sortie 2>&1 | Out-Null
        return (Get-Content $sortie -Raw | ConvertFrom-Json)[0].Rows
    }
    $vt = Join-Path $work 'vue_table'
    $ecarts = @()
    foreach ($t in 'DT_Tracks', 'DT_TracksLocations', 'DT_TracksLocationsLogos', 'DT_TracksLocationsBackgrounds') {
        New-Vue $vt @(Get-ChildItem $paks -File) | Out-Null
        $av = Read-Table $t $vt (Join-Path $vt "$t.avant.json")
        New-Vue $vt $tout | Out-Null
        $ap = Read-Table $t $vt (Join-Path $vt "$t.json")
        $nouv = @($ap.PSObject.Properties.Name | Where-Object { $_ -notin @($av.PSObject.Properties.Name) })
        $chg = @($av.PSObject.Properties.Name | Where-Object { ($av.$_ | ConvertTo-Json -Depth 12 -Compress) -ne ($ap.$_ | ConvertTo-Json -Depth 12 -Compress) })
        $attendu = if ($t -eq 'DT_Tracks') { @($cfg.track.host) } else { @() }
        if (($nouv -join ',') -ne $lieu -or ($chg -join ',') -ne ($attendu -join ',')) { $ecarts += "$t : nouvelles $($nouv -join ',') ; changées $($chg -join ',')" }
        if ($t -eq 'DT_Tracks') { $pisteAp = $ap }
        if ($t -eq 'DT_TracksLocations') { $lieuAp = $ap.$lieu }
    }
    $s = $pisteAp.$spe
    $hote = @($pisteAp.($cfg.track.host).Variants | ForEach-Object Row)
    if ($ecarts.Count -eq 0 -and $l.Track.Row -eq $spe -and $s.Location.Row -eq $lieu -and (@($s.Variants | ForEach-Object Row) -join ',') -eq $Ligne -and
        $Ligne -notin $hote -and (@($lieuAp.Tracks | ForEach-Object Row) -join ',') -eq $spe -and $lieuAp.Country.Row -eq $cfg.location.country) {
        Ok "rallye propre : lieu « $($lieuAp.Name.CultureInvariantString) » ($($lieuAp.Country.Row), $(@($lieuAp.SurfaceTypesData | ForEach-Object { $_.SurfaceType.Row }) -join ',')), spéciale « $($s.Name.CultureInvariantString) » ($Ligne) ; $($cfg.track.host) garde $($hote -join ', ')"
        Ok "logo $($lieuAp.Logo.Row), fond $($lieuAp.BackgroundImage.Row) ; météo tirée comme $($s.WeatherTypesDistribution.Row), $($s.OptimalAirTemperature) °C ; les autres lignes inchangées"
    } else {
        Echec "rallye propre non conforme : $($ecarts -join ' | ') ; variante -> $($l.Track.Row) ; hôte : $($hote -join ',')"
    }
}
