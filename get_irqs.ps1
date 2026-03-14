$output = @()

# IRQs
$resources = Get-WmiObject Win32_AllocatedResource | Where-Object { $_.Antecedent -match "Win32_IRQResource" }
foreach ($res in $resources) {
    $irqMatch = [regex]::Match($res.Antecedent, 'IRQNumber=(\d+)')
    $irq = if ($irqMatch.Success) { $irqMatch.Groups[1].Value } else { "Unknown" }

    $devMatch = [regex]::Match($res.Dependent, 'DeviceID="([^"]+)"')
    if ($devMatch.Success) {
        $devId = $devMatch.Groups[1].Value
        $escapedDevId = $devId -replace '\\', '\\'
        try {
            $device = Get-WmiObject Win32_PnPEntity -Filter "DeviceID='$escapedDevId'" -ErrorAction Stop
            if ($device) {
                $output += [PSCustomObject]@{
                    Type = "IRQ"
                    Resource = $irq
                    DeviceName = $device.Name
                    DeviceClass = $device.PNPClass
                }
            }
        } catch {}
    }
}

# DMA
$dmas = Get-WmiObject Win32_AllocatedResource | Where-Object { $_.Antecedent -match "Win32_DMAChannel" }
foreach ($dma in $dmas) {
    $dmaMatch = [regex]::Match($dma.Antecedent, 'DMAChannel=(\d+)')
    $channel = if ($dmaMatch.Success) { $dmaMatch.Groups[1].Value } else { "Unknown" }

    $devMatch = [regex]::Match($dma.Dependent, 'DeviceID="([^"]+)"')
    if ($devMatch.Success) {
        $devId = $devMatch.Groups[1].Value
        $escapedDevId = $devId -replace '\\', '\\'
        try {
            $device = Get-WmiObject Win32_PnPEntity -Filter "DeviceID='$escapedDevId'" -ErrorAction Stop
            if ($device) {
                $output += [PSCustomObject]@{
                    Type = "DMA"
                    Resource = $channel
                    DeviceName = $device.Name
                    DeviceClass = $device.PNPClass
                }
            }
        } catch {}
    }
}

$output | ConvertTo-Json
