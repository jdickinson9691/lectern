# Install / Run From Source on Windows

1. Extract the ZIP into a fresh folder. Example:

   `C:\Users\jdick\OneDrive\Desktop\CampaignManager_v1_0_verified`

2. Open PowerShell in that extracted folder.

3. Confirm you see the expected folders:

   ```powershell
   dir
   dir .\build
   ```

   You should see `Build.bat` inside `build`.

4. Run from source:

   ```powershell
   py -m pip install -r requirements.txt
   py run.py
   ```

5. Build the desktop executable:

   ```powershell
   .\build\Build.bat
   ```

6. After a successful build, launch:

   ```powershell
   .\dist\Lectern\Lectern.exe
   ```

If `dist` does not exist, the build failed before PyInstaller completed. Read the error above the failure line.
