Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectPath = "C:\Users\Admin\Documents\Codex\Демо"
pythonPath = "C:\Users\Admin\AppData\Local\Programs\Python\Python311\python.exe"
demoUrl = "http://127.0.0.1:8000/demo/open/"
powershellPath = "C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"

If Not fso.FileExists(pythonPath) Then
    MsgBox "Python табылмады: " & pythonPath, 48, "Demo launcher"
    WScript.Quit 1
End If

serverCommand = "& { " & _
    "$server = Get-NetTCPConnection -LocalPort 8000 -ErrorAction SilentlyContinue | " & _
    "Where-Object { $_.State -eq 'Listen' }; " & _
    "if (-not $server) { " & _
    "Start-Process -FilePath '" & Replace(pythonPath, "'", "''") & "' " & _
    "-ArgumentList 'manage.py','runserver','127.0.0.1:8000' " & _
    "-WorkingDirectory '" & Replace(projectPath, "'", "''") & "' " & _
    "-WindowStyle Hidden } ; " & _
    "Start-Sleep -Seconds 4; " & _
    "Start-Process '" & demoUrl & "' }"

shell.Run """" & powershellPath & """ -NoProfile -ExecutionPolicy Bypass -Command """ & serverCommand & """", 0, False
