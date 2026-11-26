param(
  [string]$BuildTools="$env:LOCALAPPDATA/Android/Sdk/build-tools/34.0.0",
  [string]$Platform="$env:TEMP/android-35-ext15/android.jar",
  [string]$WearableJar="$env:TEMP/artist-wear-lib/classes.jar"
)
$ErrorActionPreference='Stop'
function Run($command,[string[]]$arguments) {
  & $command @arguments
  if($LASTEXITCODE -ne 0){throw "$command failed ($LASTEXITCODE)"}
}
$dir=Join-Path $env:TEMP ("artist-v2-"+[guid]::NewGuid())
$null=New-Item -Type Directory "$dir/java","$dir/lib","$dir/dex"
$key="$env:USERPROFILE/.android/artist-local.p12"
if(!(Test-Path $key)){throw "Missing signing key used by Artist 1.0"}
$src=Get-ChildItem "$PSScriptRoot/engine/src/*.java" | ForEach-Object FullName
Run javac (@('-encoding','UTF-8','--release','8','-cp',"$Platform;$WearableJar;$env:TEMP/artist-push/wear-sdk.jar",'-d',"$dir/java")+$src)
Run jar @('cf',"$dir/engine.jar",'-C',"$dir/java",'.')
Push-Location "$dir/lib"
try {
  Run jar @('xf',$WearableJar,'android/support/wearable/complications','android/support/wearable/internal/aidl')
  $deps=Get-ChildItem 'android/support/wearable/complications/*.class','android/support/wearable/internal/aidl/*.class' | ForEach-Object {Resolve-Path -Relative $_.FullName}
  Run jar (@('cf',"$dir/protocol.jar")+$deps)
} finally {Pop-Location}
Run "$BuildTools/d8.bat" @('--min-api','33','--lib',$Platform,'--output',"$dir/dex","$dir/engine.jar","$dir/protocol.jar")
foreach($target in @('face','engine')) {
  $project=Join-Path $PSScriptRoot $target
  $raw="$dir/$target.apk"
  Run "$BuildTools/aapt2.exe" @('compile','--dir',"$project/res",'-o',"$dir/$target.zip")
  $extra=@()
  if($target -eq 'engine'){$extra=@('-A',"$project/assets")}
  Run "$BuildTools/aapt2.exe" (@('link','-I',$Platform,'--manifest',"$project/AndroidManifest.xml",'--min-sdk-version','36','--target-sdk-version','36','-o',$raw,"$dir/$target.zip")+$extra)
  if($target -eq 'engine'){Run jar @('uf',$raw,'-C',"$dir/dex",'classes.dex')}
  Run "$BuildTools/zipalign.exe" @('-f','4',$raw,"$dir/aligned-$target.apk")
  $out=if($target -eq "face"){"$dir/validated-face.apk"}else{"$PSScriptRoot/Artist-4.2.apk"}
  Run "$BuildTools/apksigner.bat" @('sign','--v4-signing-enabled','false','--ks',$key,'--ks-pass','pass:android','--ks-key-alias','artist','--out',$out,"$dir/aligned-$target.apk")
  Run "$BuildTools/apksigner.bat" @('verify','--verbose',$out)
  if($target -eq "face"){
    $msg = (& java -jar "$env:TEMP/artist-push/validator.jar" --apk_path=$out --package_name=local.artist.watchface 2>&1 | Out-String)
    if($LASTEXITCODE -ne 0){throw $msg}
    if($msg -notmatch '(?i)token[\s:=]+([^\s]+)'){throw $msg}
    Copy-Item -LiteralPath $out -Destination "$PSScriptRoot/engine/assets/portrait.wff" -Force
    [IO.File]::WriteAllText("$PSScriptRoot/engine/assets/push-token.txt",$matches[1])
  }
}




