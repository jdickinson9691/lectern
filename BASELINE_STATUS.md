# Lectern Baseline Status

## Current baseline

- Version: 2.9.3
- Release: Fresh Baseline and Watermark Verification
- Database schema: v4
- Code model: one continuously evolving Git repository

## Stabilization status

The source package has been reset into a clean project root. Every page registered in the left navigation is wrapped by the watermark container. Python 3.12 or 3.13 is required for the validated Windows development environment.

## Next required workstation checks

1. Run `scripts/Setup-Development.ps1`.
2. Launch with `scripts/Start-Lectern.ps1`.
3. Visually inspect all 16 navigation screens.
4. Complete Player, Monster, and Encounter CRUD checks.
5. Build `dist/Lectern/Lectern.exe`.
6. Compile and test the Inno Setup installer.

Do not begin v3.0 feature development until these Windows checks pass.
