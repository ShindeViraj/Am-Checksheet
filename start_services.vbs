Set WshShell = CreateObject("WScript.Shell")

' Set the working directory to the folder where this script is located
WshShell.CurrentDirectory = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Run the Python Flask application invisibly (0 = hidden window, False = don't wait for it to finish)
WshShell.Run "cmd /c python app.py", 0, False

' Run Node-RED invisibly
WshShell.Run "cmd /c node-red", 0, False
