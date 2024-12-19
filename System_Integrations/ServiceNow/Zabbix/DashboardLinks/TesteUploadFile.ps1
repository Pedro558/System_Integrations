$headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
$headers.Add("Content-Type", "multipart/form-data")
$headers.Add("Authorization", "Bearer <TOKEN>")
# $headers.Add("Cookie", "BIGipServerpool_eleadev=38050c29f5980322f71ae59cf95e8bc1; JSESSIONID=D59B6DF5284F65393CD2F2A61D9B6F80; glide_node_id_for_js=d37dac2be5fbdeef361ac819ffd75649ca5dbcc31367a03c8d87e14c93ee58a0; glide_session_store=C63B49003B229210B3CFC447F4E45A3C; glide_user_activity=U0N2M18xOmF4M290KzkzZFVFb2IrYlo4Z2FNMzIzbHVDTEYvQWFvcDE1OXVTU0J5TTQ9OjFJSEc1RXc4aU1Lb0RHeUp3R3M1MjZjUWlmQkc0eENsdVJmdHVqNlhpSDQ9; glide_user_route=glide.0169089b228a11a249ccb95fcfc00049")

# $filePath = 'C:/Temp/ZabbixSnowSyncImg/TotalTraffic/total_traffic_2.png'
# $uri = 'https://eleadev.service-now.com/api/now/attachment/upload'

$multipartContent = [System.Net.Http.MultipartFormDataContent]::new()
$multipartFile = 'C:/Temp/ZabbixSnowSyncImg/TotalTraffic/total_traffic_2.png'
$FileStream = [System.IO.FileStream]::new($multipartFile, [System.IO.FileMode]::Open)
$fileHeader = [System.Net.Http.Headers.ContentDispositionHeaderValue]::new("form-data")
$fileHeader.Name = "uploadFile"
$fileHeader.FileName = "C:/Temp/ZabbixSnowSyncImg/TotalTraffic/total_traffic_2.png"
$fileContent = [System.Net.Http.StreamContent]::new($FileStream)
$fileContent.Headers.ContentDisposition = $fileHeader
$multipartContent.Add($fileContent)

$body = $multipartContent


try {
    $response = Invoke-RestMethod 'https://eleadev.service-now.com/api/now/attachment/upload' `
        -Method 'POST' `
        -Headers $headers `
        -Body $body

} catch {
   Write-Host "An error occurred: $_"
    
    # Check if the exception contains a response
    if ($_.Exception.Response) {
        # Read the response stream
        $responseStream = $_.Exception.Response.GetResponseStream()
        $reader = [System.IO.StreamReader]::new($responseStream)
        $errorBody = $reader.ReadToEnd()
        
        Write-Host "Server Response: $errorBody" 
    }
}



# try {
#     $wc = New-Object System.Net.WebClient
#     $response = $wc.UploadFile($uri,$filePath)

# } catch {
#    Write-Host "An error occurred: $_"
    
#     # Check if the exception contains a response
#     if ($_.Exception.Response) {
#         # Read the response stream
#         $responseStream = $_.Exception.Response.GetResponseStream()
#         $reader = [System.IO.StreamReader]::new($responseStream)
#         $errorBody = $reader.ReadToEnd()
        
#         Write-Host "Server Response: $errorBody" 
#     }
# }





$headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
$headers.Add("Content-Type", "multipart/form-data")
$headers.Add("Authorization", "Bearer <TOKEN>")
$headers.Add("Cookie", "BIGipServerpool_eleadev=38050c29f5980322f71ae59cf95e8bc1; JSESSIONID=D59B6DF5284F65393CD2F2A61D9B6F80; glide_node_id_for_js=d37dac2be5fbdeef361ac819ffd75649ca5dbcc31367a03c8d87e14c93ee58a0; glide_user_activity=U0N2M18xOmF4M290KzkzZFVFb2IrYlo4Z2FNMzIzbHVDTEYvQWFvcDE1OXVTU0J5TTQ9OjFJSEc1RXc4aU1Lb0RHeUp3R3M1MjZjUWlmQkc0eENsdVJmdHVqNlhpSDQ9; glide_user_route=glide.0169089b228a11a249ccb95fcfc00049")

$multipartContent = [System.Net.Http.MultipartFormDataContent]::new()
$body = $multipartContent

$response = Invoke-RestMethod 'https://eleadev.service-now.com/api/now/attachment/upload' -Method 'POST' -Headers $headers -Body $body
$response | ConvertTo-Json