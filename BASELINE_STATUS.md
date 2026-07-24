# Lectern Baseline Status

## Current milestone

- Version: 3.0.0 (in progress)
- Release: Workflow and Import Refinement
- Database schema: v10
- Code model: one continuously evolving Git repository

## Stabilization status

The completed v2.9.5 work is the foundation for v3.0.0. The current 3.0 work
adds refined Fantasy Grounds workflows, local campaign ownership, persistent
parties, guided campaign setup, and the split Combat Dashboard. Python 3.13
remains the validated development and packaging environment. See
`docs/LECTERN_3_1_DEVELOPMENT.md` for active product planning and
`docs/LECTERN_3_0_0_KICKOFF.md` for the original 3.0 baseline.

## Next required workstation checks

1. Run `scripts/Setup-Development.ps1`.
2. Launch with `scripts/Start-Lectern.ps1`.
3. Visually inspect all navigation screens.
4. Complete Player, Monster, and Encounter CRUD checks.
5. Verify the Lectern Sync extension in a Fantasy Grounds Unity 5E test campaign.
6. Build `dist/Lectern/Lectern.exe` and `dist/Lectern/FantasyGrounds/LecternSync.ext`.
7. Compile and test the Inno Setup installer.

Record new v3.0.0 behavior and verification evidence as development proceeds.
