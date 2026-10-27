from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtWidgets import QApplication

from app.database.repositories import Repository
from app.database.schema import initialize_database
from app.ui.main_window import CampaignDashboardPage


def test_regular_dashboard_opens_separate_ashen_workspace(tmp_path: Path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.delenv('LECTERN_ASHEN_COMPANY', raising=False)
    monkeypatch.setenv('LOCALAPPDATA', str(tmp_path))
    db = tmp_path / 'regular.db'
    initialize_database(db)
    page = CampaignDashboardPage(Repository(db), lambda: None)
    assert not page.open_ashen_button.isHidden()
    with patch('app.ui.main_window.subprocess.Popen') as launch:
        page.open_ashen_company()
    args, kwargs = launch.call_args
    assert args[0][-1].endswith('run.py')
    assert kwargs['env']['LECTERN_ASHEN_COMPANY'] == '1'
    assert kwargs['env']['LECTERN_DATA_DIR'] == str(tmp_path / 'DND5ECampaignManager-AshenCompany')
    page.close()


def test_ashen_dashboard_has_campaign_and_hides_workspace_launcher(tmp_path: Path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv('LECTERN_ASHEN_COMPANY', '1')
    db = tmp_path / 'ashen.db'
    initialize_database(db)
    page = CampaignDashboardPage(Repository(db), lambda: None)
    assert page.open_ashen_button.isHidden()
    assert page.campaigns.count() == 1
    assert page.campaigns.itemText(0) == 'Ashen Company [Local]'
    page.close()
