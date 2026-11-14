# Enrollment and Windows verification

## Four states to record separately

1. Factory default certificates embedded in the SPI image.
2. Certificates currently enrolled as PK, KEK, db and dbx in firmware variables.
3. The signer of the Windows Boot Manager actually selected for boot.
4. Windows Secure Boot servicing status and its latest task/event results.

A success in one state leaves the others to be checked. The motherboard's certificate store and Windows' ordinary certificate stores serve different purposes. Windows boot with Secure Boot enabled proves enforcement accepted that boot path, while a particular CA claim needs certificate or measured-boot evidence for that path.

## After a matching-board firmware flash

Use the exact board's AMI key-management procedure. The tested workflow pattern enters Setup Mode and enrolls the updated factory defaults. The supplied image carries saved NVRAM, so flashing its factory files alone can leave previously enrolled keys active. Firmware menu names include Restore Factory Keys and Enroll All Factory Default Keys.

Record PK/KEK/db/dbx before and after the explicitly authorized enrollment. Enabling Secure Boot with a changed trust policy can make an incompatible boot medium fail validation. Retain a recovery path appropriate to the hardware and OS configuration. Confirm UEFI boot mode and observe the actual Windows boot result.

## Read-only Windows collection

Run elevated Windows PowerShell. Collect the enabled state and raw variables through the SecureBoot module.

```powershell
Confirm-SecureBootUEFI
Get-SecureBootUEFI -Name PK
Get-SecureBootUEFI -Name KEK
Get-SecureBootUEFI -Name db
Get-SecureBootUEFI -Name dbx
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot'
Get-ItemProperty 'HKLM:\SYSTEM\CurrentControlSet\Control\SecureBoot\Servicing' -ErrorAction SilentlyContinue
Get-ScheduledTask -TaskPath '\Microsoft\Windows\PI\' -TaskName 'Secure-Boot-Update' -ErrorAction SilentlyContinue
Get-WinEvent -FilterHashtable @{LogName='System'; ProviderName='Microsoft-Windows-TPM-WMI'} -MaxEvents 40
```

Parse `.Bytes` from each variable as complete EFI signature lists and match certificate DER fingerprints. Record collection errors, privileges and firmware support failures. Registry names and task availability depend on Windows release and servicing state. Read the current Microsoft guidance before interpreting undocumented or changed status fields. [SecureBoot PowerShell](https://learn.microsoft.com/en-us/powershell/module/secureboot/) · [Microsoft certificate update guidance](https://learn.microsoft.com/en-us/troubleshoot/windows-client/windows-security/update-secure-boot-certificates)

## Boot Manager and servicing

Identify the active boot entry and its EFI system partition. Inspect its Boot Manager file, signature and chain, then use suitable measured-boot or active-boot evidence to support the claim that this copy was executed. A 2023-signed file found elsewhere in Windows can be a staged replacement or recovery copy.

Windows update status such as `InProgress`, capability indicators or a yellow warning needs its own event and task analysis. Check cumulative update state, pending restart, servicing task result and firmware write failures. An authorized rerun of the Secure-Boot-Update task is an observation step, and can legitimately change enrolled variables. Establish the intended changes before running it when the user requires enrolled keys to remain fixed. Avoid forcing registry values to manufacture a success status.

Capture the same raw variables and hashes after a reboot. A final report should state whether the keys match the expected factory payload, Secure Boot is enabled, the selected Boot Manager has the intended signature, and Windows servicing completed or has a named pending condition. The original project observed different servicing outcomes between two boards, so hardware model and firmware hash alone cannot replace these checks.
