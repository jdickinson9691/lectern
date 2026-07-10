# Lectern Baseline Status

## Current milestone

- Version: 2.9.4 (in progress)
- Release: Verification and Stabilization
- Database schema: v4
- Code model: one continuously evolving Git repository

## Stabilization status

The v2.9.3 source baseline is the foundation for the v2.9.4 verification milestone. Every page registered in the left navigation is wrapped by the watermark container. Python 3.13 is required for the validated Windows environment. Completion requires recorded evidence in `docs/VERIFICATION_REPORT.md`.

## Next required workstation checks

1. Run `scripts/Setup-Development.ps1`.
2. Launch with `scripts/Start-Lectern.ps1`.
3. Visually inspect all 16 navigation screens.
4. Complete Player, Monster, and Encounter CRUD checks.
5. Build `dist/Lectern/Lectern.exe`.
6. Compile and test the Inno Setup installer.

Do not begin v3.0 feature development until these Windows checks pass.
