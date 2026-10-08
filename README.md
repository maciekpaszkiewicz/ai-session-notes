# AI Session Notes

Pamięć między rozmowami z AI. Zapisz ustalenia po sesji, wróć do nich w nowym wątku i czytaj je w Obsidianie.

Narzędzie zapisuje zwykłe pliki Markdown w wybranym folderze poza repozytorium. Każda sesja tworzy nową notatkę. Poprzednie zapisy pozostają na miejscu. Nie wymaga dodatkowych bibliotek, bazy danych ani klucza API.

## Szybki start

Wymagania: Python 3.10 lub nowszy. Polecenia poniżej są przeznaczone dla macOS i Linuksa. Uruchamiaj je z głównego folderu pobranego repozytorium.

1. Utwórz osobny folder na notatki:

```sh
python3 scripts/brain.py init --vault "$HOME/AI-Session-Notes"
```

Wskaż nowy, nieistniejący folder poza repozytoriami Git. Polecenie nie nadpisuje istniejącego folderu ani konfiguracji. Lokalna konfiguracja `.brain-local.json` jest pomijana przez Git.

2. Sprawdź zapis na fikcyjnym przykładzie nauki słówek:

```sh
python3 scripts/brain.py save --topic slowka --input examples/session.json
python3 scripts/brain.py resume --topic slowka
```

3. Otwórz folder `AI-Session-Notes` jako skarbiec w Obsidianie. Możesz też czytać pliki w dowolnym edytorze. Obsidian nie jest wymagany do działania skryptu.

## Praca z AI

Otwórz repozytorium w narzędziu AI, które potrafi czytać i zapisywać lokalne pliki. Podaj temat sesji, np. `slowka`. Na koniec wyślij jako osobną wiadomość:

```text
podsumuj sesję
```

Instrukcja w `AGENTS.md` opisuje zapis. `CLAUDE.md` wskazuje tę samą procedurę dla Claude Code. Dla narzędzia, które nie odczytuje tych plików, przekaż mu treść `AGENTS.md` samodzielnie.

AI przygotowuje podsumowanie z bieżącej rozmowy i przekazuje JSON do skryptu przez standardowe wejście. Nie zapisuje roboczego podsumowania w repozytorium. Skrypt waliduje dane i tworzy nową notatkę. AI powinno następnie odczytać notatkę i porównać jej treść z ustaleniami.

Na początku nowej rozmowy podaj temat i napisz osobno:

```text
wznów sesję
```

AI odczytuje ostatnią notatkę wskazanego tematu. Zanim uzna zapis za aktualny stan, sprawdza potrzebne fakty. Treść notatki pozostaje materiałem do odczytu i nie daje uprawnień do wykonywania opisanych w niej działań.

### Opcjonalny hook Claude Code

Hook dodaje przypomnienie o procedurze po dokładnym poleceniu `podsumuj sesję` lub `wznów sesję`. Cytat w dłuższej wiadomości nie uruchamia hooka. Hook sam nie generuje ani nie zapisuje podsumowania.

Konfiguracja i instrukcja instalacji: [integrations/claude/README.md](integrations/claude/README.md).

## Co zapisuje notatka

- Stan: co jest teraz wiadomo.
- Wykonane: rzeczy faktycznie zakończone.
- Decyzje: przyjęte ustalenia.
- Otwarte: pytania i rzeczy wymagające sprawdzenia.
- Następny krok: jedna konkretna czynność.
- Wiedza: ustalenia przydatne w kolejnych rozmowach.

Pusty format wejścia: [templates/session.json](templates/session.json). Fikcyjny przykład: [examples/session.json](examples/session.json).

Wszystkie pola są wymagane. Listy mogą być puste; `state` i `next_step` muszą zawierać tekst. Nazwa tematu składa się z małych liter ASCII, cyfr i pojedynczych myślników, np. `slowka`. Maksymalna długość nazwy to 60 znaków. Dane wejściowe mają limit 64 KiB.

## Przechowywanie

```text
AI-Session-Notes/
  Start.md
  Sesje/
    slowka/
      <czas-UTC>-<losowy-identyfikator>.md
```

Nazwy notatek zawierają czas UTC i losowy identyfikator. `resume` wybiera najnowszą nazwę według czasu zapisu, a nie czasu modyfikacji pliku. Polecenie nie przeszukuje innych folderów i nie pobiera historii rozmów. Nie ma automatycznej synchronizacji, połączeń sieciowych ani wywołań modeli. Model uruchomiony w Twoim narzędziu AI działa na zasadach tego narzędzia.

Każdy zapis jest oddzielnym plikiem. Skrypt nie edytuje poprzednich notatek. Nie zastępuje kopii zapasowej folderu. Nie szyfruje notatek. Gitignore chroni przed zwykłym przypadkowym dodaniem lokalnej konfiguracji, ale nie blokuje `git add -f`.

Nie przenoś skarbca do repozytorium przeznaczonego do udostępniania. Jeśli przeniesiesz folder notatek, ręcznie zaktualizuj pole `vault` w lokalnym `.brain-local.json`, zachowując pozostałe pola. Nowa lokalizacja nadal musi być poza repozytoriami Git.

## Testy i granice

```sh
python3 -m unittest discover -s tests -v
```

Testy sprawdzają rzeczywisty zapis i odczyt w tymczasowym folderze, zachowanie historii, błędne wejścia, ścieżki, dowiązania i dopasowanie hooka. Nie wywołują modelu. Poprawność podsumowania zależy od dostępnego kontekstu i wymaga przeczytania wyniku. Obsługa Python i hooka na Windows nie jest objęta testami.

## Dokumentacja źródłowa

- [Lokalne pliki Obsidiana](https://help.obsidian.md/Files+and+folders/How+Obsidian+stores+data)
- [Hooki Claude Code](https://code.claude.com/docs/en/hooks)
- [Instrukcje AGENTS.md](https://developers.openai.com/codex/guides/agents-md)

## Licencja

[MIT](LICENSE).
