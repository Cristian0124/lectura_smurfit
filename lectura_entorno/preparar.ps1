$ErrorActionPreference = 'Stop'

$runtime = Join-Path $PSScriptRoot '.runtime'
$pythonDir = Join-Path $runtime 'python'
$sitePackages = Join-Path $runtime 'packages'
$pythonExe = Join-Path $pythonDir 'python.exe'
$pythonZip = Join-Path $runtime 'python-embed.zip'
$getPip = Join-Path $runtime 'get-pip.py'

New-Item -ItemType Directory -Force -Path $runtime | Out-Null

if (-not (Test-Path $pythonExe)) {
    Invoke-WebRequest 'https://www.python.org/ftp/python/3.12.10/python-3.12.10-embed-amd64.zip' -OutFile $pythonZip
    Expand-Archive -LiteralPath $pythonZip -DestinationPath $pythonDir -Force
}

$pth = Join-Path $pythonDir 'python312._pth'
$pthContents = @(Get-Content -LiteralPath $pth | Where-Object { $_ -notin @('Lib', 'packages', '..\packages', '..\..', 'import site') })
$pthContents += @('..\..', '..\packages')
[System.IO.File]::WriteAllLines($pth, $pthContents, [System.Text.Encoding]::ASCII)
New-Item -ItemType Directory -Force -Path $sitePackages | Out-Null

if (-not (Test-Path (Join-Path $sitePackages 'pip'))) {
    Invoke-WebRequest 'https://bootstrap.pypa.io/get-pip.py' -OutFile $getPip
    & $pythonExe $getPip --target $sitePackages
    if ($LASTEXITCODE -ne 0) { throw 'No se pudo instalar pip.' }
}

& $pythonExe -m pip install --target $sitePackages -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'No se pudieron instalar las dependencias.' }

Write-Host 'Preparacion completa. Inicia la app con iniciar.bat.'
