# Code Structure Review - Tasks

## 1. Scoring Services aufteilen

### 1.1 ScoringService in eigenes Modul extrahieren
- [x] `scoring/match_scoring.py` erstellen mit ScoringService Klasse
- [x] Nur Match-Scoring Logik übernehmen (_calculate_base_points, calculate_match_points, score_prediction, score_all_predictions_for_match)
- [x] Round-Multiplier und Joker-Multiplier Logik behalten
- [x] TYPE_CHECKING Imports für Match, MatchPrediction, Team verwenden
- [x] Tests: Bestehende test_scoring_service.py Tests müssen passieren

### 1.2 Champion-Scoring extrahieren
- [x] `scoring/champion_scoring.py` erstellen
- [x] get_current_champion_team() verschieben
- [x] update_live_champion_bonuses() verschieben
- [x] calculate_champion_points() verschieben
- [x] CHAMPION_POINTS Konstante mitnehmen
- [x] Tests: test_champion_scoring.py Tests müssen passieren

### 1.3 RankingService in eigenes Modul extrahieren
- [x] `scoring/ranking_service.py` erstellen mit RankingService Klasse
- [x] get_leaderboard_up_to_round() verschieben
- [x] get_current_leaderboard() verschieben
- [x] _calculate_rank_numbers() verschieben
- [x] Tests: test_ranking_service.py Tests müssen passieren

### 1.4 Services Facade erstellen
- [x] `scoring/services.py` zu Re-Export Facade umwandeln
- [x] Backward-kompatible Imports: `from scoring.services import ScoringService, RankingService`
- [x] Docstring hinzufügen der auf neue Module verweist
- [x] Alle imports in anderen Dateien bleiben unverändert

## 2. Signal-basiertes Scoring implementieren

### 2.1 Match-Signal definieren
- [x] `matches/signals.py` erstellen
- [x] `match_result_entered = Signal()` definieren mit Dokumentation
- [x] Signal-Parameter: sender, match

### 2.2 Signal-Receiver implementieren
- [x] `scoring/signals.py` erstellen
- [x] Receiver für match_result_entered: ruft ScoringService.score_all_predictions_for_match() auf
- [x] Receiver für Champion-Bonus bei Final: ruft update_live_champion_bonuses() auf
- [x] Error-Handling mit logging (wie aktuell in Match.save())

### 2.3 Match.save() auf Signal umstellen
- [x] Inline-Import von ScoringService entfernen
- [x] Signal-Import hinzufügen: `from matches.signals import match_result_entered`
- [x] Signal senden wenn goals_home und goals_away gesetzt
- [x] Tests: test_models.py Tests müssen passieren

### 2.4 AppConfig Signal-Registration
- [x] `scoring/apps.py` anpassen: signals in ready() importieren
- [x] `matches/apps.py` prüfen ob Signal-Import nötig
- [x] Verify: Signals werden bei Serverstart registriert

## 3. Inline-Imports aufräumen

### 3.1 scoring/match_scoring.py Imports aufräumen
- [x] Prüfen welche Inline-Imports nach Refactoring noch nötig
- [x] MatchPrediction, User, Match Imports nach oben verschieben wenn möglich
- [x] TYPE_CHECKING behalten für Type Hints

### 3.2 scoring/ranking_service.py Imports aufräumen
- [x] Prüfen welche Inline-Imports nach Refactoring noch nötig
- [x] User Import nach oben verschieben
- [x] LeaderboardSnapshot Import nach oben verschieben

### 3.3 Verbleibende Inline-Imports dokumentieren
- [x] Für jeden verbleibenden Inline-Import Kommentar warum nötig
- [x] # noqa Kommentare aktualisieren

## 4. Abschluss und Verifikation

### 4.1 Alle Tests ausführen
- [x] `pytest` - alle Tests müssen passieren
- [x] Keine neuen Test-Failures

### 4.2 Type Checking
- [x] `mypy .` - keine neuen Fehler
- [x] Import-Typen korrekt aufgelöst

### 4.3 Linting
- [x] `ruff check .` - keine neuen Warnungen
- [x] `ruff format .` - Code formatiert

### 4.4 Dokumentation aktualisieren
- [x] README falls nötig anpassen
- [x] docs/project/decisions.md mit Refactoring-Entscheidung ergänzen

---

## Akzeptanzkriterien

- [x] Alle bestehenden Tests passieren ohne Änderung
- [x] Keine neuen mypy Fehler
- [x] Keine neuen ruff Warnungen  
- [x] `from scoring.services import ScoringService, RankingService` funktioniert weiterhin
- [x] Match-Scoring wird weiterhin automatisch bei Match.save() ausgelöst
- [x] Champion-Bonus wird weiterhin bei Final-Änderungen aktualisiert
- [x] Inline-Imports in scoring/ reduziert von 10+ auf <3
