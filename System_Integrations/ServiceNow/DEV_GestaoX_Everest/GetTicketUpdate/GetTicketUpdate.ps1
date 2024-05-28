# Activate the virtual environment
$venvPath = "C:\python\venv\System_Integrations" # TODO create venv to proxmox
$activateScript = Join-Path -Path $venvPath -ChildPath "Scripts\Activate.ps1"
. $activateScript

# Run your Python script
$scriptPath = "C:\rundeck\projects\System_Integrations\ScmImport"
$scriptModule = "System_Integrations.ServiceNow.GetTicketUpdate.GetTicketUpdate"
Set-Location -Path $scriptPath
python -m $scriptModule
