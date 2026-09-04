# 몽글이 버추얼 스트리머 - PowerShell 실행 서버 (Node.js 없는 컴퓨터용)
param([int]$Port = 8977)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$mime = @{
  ".html" = "text/html; charset=utf-8"
  ".js"   = "text/javascript"
  ".css"  = "text/css"
  ".png"  = "image/png"
  ".md"   = "text/plain; charset=utf-8"
}

$listener = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback, $Port)
$listener.Start()
Write-Host ""
Write-Host "  몽글이 실행 중! 브라우저에서 http://localhost:$Port 를 여세요"
Write-Host "  (이 창은 끄지 말고 두세요)"
Write-Host ""

while ($true) {
  $client = $listener.AcceptTcpClient()
  try {
    $stream = $client.GetStream()
    $reader = New-Object System.IO.StreamReader($stream)
    $requestLine = $reader.ReadLine()
    while ($true) { $line = $reader.ReadLine(); if ($null -eq $line -or $line -eq "") { break } }
    if (-not $requestLine) { continue }

    $urlPath = ($requestLine -split " ")[1].Split("?")[0]
    if ($urlPath -eq "/") { $urlPath = "/index.html" }
    $file = Join-Path $root ($urlPath.TrimStart("/") -replace "/", "\")

    if ((Test-Path $file -PathType Leaf) -and ([System.IO.Path]::GetFullPath($file)).StartsWith($root)) {
      $bytes = [System.IO.File]::ReadAllBytes($file)
      $ext = [System.IO.Path]::GetExtension($file).ToLower()
      $ct = $mime[$ext]; if (-not $ct) { $ct = "application/octet-stream" }
      $header = "HTTP/1.1 200 OK`r`nContent-Type: $ct`r`nContent-Length: $($bytes.Length)`r`nConnection: close`r`n`r`n"
    } else {
      $bytes = [System.Text.Encoding]::UTF8.GetBytes("Not found")
      $header = "HTTP/1.1 404 Not Found`r`nContent-Type: text/plain`r`nContent-Length: $($bytes.Length)`r`nConnection: close`r`n`r`n"
    }
    $hb = [System.Text.Encoding]::ASCII.GetBytes($header)
    $stream.Write($hb, 0, $hb.Length)
    $stream.Write($bytes, 0, $bytes.Length)
    $stream.Flush()
  } catch {
  } finally {
    $client.Close()
  }
}
