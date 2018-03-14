#!/usr/bin/pwsh

<#
.SYNOPSIS
Play or download random podcast(s)
.DESCRIPTION
Play or download random podcast(s) from 
podcast MP3 URL file podcasts_opml.txt 
or provide alternative filename at runtime.
#>

Param(
    [Alias('count','c','n')]
    # Download multiple MP3s
    [int]
    $mp3FileCount = 1,
    [Alias('path','file','f')]
    # Define alternative URL list file
    [string]
    $pathToMp3File = './podcasts_opml.txt',
    [Alias('d','down')]
    # Download file(s) only
    [switch]
    $downloadOnly,
    [Alias('b')]
    # Define browser
    $browser = 'firefox'
    )

$allMp3Urls = Get-Content $pathToMp3File

for ($i=0; $i -lt $mp3FileCount; $i++){

[Object]$Random = New-Object System.Random
$randomInt = $Random.Next(1, $allMp3Urls.Length)

$mp3Url = $allMp3Urls[$randomInt]

if (-not $downloadOnly){
Write-Output "#$randomInt $mp3Url"
& $browser $mp3Url 2> /dev/null 1> /dev/null
}
else {
    Write-Output "#$randomInt $mp3Url"
    wget -T 10 -t 1 $mp3Url 2> /dev/null 1> /dev/null
}
}

 
