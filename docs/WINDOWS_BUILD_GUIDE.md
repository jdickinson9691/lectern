# Windows Build Guide

1. Extract the ZIP into a normal folder, not inside the compressed ZIP preview.
2. Open PowerShell in the extracted project root.
3. Confirm the build folder exists:

```powershell
dir .\build
```

4. Run:

```powershell
.\build\Build.ps1
```

5. Launch:

```powershell
.\dist\Lectern\Lectern.exe
```

If Python is missing, install Python 3.13 and enable the Python launcher during installation.
