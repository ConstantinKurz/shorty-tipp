# Email Notifications - Tasks

## 1. Notifications App erstellen

### 1.1 App-Struktur anlegen
- [x] `python manage.py startapp notifications` ausführen
- [x] App in `INSTALLED_APPS` registrieren
- [x] `notifications/management/commands/` Verzeichnisse erstellen
- [x] `notifications/tests/` Verzeichnis erstellen
- [x] `notifications/templates/notifications/emails/` Verzeichnisse erstellen

**Scope:** Nur Verzeichnisstruktur und App-Registrierung
**Out of Scope:** Implementierung der Services oder Commands
**Acceptance Criteria:**
- App ist in INSTALLED_APPS
- Verzeichnisstruktur wie in Design beschrieben
- `python manage.py check` läuft ohne Fehler

---

## 2. Settings und Konfiguration

### 2.1 E-Mail-Settings erweitern
- [x] `LEADERBOARD_ADMIN_EMAIL` Setting hinzufügen
- [x] `DEFAULT_FROM_EMAIL` Setting hinzufügen (falls nicht vorhanden)
- [x] Environment-Variablen dokumentieren

**Scope:** Settings in base.py und Dokumentation
**Out of Scope:** SMTP-Konfiguration für Production
**Acceptance Criteria:**
- Settings lesbar aus Environment-Variablen
- Sinnvolle Defaults für Development

---

## 3. E-Mail Service implementieren

### 3.1 EmailService Grundgerüst
- [x] `notifications/services.py` erstellen
- [x] `EmailService` Klasse anlegen
- [x] Hilfsmethoden für Template-Rendering
- [x] Fehlerbehandlung und Logging

**Scope:** Grundstruktur der Service-Klasse
**Out of Scope:** Spezifische E-Mail-Methoden
**Acceptance Criteria:**
- Service-Klasse existiert
- Logging konfiguriert

### 3.2 Leaderboard E-Mail Methode
- [x] `send_leaderboard_to_admin()` implementieren
- [x] Aktuellsten Snapshot laden
- [x] Template rendern
- [x] E-Mail senden
- [x] Return-Wert mit Erfolg/Fehler

**Scope:** Leaderboard-E-Mail Logik
**Out of Scope:** Template-Erstellung
**Acceptance Criteria:**
- Methode sendet E-Mail mit Leaderboard-Daten
- Fehlerfall bei fehlendem Snapshot behandelt
- Fehlerfall bei fehlender Admin-E-Mail behandelt
**Required Tests:**
- Test mit gemocktem E-Mail-Backend
- Test bei fehlendem Snapshot
- Test bei fehlender Admin-E-Mail

### 3.3 Missing Predictions Finder
- [x] `get_users_with_missing_predictions()` implementieren
- [x] Spiele in nächsten 24h finden
- [x] Nutzer ohne Tipp für diese Spiele finden
- [x] Dict mapping User → List[Match] zurückgeben

**Scope:** Query-Logik für fehlende Tipps
**Out of Scope:** E-Mail-Versand
**Acceptance Criteria:**
- Findet nur Spiele mit kickoff > now und < now + 24h
- Findet nur aktive Nutzer
- Ignoriert Spiele mit bestehendem Tipp
**Required Tests:**
- Test mit Spielen in verschiedenen Zeitfenstern
- Test mit teilweise getippten Spielen
- Test mit inaktiven Nutzern

### 3.4 Prediction Reminder E-Mail Methode
- [x] `send_prediction_reminder(user, matches)` implementieren
- [x] Template rendern mit Nutzer und Match-Liste
- [x] E-Mail an user.email senden
- [x] Return-Wert mit Erfolg/Fehler

**Scope:** Einzelne Reminder-E-Mail senden
**Out of Scope:** Batch-Versand
**Acceptance Criteria:**
- E-Mail wird an korrekte Adresse gesendet
- Alle Matches sind im Template aufgeführt
- Fehlerbehandlung bei ungültiger E-Mail
**Required Tests:**
- Test mit gemocktem E-Mail-Backend
- Test mit mehreren Matches

---

## 4. E-Mail Templates erstellen

### 4.1 Leaderboard Report Templates
- [x] `leaderboard_report.txt` erstellen
- [x] `leaderboard_report.html` erstellen (optional, minimal)
- [x] Snapshot-Datum und Rankings anzeigen
- [x] Deutsche Texte

