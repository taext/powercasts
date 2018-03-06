#!/usr/bin/pwsh

<#
.SYNOPSIS
Play or download random podcast(s)
.DESCRIPTION
Play or download random podcast(s) from PocketCasts 
OPML 37.000 podcast file podcasts_opml.txt 
or provide alternative filename at runtime.
#>

Param(
    [Alias('c','n')]
    # Download multiple MP3s
    [int]
    $Count = 1,
    [Alias('file','f')]
    # Define alternative URL list file
    [string]
    $Path = '/home/dd/Documents/newer_opml_parsing/podcasts_opml.txt',
    [Alias('d','down','download')]
    # Download file(s) only
    [switch]
    $DownloadOnly,
    [Alias('b')]
    # Define browser
    $Browser = 'firefox'
    )

$content = Get-Content $Path

for ($i=0; $i -lt $Count; $i++){

[Object]$Random = New-Object System.Random
$randInt = $Random.Next(1, $content.Length)

$mp3Url = $content[$randInt]

if (-not $DownloadOnly){
Write-Output "#$randInt $mp3Url"
& $Browser $mp3Url 2> /dev/null 1> /dev/null
}
else {
    Write-Output "#$randInt $mp3Url"
    wget -T 10 -t 1 $mp3Url 2> /dev/null 1> /dev/null
}
}

