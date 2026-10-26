"""Keep Ashen campaign tests isolated from generic Lectern databases."""
from pathlib import Path

import pytest


ASHEN_TEST_FILES = {
    'test_ashen_migration.py', 'test_campaign_identity.py',
    'test_player_export.py', 'test_fantasy_grounds_export.py',
    'test_campaign_canon.py', 'test_canon_review.py',
    'test_story_editor.py', 'test_story_mission_agent.py',
    'test_story_ui.py', 'test_world_agents.py',
}


@pytest.fixture(autouse=True)
def ashen_database_for_ashen_tests(request, monkeypatch):
    if Path(str(request.node.path)).name in ASHEN_TEST_FILES:
        monkeypatch.setenv('LECTERN_ASHEN_COMPANY', '1')
