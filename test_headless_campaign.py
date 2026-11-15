"""Regression tests for running the campaign engine without the desktop UI."""

import subprocess
import sys
import unittest


class HeadlessCampaignTests(unittest.TestCase):
    def test_campaign_can_save_load_and_advance_without_ui(self):
        script = r"""
from pathlib import Path
import sys
import tempfile

from management import CampaignState, advance_turn, load_campaign, save_campaign

with tempfile.TemporaryDirectory() as temporary_directory:
    path = Path(temporary_directory) / "campaign.json"

    campaign = CampaignState()
    save_campaign(campaign, path)
    restored = load_campaign(path)

    assert restored.campaign_id == campaign.campaign_id
    assert restored.turn_number == 1

    advance_turn(restored)

    assert restored.turn_number == 2
    assert "tkinter" not in sys.modules
    assert "ui.app" not in sys.modules
"""

        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()