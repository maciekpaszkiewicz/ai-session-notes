# Opcjonalny hook Claude Code

Integracja dotyczy pracy z głównego katalogu tego repozytorium na macOS lub Linuksie. Wymaga polecenia `python3` dostępnego w środowisku Claude Code.

Przeczytaj `settings.example.json` oraz `scripts/hook.py`. Skopiuj sekcję `UserPromptSubmit` z przykładu do `hooks` w pliku `.claude/settings.local.json` w głównym folderze repozytorium. Jeśli plik lub sekcja już istnieją, zachowaj ich pozostałą zawartość i dodaj wpis do tablicy. Jeśli pliku nie ma, utwórz folder `.claude` i zapisz pełną zawartość przykładu jako `settings.local.json`.

Zrestartuj sesję Claude Code i zaakceptuj zaufanie do katalogu, jeśli program o nie poprosi. Integracja nie zmienia globalnych ustawień i nie włącza automatycznej zgody na polecenia.

Hook reaguje tylko na całą wiadomość: `podsumuj sesję`, `podsumuj sesje`, `wznów sesję` lub `wznow sesje`. Obsługuje wielkie litery i końcową kropkę. Temat podaj wcześniej w rozmowie. Wiadomość „W poście napisałem podsumuj sesję” niczego nie uruchamia.

Sprawdzenie samego hooka:

```sh
printf '%s' '{"hook_event_name":"UserPromptSubmit","prompt":"podsumuj sesję"}' | python3 scripts/hook.py
```

Powinien zwrócić JSON z `additionalContext`. To przypomnienie dla modelu. Rzeczywisty zapis następuje dopiero po wywołaniu `brain.py save`; jego powodzenie potwierdza odczyt notatki.

Źródło formatu: [dokumentacja hooków Claude Code](https://code.claude.com/docs/en/hooks). Integracja nie jest hookiem dla innych narzędzi AI; mogą one korzystać z `AGENTS.md` i CLI.
