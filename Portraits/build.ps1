param(
    [string]$BuildTools = "$env:LOCALAPPDATA/Android/Sdk/build-tools/34.0.0",
    [string]$AndroidJar = "$env:TEMP/android-35-ext15/android.jar"
)
$ErrorActionPreference = 'Stop'
function Run($command, [string[]]$arguments) {
    & $command @arguments
    if ($LASTEXITCODE -ne 0) { throw "$command failed ($LASTEXITCODE)" }
}
$tempBuild = Join-Path $env:TEMP ("portraits-build-" + [guid]::NewGuid())
New-Item -ItemType Directory $tempBuild | Out-Null
$keyDir = Join-Path $env:USERPROFILE '.android'
New-Item -ItemType Directory -Force $keyDir | Out-Null
$key = Join-Path $keyDir 'artist-local.p12'
if (!(Test-Path $key)) {
    Run keytool @('-genkeypair','-alias','artist','-keyalg','RSA','-keysize','3072','-validity','10000','-keystore',$key,'-storetype','PKCS12','-storepass','android','-keypass','android','-dname','CN=Artist local build')
}
$compiled = Join-Path $tempBuild 'res.zip'
$raw = Join-Path $tempBuild 'raw.apk'
$aligned = Join-Path $tempBuild 'aligned.apk'
$output = Join-Path $PSScriptRoot 'Portraits-1.1.apk'
Run "$BuildTools/aapt2.exe" @('compile','--dir',"$PSScriptRoot/res",'-o',$compiled)
Run "$BuildTools/aapt2.exe" @('link','-I',$AndroidJar,'--manifest',"$PSScriptRoot/AndroidManifest.xml",'--min-sdk-version','36','--target-sdk-version','36','-o',$raw,$compiled)
Run "$BuildTools/zipalign.exe" @('-f','4',$raw,$aligned)
Run "$BuildTools/apksigner.bat" @('sign','--v4-signing-enabled','false','--ks',$key,'--ks-pass','pass:android','--ks-key-alias','artist','--out',$output,$aligned)
Run "$BuildTools/apksigner.bat" @('verify','--verbose',$output)