**Scope:** Template-Dateien
**Out of Scope:** Komplexes HTML-Styling
**Acceptance Criteria:**
- Lesbarer Text mit Ranking-Tabelle
- Datum des Snapshots sichtbar

### 4.2 Prediction Reminder Templates
- [x] `prediction_reminder.txt` erstellen
- [x] `prediction_reminder.html` erstellen (optional, minimal)
- [x] Nutzername, Match-Liste, Link zur Tipp-Seite
- [x] Deutsche Texte

**Scope:** Template-Dateien
**Out of Scope:** Komplexes HTML-Styling
**Acceptance Criteria:**
- Persönliche Anrede
- Liste der fehlenden Tipps mit Kickoff-Zeit
- Link zum Tippen

---

## 5. Notification Daemon implementieren

### 5.1 notification_daemon Command
- [x] `notifications/management/commands/notification_daemon.py` erstellen
- [x] Endlosschleife mit `self.running` Flag
- [x] Signal-Handler für SIGTERM/SIGINT (graceful shutdown)
- [x] `--once` Flag für Test-Modus
- [x] `--interval` Option (Default: 3600 Sekunden)
- [x] `--leaderboard-hour` Option (Default: 20)
- [x] `--reminder-hour` Option (Default: 10)
- [x] Daily-Tracking mit `last_leaderboard_date` und `last_reminder_date`
- [x] Logging für gesendete E-Mails

**Scope:** Daemon Command analog zu `update_matches.py`
**Out of Scope:** E-Mail-Logik (in Service)
**Acceptance Criteria:**
- `python manage.py notification_daemon` startet Endlosschleife
- `python manage.py notification_daemon --once` führt einmal aus und beendet
- Graceful shutdown bei SIGTERM/SIGINT
- E-Mails werden nur einmal pro Tag gesendet
- Konfigurierbare Uhrzeiten
**Required Tests:**
- Test mit `--once` Flag
- Test dass E-Mails nicht doppelt gesendet werden
- Test für konfigurierbare Uhrzeiten

---

## 6. Tests

### 6.1 Unit Tests für EmailService
- [x] `notifications/tests/test_email_service.py` erstellen
- [x] Tests für `send_leaderboard_to_admin()`
- [x] Tests für `get_users_with_missing_predictions()`
- [x] Tests für `send_prediction_reminder()`

**Scope:** Unit Tests mit Mocks
**Out of Scope:** Integration Tests
**Acceptance Criteria:**
- Alle Service-Methoden getestet
- Edge Cases abgedeckt

### 6.2 Tests für Notification Daemon
- [x] `notifications/tests/test_notification_daemon.py` erstellen
- [x] Test für `--once` Modus
- [x] Test dass Daily-Tracking funktioniert
- [x] Test für konfigurierbare Uhrzeiten

**Scope:** Daemon-Tests
**Out of Scope:** E-Mail-Delivery Tests
**Acceptance Criteria:**
- Daemon kann mit `--once` getestet werden
- Daily-Tracking verhindert doppelte E-Mails

---

## 7. Dokumentation

### 7.1 README und docs aktualisieren
- [ ] Notification Daemon in README dokumentieren
- [ ] Environment-Variablen dokumentieren
- [ ] Docker/Systemd Beispiele hinzufügen

**Scope:** Dokumentation
**Out of Scope:** Detaillierte Deployment-Anleitung
**Acceptance Criteria:**
- Daemon-Usage dokumentiert
- Konfigurationsoptionen dokumentiert

---

## Akzeptanzkriterien (Gesamt)

- [x] `python manage.py notification_daemon` startet Endlosschleife
- [x] `python manage.py notification_daemon --once` führt einmal aus
- [ ] Leaderboard-E-Mail wird täglich zur konfigurierten Uhrzeit gesendet (Daemon muss im Deployment laufen)
- [ ] Reminder-E-Mails werden täglich zur konfigurierten Uhrzeit gesendet (Daemon muss im Deployment laufen)
- [x] E-Mails werden nur einmal pro Tag gesendet (Daily-Tracking)
- [x] Graceful shutdown funktioniert
- [ ] Alle Tests passieren (auf diesem Branch neu portiert, noch zu verifizieren)
- [ ] `mypy` ohne neue Fehler
- [ ] `ruff check` ohne neue Warnungen
- [x] E-Mails werden im Development-Modus auf Console ausgegeben
