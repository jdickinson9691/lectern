# Lectern Baseline Status

## Current milestone

- Version: 2.9.5 (in progress)
- Release: Workflow and Import Refinement
- Database schema: v5
- Code model: one continuously evolving Git repository

## Stabilization status

The tested v2.9.4 Windows build is the foundation for v2.9.5. It includes campaigns, cumulative encounter reporting, expanded reference data, character PDF import, player portraits, and the reorganized application workflow. Python 3.13 remains the validated development and packaging environment. See `docs/LECTERN_2_9_5_HANDOFF.md` for the complete handoff.

## Next required workstation checks

1. Run `scripts/Setup-Development.ps1`.
2. Launch with `scripts/Start-Lectern.ps1`.
3. Visually inspect all 16 navigation screens.
4. Complete Player, Monster, and Encounter CRUD checks.
5. Build `dist/Lectern/Lectern.exe`.
6. Compile and test the Inno Setup installer.

Record new v2.9.5 behavior and verification evidence as development proceeds.
