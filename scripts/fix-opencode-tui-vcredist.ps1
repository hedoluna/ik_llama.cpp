$ErrorActionPreference = "Stop"

Write-Host "This opens elevated winget installers for the Microsoft Visual C++ 2015-2022 Redistributable."
Write-Host "Approve the UAC prompt when Windows asks for administrator permission."

$packages = @(
  "Microsoft.VCRedist.2015+.x64",
  "Microsoft.VCRedist.2015+.x86"
)

foreach ($package in $packages) {
  Write-Host "Upgrading $package"
  $arguments = @(
    "upgrade",
    $package,
    "--accept-package-agreements",
    "--accept-source-agreements"
  )

  $process = Start-Process -FilePath "winget" -ArgumentList $arguments -Verb RunAs -Wait -PassThru
  if ($process.ExitCode -ne 0) {
    Write-Warning "$package exited with code $($process.ExitCode)"
  }
}

Write-Host "Done. Open a new terminal and run: ocl"
