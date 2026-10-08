#!/usr/bin/env python3
"""Local, append-only session notes. Python standard library only."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import uuid

REPO = Path(__file__).resolve().parents[1]
CONFIG = REPO / '.brain-local.json'
MAX_INPUT = 65536
MAX_NOTE = 131072
TOPIC = re.compile(r'[a-z0-9]+(?:-[a-z0-9]+)*')
NOTE_NAME = re.compile(r'\d{8}T\d{12}Z-[0-9a-f]{32}\.md')
FIELDS = ('state', 'done', 'decisions', 'open_questions', 'next_step', 'knowledge')


def fail(message):
    raise ValueError(message)


def check_path(path):
    """Reject links in managed paths, including changed ancestor directories."""
    for part in (path, *path.parents):
        if part.is_symlink():
            fail('Dowiązania symboliczne nie są obsługiwane.')


def outside_git(path):
    if path == REPO or REPO in path.parents:
        fail('Folder notatek musi być poza repozytorium.')
    if any((parent / '.git').exists() for parent in (path, *path.parents)):
        fail('Folder notatek nie może znajdować się w repozytorium Git.')


def read_small(path, limit):
    check_path(path)
    with path.open('rb') as stream:
        data = stream.read(limit + 1)
    if len(data) > limit:
        fail('Przekroczono limit wielkości pliku.')
    return data.decode('utf-8')


def publish_new(path, text):
    """Publish a complete file without replacing any existing destination."""
    check_path(path)
    fd, temporary = tempfile.mkstemp(prefix='.writing-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='\n') as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path)
    finally:
        os.unlink(temporary)


def initialize(vault):
    check_path(CONFIG)
    if CONFIG.exists():
        fail('Konfiguracja już istnieje. Nie została zmieniona.')
    root = Path(vault).expanduser().resolve()
    outside_git(root)
    if root.exists():
        fail('Wybierz nowy, nieistniejący folder na notatki.')
    root.mkdir(mode=0o700, parents=True)
    (root / 'Sesje').mkdir(mode=0o700)
    store_id = uuid.uuid4().hex
    publish_new(root / '.brain-store.json', json.dumps({'id': store_id}) + '\n')
    publish_new(root / 'Start.md', '# Pamięć sesji\n\nNotatki znajdują się w folderze Sesje, pod nazwami tematów. Każdy zapis jest osobnym plikiem.\n\nOtwórz temat w panelu plików. Najnowszy zapis ma najwyższą nazwę w kolejności alfabetycznej; czas w nazwie jest podany w UTC.\n\nPrzed wznowieniem sprawdź aktualność ustaleń.\n')
    config = {'version': 1, 'vault': str(root), 'id': store_id}
    publish_new(CONFIG, json.dumps(config, ensure_ascii=False, indent=2) + '\n')
    return root


def store():
    config = json.loads(read_small(CONFIG, MAX_INPUT))
    if not isinstance(config, dict) or config.get('version') != 1:
        fail('Nieprawidłowy format konfiguracji.')
    if not isinstance(config.get('vault'), str) or not isinstance(config.get('id'), str):
        fail('Nieprawidłowy format konfiguracji.')
    root = Path(config['vault'])
    if not root.is_absolute() or '..' in root.parts:
        fail('Konfiguracja wymaga pełnej ścieżki folderu.')
    check_path(root)
    outside_git(root)
    marker = json.loads(read_small(root / '.brain-store.json', MAX_INPUT))
    if not isinstance(marker, dict) or marker.get('id') != config['id']:
        fail('Folder nie odpowiada zapisanej konfiguracji.')
    check_path(root / 'Sesje')
    if not (root / 'Sesje').is_dir():
        fail('Brak folderu Sesje.')
    return root


def validate_topic(topic):
    if not isinstance(topic, str) or len(topic) > 60 or not TOPIC.fullmatch(topic):
        fail('Temat: małe litery ASCII, cyfry i pojedyncze myślniki; do 60 znaków.')
    return topic


def validate(data):
    if not isinstance(data, dict) or set(data) != set(FIELDS):
        fail('Dane muszą zawierać dokładnie pola z templates/session.json.')
    for key in FIELDS:
        values = data[key]
        if key in ('state', 'next_step'):
            values = [values]
        elif not isinstance(values, list) or len(values) > 100:
            fail('Pole listy ma nieprawidłowy format lub zbyt wiele elementów.')
        for value in values:
            if not isinstance(value, str) or not value.strip() or len(value) > 8000:
                fail('Elementy muszą być niepustymi tekstami, do 8000 znaków.')
            if any(ord(c) < 32 and c not in '\n\t' for c in value):
                fail('Tekst zawiera niedozwolone znaki sterujące.')
    return data


def plain(text):
    """Keep supplied notes as text, not HTML or active Markdown embeds."""
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    for character in '\\`*_{}[]()#!|':
        text = text.replace(character, '\\' + character)
    return text


def render(topic, data, timestamp):
    sections = [('state', 'Stan'), ('done', 'Wykonane'), ('decisions', 'Decyzje'),
                ('open_questions', 'Otwarte'), ('next_step', 'Następny krok'),
                ('knowledge', 'Wiedza')]
    parts = [f'# {topic}', f'Zapis: {timestamp.isoformat()}']
    for key, title in sections:
        value = data[key]
        if isinstance(value, list):
            body = '\n'.join('- ' + plain(item).replace('\n', '\n  ') for item in value)
            body = body or '(brak wpisów)'
        else:
            body = plain(value)
        parts.append(f'## {title}\n\n{body}')
    return '\n\n'.join(parts) + '\n'


def save(topic, data):
    validate_topic(topic)
    validate(data)
    root = store()
    directory = root / 'Sesje' / topic
    check_path(directory)
    directory.mkdir(mode=0o700, exist_ok=True)
    stamp = datetime.now(timezone.utc)
    name = stamp.strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid.uuid4().hex + '.md'
    note = render(topic, data, stamp)
    if len(note.encode('utf-8')) > MAX_NOTE:
        fail('Wynikowa notatka jest zbyt duża.')
    target = directory / name
    publish_new(target, note)
    if read_small(target, MAX_NOTE) != note:
        fail('Nie udało się potwierdzić zawartości notatki.')
    return target


def resume(topic):
    validate_topic(topic)
    directory = store() / 'Sesje' / topic
    check_path(directory)
    if not directory.is_dir():
        fail('Brak notatek dla tego tematu.')
    notes = sorted(p for p in directory.iterdir() if NOTE_NAME.fullmatch(p.name))
    if not notes:
        fail('Brak notatek dla tego tematu.')
    latest = notes[-1]
    return latest, read_small(latest, MAX_NOTE)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    init = commands.add_parser('init', help='Utwórz osobny folder notatek')
    init.add_argument('--vault', required=True)
    write = commands.add_parser('save', help='Zapisz nową sesję z JSON')
    write.add_argument('--topic', required=True)
    write.add_argument('--input', type=Path, help='Domyślnie odczyt ze stdin')
    read = commands.add_parser('resume', help='Odczytaj ostatni zapis tematu')
    read.add_argument('--topic', required=True)
    args = parser.parse_args()
    try:
        if args.command == 'init':
            print(initialize(args.vault))
        elif args.command == 'save':
            if args.input:
                payload = read_small(args.input, MAX_INPUT)
            else:
                raw = sys.stdin.buffer.read(MAX_INPUT + 1)
                if len(raw) > MAX_INPUT:
                    fail('Przekroczono limit wejścia 64 KiB.')
                payload = raw.decode('utf-8')
            print(save(args.topic, json.loads(payload)))
        else:
            path, note = resume(args.topic)
            print(f'Źródło: {path}\n\n{note}', end='')
        return 0
    except (ValueError, OSError) as error:
        if isinstance(error, OSError):
            print('Błąd dostępu do pliku lub folderu. Sprawdź konfigurację i uprawnienia.', file=sys.stderr)
        else:
            print('Błąd: ' + str(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
