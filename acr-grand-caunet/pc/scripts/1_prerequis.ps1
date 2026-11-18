<#
.SYNOPSIS
  Vérifie et, après confirmation, installe les logiciels nécessaires avec winget (le gestionnaire de logiciels de
  Windows) : PowerShell 7, Git, kit .NET 10, outils de compilation C++ de Microsoft (exigés par Rust sous Windows),
  Rust. NON TESTÉ (écrit sans Windows). Doit tourner sous Windows PowerShell 5.1 (PowerShell 7 n'est peut-être pas
  encore là).

  Documenté par ACR Extra Stages (CONTRIBUTING.md) : .NET 10 SDK, Git, Rust via rustup, PowerShell 7.
  Supposé : les identifiants winget ci-dessous, et le besoin des outils C++ (Rust « msvc » ne peut pas lier sans eux).

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File pc\scripts\1_prerequis.ps1
#>
param([string]$Travail, [switch]$Oui)
. "$PSScriptRoot\commun.ps1"
if (-not $Travail) { $Travail = $script:TravailParDefaut }
New-Item -ItemType Directory -Force $Travail | Out-Null
Start-Journal $Travail '1_prerequis'

if (-not (Test-Commande 'winget')) {
    Echec "winget est absent. Installer « App Installer » depuis le Microsoft Store (https://apps.microsoft.com/detail/9nblggh4nns1), puis relancer."
}

# nom affiché, identifiant winget, commande qui prouve la présence, options d'installation
$logiciels = @(
    @{ Nom = 'PowerShell 7'; Id = 'Microsoft.PowerShell'; Test = { Test-Commande 'pwsh' }; Opt = @() },
    @{ Nom = 'Git'; Id = 'Git.Git'; Test = { Test-Commande 'git' }; Opt = @() },
    @{ Nom = 'kit .NET 10'; Id = 'Microsoft.DotNet.SDK.10'; Test = { (Test-Commande 'dotnet') -and ((& dotnet --list-sdks 2>$null) -join ' ') -match '(^|\s)10\.' }; Opt = @() },
    @{ Nom = 'outils de compilation C++ (Visual Studio Build Tools 2022, ~5 Go)'; Id = 'Microsoft.VisualStudio.2022.BuildTools';
       Test = { $vw = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
                (Test-Path $vw) -and ($null -ne (& $vw -products * -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath)) };
       Opt = @('--override', '--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended') },
    @{ Nom = 'Rust (rustup)'; Id = 'Rustlang.Rustup'; Test = { (Test-Commande 'cargo') -or (Test-Path "$HOME\.cargo\bin\cargo.exe") }; Opt = @() }
)

foreach ($l in $logiciels) {
    Etape $l.Nom
    if (& $l.Test) { Ok "déjà installé"; continue }
    if (-not (Confirmer "Installer $($l.Nom) avec winget (identifiant $($l.Id)) ?" -Oui:$Oui)) { Attention "non installé (refusé)"; continue }
    $a = @('install', '--id', $l.Id, '-e', '--source', 'winget', '--accept-package-agreements', '--accept-source-agreements') + $l.Opt
    Lancer 'winget' $a "installation de $($l.Nom)"
    Ok "installé (fermer puis rouvrir la fenêtre pour qu'il soit trouvé)"
}

Etape "Chaîne Rust"
$cargoBin = "$HOME\.cargo\bin"
if (Test-Path "$cargoBin\rustup.exe") {
    $env:Path = "$cargoBin;$env:Path"
    Lancer 'rustup' @('default', 'stable') "choix de la chaîne Rust stable"
} else { Attention "rustup introuvable dans $cargoBin : rouvrir la fenêtre après l'installation, puis relancer ce script" }

Etape "Fin"
Write-Host "Fermer cette fenêtre, en ouvrir une nouvelle (PowerShell 7 : « pwsh »), puis lancer 2_recuperer_acrxs.ps1."
Stop-Journal
