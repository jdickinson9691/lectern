# Windows Build Guide

1. Extract the ZIP into a normal folder, not inside the compressed ZIP preview.
2. Open PowerShell in the extracted project root.
3. Confirm the build folder exists:

```powershell
dir .\build
```

4. Run:

```powershell
.\build\Build.bat
```

5. Launch:

```powershell
.\dist\Lectern\Lectern.exe
```

If Python is missing, install Python 3.11+ and select **Add Python to PATH**.
