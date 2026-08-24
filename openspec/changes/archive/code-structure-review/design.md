# Code Structure Review - Design

## Context

Das Projekt ist eine Django-Anwendung für ein WM 2026 Tippspiel. Die Codebase ist funktional, hat aber strukturelle Probleme die Wartung und Erweiterbarkeit erschweren:

- `scoring/services.py` ist mit 700+ Zeilen und 2 Klassen zu groß
- 10+ Inline-Imports zur Vermeidung zirkulärer Abhängigkeiten
- Direkte Service-Aufrufe in Model `save()` Methoden
- Signals werden bereits in `users/signals.py` verwendet - dieses Pattern kann erweitert werden

## Goals / Non-Goals

**Goals:**
- Service-Module aufteilen für bessere Lesbarkeit
- Zirkuläre Imports durch Signals auflösen
- Import-Patterns konsistent halten
- Code-Navigation vereinfachen

**Non-Goals:**
- Funktionale Änderungen an der Scoring-Logik
- Änderungen an APIs oder Views
- Performance-Optimierungen
- Neue Features hinzufügen

## Decisions

### 1. Aufteilen von scoring/services.py

**Decision:** `scoring/services.py` in drei Module aufteilen:
- `scoring/match_scoring.py` - ScoringService für Punkteberechnung
- `scoring/ranking_service.py` - RankingService für Leaderboard
- `scoring/champion_scoring.py` - Champion-bezogene Scoring-Logik (extrahiert aus ScoringService)

**Rationale:** 
- Einzelne Module mit fokussiertem Zweck
- Bessere Testbarkeit
- Einfachere Code-Reviews
- `services.py` kann als re-export facade erhalten bleiben für Backward-Kompatibilität

**Alternatives considered:**
- Alles in einer Datei lassen: Abgelehnt - zu groß für effektive Wartung
- Pro-Klasse eigenes Modul ohne Facade: Würde alle Import-Statements ändern

### 2. Signals statt direkter Service-Aufrufe in Models

**Decision:** Match.save() soll ein Signal senden statt ScoringService direkt zu importieren.

```python
# matches/signals.py
match_result_entered = Signal()

# matches/models.py - in save()
if goals changed:
    match_result_entered.send(sender=self.__class__, match=self)

# scoring/signals.py - receiver
@receiver(match_result_entered)
def score_predictions_on_result(sender, match, **kwargs):
    ScoringService.score_all_predictions_for_match(match)
```

**Rationale:**
- Entkopplung von matches und scoring App
- Kein zirkulärer Import
- Testbar durch Signal-Mocking
- Konsistent mit bestehendem users/signals.py Pattern

**Alternatives considered:**
- Celery Tasks: Overkill für diesen Use-Case
- Management Commands: Nicht automatisch bei save()
- Behalten wie es ist: Funktioniert, aber schlechte Architektur

### 3. TYPE_CHECKING für Forward References behalten

**Decision:** `TYPE_CHECKING` Imports für Type Hints behalten.

```python
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from matches.models import Match
```

**Rationale:**
- Python Best Practice für zirkuläre Type Hints
- Keine Runtime-Kosten
- mypy funktioniert korrekt

### 4. Inline-Imports in Funktionen eliminieren wo möglich

**Decision:** Nach Signal-Refactoring sollten die meisten Inline-Imports unnötig werden.

**Verbleibende akzeptable Inline-Imports:**
- Lazy loading für optionale Features
- Test-spezifische Imports

**Zu eliminierende Inline-Imports:**
- `from predictions.models import MatchPrediction` innerhalb von ScoringService
- `from users.models import User` innerhalb von ScoringService
- `from matches.models import Match, Team` innerhalb von ScoringService

**Rationale:** Nach Aufteilung und Signal-Nutzung gibt es keine zirkulären Abhängigkeiten mehr.

## Technical Design

### Neue Dateistruktur

```
scoring/
├── __init__.py
├── services.py          # Re-export facade (ScoringService, RankingService)
├── match_scoring.py     # ScoringService Kern-Logik
├── ranking_service.py   # RankingService
├── champion_scoring.py  # Champion-bezogene Methoden
└── signals.py           # Signal receivers

matches/
├── signals.py           # Signal definitions (match_result_entered)
└── models.py            # Sauber ohne Service-Import
```

### Import-Hierarchie (nach Refactoring)

```
matches.models → matches.signals (sendet)
                      ↓
scoring.signals (empfängt) → scoring.services (aufruft)
                                   ↓
                            predictions.models
                            users.models
```

### Migration Path

1. Services aufteilen (ohne Breaking Changes)
2. Signals erstellen und verbinden
3. Match.save() auf Signal umstellen
4. Inline-Imports entfernen
5. Tests anpassen

## Risks

- **Risiko:** Signal-Receiver werden nicht aufgerufen wenn Apps nicht geladen
  - **Mitigation:** Signals in AppConfig.ready() importieren

- **Risiko:** Zeitliche Reihenfolge von Signals unklar
  - **Mitigation:** Dokumentation, keine Abhängigkeiten zwischen Receivers

- **Risiko:** Breaking Changes für externe Imports
  - **Mitigation:** services.py als Facade erhalten

## Testing Strategy

- Unit Tests für jeden neuen Service-Modul
- Integration Tests für Signal-Kette
- Alle bestehenden Tests müssen weiterhin passieren
- Signal-Mocking in Tests für Isolation
