Set shell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")

projectPath = "C:\Users\Admin\Documents\Codex\Демо"
pycharmPath = "C:\Program Files\JetBrains\PyCharm Community Edition 2023.1.2\bin\pycharm64.exe"
starterPath = projectPath & "\start-demo.bat"

If fso.FileExists(pycharmPath) Then
    shell.Run """" & pycharmPath & """ """ & projectPath & """", 1, False
End If

If fso.FileExists(starterPath) Then
    shell.Run """" & starterPath & """", 1, False
End If
