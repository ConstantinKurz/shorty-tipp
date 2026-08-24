# Code Structure Review

## Why

Die aktuelle Codebase hat einige strukturelle Probleme:

1. **Mehrere Klassen in einer Datei**: `scoring/services.py` enthält `ScoringService` (~300 Zeilen) und `RankingService` (~200 Zeilen). Diese könnten in separate Module aufgeteilt werden.

2. **Viele Inline-Imports**: Es gibt 10+ Imports innerhalb von Funktionen (statt am Dateianfang). Diese sind nötig um zirkuläre Imports zu vermeiden, deuten aber auf architektonische Probleme hin.

3. **Zirkuläre Abhängigkeiten**: Das Match-Model importiert ScoringService in der `save()` Methode. Services importieren Models innerhalb von Methoden.

4. **Konsolidierungspotential**: Einige Patterns könnten vereinheitlicht werden.

## What Changes

- Refaktorierung der Service-Module für bessere Separation of Concerns
- Verwendung von Django Signals statt direkter Imports in Model-save()
- Auflösung zirkulärer Abhängigkeiten durch bessere Architektur
- Vereinheitlichung von Import-Patterns

## Capabilities

### Modified Capabilities

- `scoring-service`: Aufteilen in separate Module (`scoring/match_scoring.py`, `scoring/ranking_service.py`)
- `model-scoring-trigger`: Ersetzen des direkten ScoringService-Imports im Match.save() durch Django Signal
- `import-patterns`: Konsolidierung der Imports auf Dateiebene wo möglich

## Impact

- Keine funktionalen Änderungen - rein strukturelles Refactoring
- Bessere Testbarkeit durch entkoppelte Module
- Einfachere Navigation im Code
- Klarere Abhängigkeitsstruktur
- Keine Breaking Changes für externe APIs
