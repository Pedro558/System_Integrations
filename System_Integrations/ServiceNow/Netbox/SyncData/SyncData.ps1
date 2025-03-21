# Activate the virtual environment
$scriptPath = "C:\rundeck\projects\System_Integrations\ScmImport"
$activateScript = Join-Path -Path $scriptPath -ChildPath "venv\Scripts\Activate.ps1"
. $activateScript

# Run your Python script
$scriptModule = "System_Integrations.ServiceNow.Netbox.SyncData.SyncData"
Set-Location -Path $scriptPath
python -m $scriptModule
