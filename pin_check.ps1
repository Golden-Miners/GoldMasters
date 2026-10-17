$PINNED_ROOT = 'C:/XauMaster'
$ACTUAL_ROOT = git rev-parse --show-toplevel
$PINNED_TL = git -C $PINNED_ROOT rev-parse --show-toplevel
if ($ACTUAL_ROOT -eq $PINNED_TL) { 
    Write-Host "PIN OK: ACTUAL_ROOT=$ACTUAL_ROOT PINNED_TL=$PINNED_TL"
    exit 0
} else { 
    Write-Host "MISMATCH: ACTUAL_ROOT=$ACTUAL_ROOT PINNED_TL=$PINNED_TL"
    exit 1 
}