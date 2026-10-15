"""Real dependency construction and Linux SQLite fallback regression checks."""
import os
import sqlite3
import sys
import types
import tempfile
import unittest
from unittest.mock import patch
from runtime import configure_runtime
from review import build_quick_crew


class RuntimeTests(unittest.TestCase):
    def test_old_sqlite_fallback(self):
        replacement = types.ModuleType('pysqlite3')
        with patch.object(sqlite3, 'sqlite_version_info', (3, 34, 0)):
            with patch.dict(sys.modules, {'pysqlite3': replacement}):
                configure_runtime()
                self.assertIs(sys.modules['sqlite3'], replacement)

    def test_real_crew_construction_without_network(self):
        expanduser = os.path.expanduser
        with tempfile.TemporaryDirectory() as directory:
            # Isolate dependency support files from the user's CrewAI profile.
            with patch('appdirs.user_data_dir', return_value=directory), patch(
                'os.path.expanduser', side_effect=lambda path: directory
                if path in ('~/Library/Application Support', '~/.local/share')
                else expanduser(path)
            ):
                crew = build_quick_crew('Resume experience ' * 20,
                                        'Required experience ' * 20,
                                        'offline-test-key', 'openai/gpt-oss-120b')
        self.assertEqual(len(crew.agents), 1)
        self.assertEqual(len(crew.tasks), 1)
        self.assertFalse(crew.memory)
        self.assertFalse(crew.agents[0].allow_delegation)
        self.assertEqual(os.environ['OTEL_SDK_DISABLED'], 'true')


if __name__ == '__main__':
    unittest.main()
