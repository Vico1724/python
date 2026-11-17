<#
.SYNOPSIS
  Contrôle avant départ : vérifie, sans rien modifier, que le PC est prêt (voir pc/controle_avant_depart.md).
  NON TESTÉ (écrit sans Windows). Fonctionne sous Windows PowerShell 5.1 comme sous PowerShell 7.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File pc\scripts\0_controle.ps1
#>
param(
    [string]$Jeu,
    [string]$Travail
)
. "$PSScriptRoot\commun.ps1"
if (-not $Jeu) { $Jeu = $script:JeuParDefaut }
if (-not $Travail) { $Travail = $script:TravailParDefaut }
New-Item -ItemType Directory -Force $Travail | Out-Null
Start-Journal $Travail '0_controle'
$problemes = 0
function Pb([string]$t) { Attention $t; $script:problemes++ }

Etape "Jeu"
$paks = Get-Paks $Jeu
if (Test-Path (Join-Path $paks 'global.utoc')) { Ok "jeu trouvé : $Jeu" } else { Pb "pas de jeu à $Jeu (paramètre -Jeu)" }
$b = Get-BuildJeu $Jeu
if ($b -eq $script:BuildJeu) { Ok "version de construction $b" }
elseif ($b) { Pb "version de construction $b, différente de $($script:BuildJeu) : la mise à jour du jeu peut tout casser (fichier .usmap à refaire, essai non garanti)" }
else { Pb "version de construction inconnue (steamapps\appmanifest_3917090.acf introuvable)" }
if (Test-JeuLance) { Pb "le jeu est lancé : le fermer avant de construire ou d'installer" } else { Ok "le jeu n'est pas lancé" }

Etape "Archives du jeu (comparées à la liste relevée pour la version 25170642)"
$ref = Import-Csv (Join-Path $script:Projet 'data\reference\acr_paks_build_25170642.csv')
$diff = 0
foreach ($r in $ref) {
    $f = Join-Path $paks $r.fichier
    if ($r.fichier -like 'pakchunk99-*') { continue }               # BioBio, traité plus bas
    if (-not (Test-Path $f)) { $diff++; Attention "absent : $($r.fichier)"; continue }
    if ((Get-Item $f).Length -ne [long]$r.taille_octets) { $diff++; Attention "taille différente : $($r.fichier)" }
}
if ($diff -eq 0) { Ok "les archives d'origine ont les tailles attendues" } else { Pb "$diff archives d'origine diffèrent de la liste de référence" }
$autres = Get-ChildItem $paks -File | Where-Object { $_.BaseName -notmatch '^(global|pakchunk\d+(optional)?-Windows)$' }
foreach ($a in $autres) { Write-Host "  archive non d'origine (mod) : $($a.Name)" }
if ($autres | Where-Object Name -like 'pakchunk99-ChileBioBio_P*') { Ok "BioBio présent (il peut rester installé avec les options par défaut, voir LISEZMOI)" }
$mods = Join-Path $paks '~mods'
if (Test-Path $mods) { Get-ChildItem $mods -File | ForEach-Object { Write-Host "  dans ~mods : $($_.Name)" } } else { Ok "pas de dossier ~mods (il sera créé à l'installation)" }

Etape "Disque"
$q = Split-Path -Qualifier $Jeu
$qt = Split-Path -Qualifier (Resolve-Path $Travail).Path
if ($q -ne $qt) { Pb "le dossier de travail ($Travail) n'est pas sur le disque du jeu ($q) : les liens physiques échoueront" } else { Ok "dossier de travail sur le disque du jeu ($q)" }
$libre = [math]::Round((Get-PSDrive ($q.TrimEnd(':'))).Free / 1GB, 1)
if ($libre -ge 10) { Ok "$libre Go libres sur $q" } else { Pb "$libre Go libres sur $q (10 Go conseillés)" }
try { $vol = Get-Volume -DriveLetter ($q.TrimEnd(':')) -ErrorAction Stop; if ($vol.FileSystem -ne 'NTFS') { Pb "$q est en $($vol.FileSystem), pas en NTFS" } else { Ok "$q est en NTFS" } } catch { Attention "type de disque non vérifié" }

Etape "Outils"
foreach ($t in @(@('pwsh', 'PowerShell 7'), @('git', 'Git'), @('dotnet', 'kit .NET'), @('cargo', 'Rust (cargo)'), @('winget', 'winget'))) {
    if (Test-Commande $t[0]) { Ok "$($t[1]) présent" } else { Pb "$($t[1]) absent (1_prerequis.ps1)" }
}
if (Test-Commande 'dotnet') {
    $sdk = (& dotnet --list-sdks 2>$null) -join ' '
    if ($sdk -match '(^|\s)10\.') { Ok "kit .NET 10 présent" } else { Pb "kit .NET 10 absent (trouvé : $sdk)" }
}
if (Test-Commande 'pwsh') { Ok ("PowerShell " + (& pwsh -NoProfile -Command '$PSVersionTable.PSVersion.ToString()')) }

Etape "Kit"
$src = Get-Source $Travail
if (Test-Path (Join-Path $src '.git')) {
    $h = (& git -C $src rev-parse HEAD)
    if ($h -eq $script:CommitAcrXs) { Ok "ACR Extra Stages à la version étudiée ($h)" } else { Pb "ACR Extra Stages à la version $h, pas $($script:CommitAcrXs)" }
} else { Write-Host "  ACR Extra Stages pas encore récupéré (2_recuperer_acrxs.ps1)" }
foreach ($e in @("bin\retoc\bin\retoc.exe", "bin\acr-ref\acr-ref.exe")) {
    if (Test-Path (Join-Path $Travail $e)) { Ok "$e présent" } else { Write-Host "  $e pas encore construit (2_recuperer_acrxs.ps1)" }
}
$u = Get-Usmap $Travail
if (Test-Path $u) { Ok "fichier de correspondance présent : $u ($([math]::Round((Get-Item $u).Length / 1KB)) Ko)" } else { Write-Host "  fichier de correspondance (.usmap) pas encore produit (3_usmap.ps1)" }
$ir = Join-Path $script:Projet 'export\stage_ir\grand_caunet'
foreach ($f in 'stage.json', 'collision.glb') {
    if (Test-Path (Join-Path $ir $f)) { Ok "export : $f" } else { Pb "export : $f absent de $ir (voir LISEZMOI, « si l'export manque »)" }
}

Etape "Bilan"
if ($problemes -eq 0) { Ok "rien à signaler" } else { Attention "$problemes point(s) à régler avant de continuer" }
Stop-Journal
