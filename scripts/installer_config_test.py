from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
installer = (ROOT / "installer" / "CampaignManager.iss").read_text(encoding="utf-8")

assert "CreateInputDirPage(" in installer, "Fantasy Grounds folder prompt is missing"
assert "FantasyGroundsExtensionsPage.Values[0]" in installer, "Selected Fantasy Grounds folder is not retained"
assert "{userappdata}\\SmiteWorks\\Fantasy Grounds\\extensions" in installer, "Account-agnostic default folder is missing"
assert 'DestDir: "{code:GetFantasyGroundsExtensionsDir}"' in installer, "Lectern Sync is not installed to the selected folder"
assert "DirExists(SelectedFolder)" in installer, "Fantasy Grounds extension folder is not validated"
assert "c:\\users\\" not in installer.casefold(), "Installer contains a user-specific Windows path"

print("Windows installer configuration test passed.")
