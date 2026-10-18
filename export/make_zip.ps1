# 회사 이관용 zip을 만든다.
#   powershell -ExecutionPolicy Bypass -File export\make_zip.ps1
# 결과: export\mcp-hub-platform\ (복사본), export\mcp-hub-platform.zip
# 제외: .venv, node_modules, .env, backend 테스트 데이터(data, storage), 빌드 산출물

$ErrorActionPreference = 'Stop'
$root = Split-Path $PSScriptRoot -Parent
$out = Join-Path $PSScriptRoot 'mcp-hub-platform'
$zip = Join-Path $PSScriptRoot 'mcp-hub-platform.zip'

if (Test-Path $out) { Remove-Item $out -Recurse -Force }
if (Test-Path $zip) { Remove-Item $zip -Force }

robocopy $root $out /E /XD .venv node_modules data storage __pycache__ dist $PSScriptRoot /XF .env /NFL /NDL /NJH /NJS | Out-Null
# robocopy는 8 이상이 실패 코드다
if ($LASTEXITCODE -ge 8) { throw "robocopy 실패 (exit $LASTEXITCODE)" }

# Compress-Archive와 .NET ZipFile은 경로를 역슬래시로 저장해서 Linux에서 폴더가 깨진다. tar(bsdtar)는 / 로 저장한다
tar.exe -a -c -f $zip -C $out @(Get-ChildItem $out -Force -Name)
if ($LASTEXITCODE -ne 0) { throw "zip 생성 실패 (exit $LASTEXITCODE)" }
Write-Host "생성 완료: $zip"
