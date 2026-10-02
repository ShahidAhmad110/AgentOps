Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\my python code\PythonProject\AgentOps"
WshShell.Run "python run_project.py", 0, False
