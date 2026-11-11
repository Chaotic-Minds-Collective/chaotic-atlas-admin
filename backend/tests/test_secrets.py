"""Regression checks for private backend secret provisioning."""
import asyncio
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

from starlette.requests import Request
import httpx


BACKEND = Path(__file__).resolve().parents[1]


class SecretConfigurationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        for name in ('main.py', 'config.yaml'):
            shutil.copyfile(BACKEND / name, self.root / name)

    def load(self, values, dotenv=''):
        (self.root / '.env').write_text(dotenv)
        spec = importlib.util.spec_from_file_location('secret_test_app', self.root / 'main.py')
        module = importlib.util.module_from_spec(spec)
        # Game queries are outside these configuration/OAuth unit tests.
        a2s = ModuleType('valve.source.a2s')
        a2s.NoResponseError = type('NoResponseError', (Exception,), {})
        a2s.ServerQuerier = None
        with patch.dict(os.environ, values, clear=True), patch.dict(
            'sys.modules', {'valve.source.a2s': a2s}
        ):
            spec.loader.exec_module(module)
        return module

    def test_copied_example_rejects_session_placeholder(self):
        with self.assertRaisesRegex(RuntimeError, 'SESSION_SECRET'):
            self.load({}, (BACKEND / '.env.example').read_text())

    def test_missing_and_short_session_secrets_fail(self):
        for value in ('', 'short'):
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, 'SESSION_SECRET'):
                self.load({'SESSION_SECRET': value})

    def test_yaml_cannot_supply_discord_secret(self):
        with (self.root / 'config.yaml').open('a') as config:
            config.write('\n  client_secret: legacy-synthetic-value\n')
        for value in ('', '   '):
            with self.subTest(value=value), self.assertRaisesRegex(RuntimeError, 'DISCORD_CLIENT_SECRET'):
                self.load({'SESSION_SECRET': 's' * 32, 'DISCORD_CLIENT_SECRET': value})

    def test_dotenv_and_environment_precedence(self):
        dotenv = 'SESSION_SECRET=' + 's' * 32 + '\nDISCORD_CLIENT_SECRET=synthetic-file-value\n'
        self.assertEqual(self.load({}, dotenv).discord_client_secret, 'synthetic-file-value')
        module = self.load({'DISCORD_CLIENT_SECRET': 'synthetic-env-value'}, dotenv)
        self.assertEqual(module.discord_client_secret, 'synthetic-env-value')

    def test_callback_uses_private_secret_and_preserves_identity_contract(self):
        module = self.load({'SESSION_SECRET': 's' * 32, 'DISCORD_CLIENT_SECRET': 'synthetic-env-value'})
        calls = []

        def respond(request):
            calls.append(request)
            if request.url.path.endswith('/token'):
                self.assertIn(b'client_secret=synthetic-env-value', request.content)
                return httpx.Response(200, json={'access_token': 'synthetic-token'})
            return httpx.Response(200, json={'id': 'test-id', 'username': 'tester', 'email': 'omit@example.invalid'})

        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        request = Request({'type': 'http', 'session': {}})
        with patch.object(module.httpx, 'AsyncClient', return_value=client):
            response = asyncio.run(module.auth_callback('synthetic-code', request))
        self.assertEqual(len(calls), 2)
        self.assertEqual(request.session, {'user': {'id': 'test-id', 'username': 'tester'}})
        self.assertEqual(response.headers['location'], '/')


if __name__ == '__main__':
    unittest.main()
