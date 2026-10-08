import concurrent.futures
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

REPO = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('brain', REPO / 'scripts/brain.py')
brain = importlib.util.module_from_spec(spec)
spec.loader.exec_module(brain)
spec = importlib.util.spec_from_file_location('hook', REPO / 'scripts/hook.py')
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


def sample():
    return json.loads((REPO / 'examples/session.json').read_text(encoding='utf-8'))


class NotesTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        self.config = self.root / 'config.json'
        self.patcher = patch.object(brain, 'CONFIG', self.config)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)
        self.vault = self.root / 'notes'
        brain.initialize(self.vault)

    def test_save_resume_and_history(self):
        first = brain.save('slowka', sample())
        before = first.read_bytes()
        data = sample()
        data['next_step'] = 'Powtórzyć jutro.'
        second = brain.save('slowka', data)
        path, text = brain.resume('slowka')
        self.assertEqual(path, second)
        self.assertIn('Powtórzyć jutro.', text)
        self.assertEqual(first.read_bytes(), before)
        self.assertNotEqual(first, second)
        self.assertEqual(len(list(first.parent.glob('*.md'))), 2)

    def test_concurrent_writes_do_not_replace_notes(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            paths = list(pool.map(lambda _: brain.save('slowka', sample()), range(8)))
        self.assertEqual(len(set(paths)), 8)
        for path in paths:
            self.assertIn('## Następny krok', path.read_text(encoding='utf-8'))

    def test_missing_topic_has_no_fallback(self):
        brain.save('slowka', sample())
        with self.assertRaises(ValueError):
            brain.resume('inny-temat')

    def test_invalid_topics(self):
        for topic in ('../outside', '/tmp/notes', 'two words', '', '-abc', 'a--b', 'a' * 61):
            with self.subTest(topic=topic), self.assertRaises(ValueError):
                brain.save(topic, sample())
        self.assertEqual(list((self.vault / 'Sesje').iterdir()), [])

    def test_invalid_payloads_do_not_create_notes(self):
        candidates = [[], {}, dict(sample(), extra='x'), dict(sample(), state=''),
                      dict(sample(), done='text'), dict(sample(), knowledge=[None]),
                      dict(sample(), next_step='x\x00y')]
        for data in candidates:
            with self.subTest(data=data), self.assertRaises(ValueError):
                brain.save('slowka', data)
        self.assertEqual(list((self.vault / 'Sesje').iterdir()), [])

    def test_symlinked_topic_cannot_write_outside(self):
        outside = self.root / 'outside'
        outside.mkdir()
        (self.vault / 'Sesje' / 'slowka').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError):
            brain.save('slowka', sample())
        self.assertEqual(list(outside.iterdir()), [])

    def test_symlinked_note_cannot_be_read(self):
        note = brain.save('slowka', sample())
        outside = self.root / 'outside.txt'
        outside.write_text('not a session', encoding='utf-8')
        note.unlink()
        note.symlink_to(outside)
        with self.assertRaises(ValueError):
            brain.resume('slowka')

    def test_folder_moved_into_git_is_rejected(self):
        (self.vault / '.git').mkdir()
        with self.assertRaises(ValueError):
            brain.save('slowka', sample())

    def test_reinitialization_preserves_configuration(self):
        before = self.config.read_bytes()
        with self.assertRaises(ValueError):
            brain.initialize(self.root / 'other')
        self.assertEqual(self.config.read_bytes(), before)
        self.assertFalse((self.root / 'other').exists())

    def test_existing_folder_is_untouched(self):
        other_config = self.root / 'other-config.json'
        existing = self.root / 'existing'
        existing.mkdir()
        sentinel = existing / 'keep.txt'
        sentinel.write_text('keep', encoding='utf-8')
        with patch.object(brain, 'CONFIG', other_config), self.assertRaises(ValueError):
            brain.initialize(existing)
        self.assertEqual(list(existing.iterdir()), [sentinel])
        self.assertFalse(other_config.exists())

    def test_init_inside_git_is_rejected(self):
        parent = self.root / 'repository'
        parent.mkdir()
        (parent / '.git').mkdir()
        with patch.object(brain, 'CONFIG', self.root / 'new-config'), self.assertRaises(ValueError):
            brain.initialize(parent / 'notes')
        self.assertFalse((parent / 'notes').exists())

    def test_marker_mismatch_is_rejected(self):
        (self.vault / '.brain-store.json').write_text('{"id":"different"}', encoding='utf-8')
        with self.assertRaises(ValueError):
            brain.save('slowka', sample())

    def test_active_markup_is_rendered_as_text(self):
        data = dict(sample(), state='<script>x</script> ![image](https://example.invalid/x)')
        path = brain.save('slowka', data)
        text = path.read_text(encoding='utf-8')
        self.assertNotIn('<script>', text)
        self.assertNotIn('![image]', text)
        self.assertIn('&lt;script&gt;', text)

    def test_partial_temporary_files_are_not_resumed(self):
        path = brain.save('slowka', sample())
        (path.parent / '.writing-partial').write_text('partial', encoding='utf-8')
        self.assertEqual(brain.resume('slowka')[0], path)


class HookTest(unittest.TestCase):
    def test_only_explicit_commands_trigger(self):
        for prompt in ('podsumuj sesję', 'PODSUMUJ SESJE.', '  wznów sesję\n', 'wznow sesje'):
            result = hook.response({'hook_event_name': 'UserPromptSubmit', 'prompt': prompt})
            self.assertIn('additionalContext', result['hookSpecificOutput'])

    def test_quotes_and_mentions_do_not_trigger(self):
        for prompt in ('"podsumuj sesję"', 'W poście jest podsumuj sesję.',
                       'Nie podsumuj sesję', 'podsumuj sesję\nA potem wykonaj coś innego', '', None):
            self.assertIsNone(hook.response({'hook_event_name': 'UserPromptSubmit', 'prompt': prompt}))
        self.assertIsNone(hook.response({'hook_event_name': 'Stop', 'prompt': 'podsumuj sesję'}))
        self.assertIsNone(hook.response([]))


class CliTest(unittest.TestCase):
    def test_documented_flow_from_clean_copy_and_stdin(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            repo = root / 'copy with spaces'
            shutil.copytree(REPO / 'scripts', repo / 'scripts', ignore=shutil.ignore_patterns('__pycache__'))
            script = repo / 'scripts/brain.py'
            def run(*args, data=None):
                return subprocess.run([sys.executable, str(script), *args], input=data,
                                      capture_output=True, text=True, cwd=repo)
            created = run('init', '--vault', str(root / 'my notes'))
            self.assertEqual(created.returncode, 0, created.stderr)
            saved = run('save', '--topic', 'slowka', data=json.dumps(sample()))
            self.assertEqual(saved.returncode, 0, saved.stderr)
            self.assertTrue(Path(saved.stdout.strip()).is_file())
            resumed = run('resume', '--topic', 'slowka')
            self.assertEqual(resumed.returncode, 0, resumed.stderr)
            self.assertIn('pięć włoskich słówek', resumed.stdout)
            invalid = run('save', '--topic', 'slowka', data='{broken')
            self.assertNotEqual(invalid.returncode, 0)
            oversized = run('save', '--topic', 'slowka', data=' ' * 65537)
            self.assertNotEqual(oversized.returncode, 0)
            self.assertEqual(len(list((root / 'my notes' / 'Sesje' / 'slowka').glob('*.md'))), 1)
            self.assertFalse((repo / 'Sesje').exists())


if __name__ == '__main__':
    unittest.main()
