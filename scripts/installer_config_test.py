from pathlib import Path
import zipfile


ROOT = Path(__file__).resolve().parents[1]
installer = (ROOT / "installer" / "CampaignManager.iss").read_text(encoding="utf-8")
spec = (ROOT / "build" / "CampaignManager.spec").read_text(encoding="utf-8")
launcher = (ROOT / "Start Ashen Company.cmd").read_text(encoding="utf-8")
module = ROOT / "docs" / "campaign" / "Ashen_Company_Players.mod"

assert "CreateInputDirPage(" in installer, "Fantasy Grounds folder prompt is missing"
assert "FantasyGroundsExtensionsPage.Values[0]" in installer, "Selected Fantasy Grounds folder is not retained"
assert "{userappdata}\\SmiteWorks\\Fantasy Grounds\\extensions" in installer, "Account-agnostic default folder is missing"
assert 'DestDir: "{code:GetFantasyGroundsExtensionsDir}"' in installer, "Lectern Sync is not installed to the selected folder"
assert 'Start Ashen Company.cmd' in installer, "Ashen Company launcher is not installed"
assert 'Ashen_Company_Players.mod' in installer, "Approved Ashen player module is not installed"
assert 'DestDir: "{code:GetFantasyGroundsModulesDir}"' in installer, "Player module does not target Fantasy Grounds modules"
assert 'Tasks: ashenmodule' in installer, "Player module installation must be selectable"
assert "DirExists(SelectedFolder)" in installer, "Fantasy Grounds extension folder is not validated"
assert "c:\\users\\" not in installer.casefold(), "Installer contains a user-specific Windows path"
assert "'icuuc.dll', 'icudt78.dll'" in spec, "Incompatible third-party ICU binaries must be excluded"
assert 'if exist "Lectern.exe"' in launcher, "Packaged Ashen launcher must use the installed executable"
assert 'LECTERN_ASHEN_COMPANY=1' in launcher, "Ashen launcher must opt into campaign mode"
assert 'LECTERN_DATA_DIR=%LOCALAPPDATA%\\DND5ECampaignManager-AshenCompany' in launcher
with zipfile.ZipFile(module) as archive:
    assert set(archive.namelist()) == {"definition.xml", "client.xml"}
    player_xml = archive.read("client.xml")
    assert player_xml.count(b"<id-") == 7
    for private_marker in (b"GM ONLY", b"GM KNOWLEDGE SECRET", b"SOURCE SECRET"):
        assert private_marker not in player_xml, f"Private content leaked: {private_marker!r}"

print("Windows installer configuration test passed.")
