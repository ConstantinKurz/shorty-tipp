# Email Notifications - Design

## Context

Das Shortytipp Tippspiel ist eine Django-Anwendung für die WM 2026. Es existiert bereits:

- `LeaderboardSnapshot` Model mit JSON-Daten für Rankings
- `MatchPrediction` Model für Nutzer-Tipps
- `Match` Model mit `kickoff` Zeitstempel
- E-Mail-Backend konfiguriert (Console für Development)
- Bestehende E-Mail-Templates für Password Reset

Die neue Funktionalität soll zwei E-Mail-Typen ermöglichen:
1. Leaderboard-Report an Admin
2. Tipp-Erinnerungen an Nutzer

## Goals / Non-Goals

**Goals:**
- Management Command für Leaderboard-E-Mail an konfigurierte Admin-Adresse
- Management Command für Tipp-Erinnerungen an Nutzer ohne Tipps für Spiele in 24h
- Wiederverwendbare E-Mail-Service-Klasse
- Klare E-Mail-Templates im deutschen Text

**Non-Goals:**
- Automatische Cron-Einrichtung
- User-Preferences für E-Mail-Opt-Out
- HTML-E-Mails mit komplexem Styling (Plain-Text mit minimalem HTML)
- Retry-Logik bei fehlgeschlagenen E-Mails

## Decisions

### 1. Neues notifications App

**Decision:** Neue Django App `notifications/` für alle E-Mail-Logik.

**Rationale:**
- Klare Trennung von Verantwortlichkeiten
- E-Mail-Logik nicht in scoring/ oder predictions/ vermischen
- Einfache Erweiterbarkeit für zukünftige Notification-Typen

**Alternatives considered:**
- E-Mail-Funktionen in scoring/services.py: Abgelehnt - vermischt Scoring mit Notification
- Einzelne Scripts ohne App: Abgelehnt - keine Django-Integration

### 2. Daemon statt Cron-Jobs

**Decision:** Ein einzelner `notification_daemon` Command als Endlosschleife, analog zu `update_matches`.

```bash
python manage.py notification_daemon
python manage.py notification_daemon --leaderboard-hour=20 --reminder-hour=10
python manage.py notification_daemon --once  # Test-Modus
```

**Rationale:**
- Konsistent mit `update_matches.py` Pattern
- Kein Cron nötig - Daemon verwaltet Zeitplanung selbst
- Graceful shutdown via SIGTERM/SIGINT
- `--once` Flag für Tests
- Einfaches Docker/Systemd Deployment

### 3. Admin-E-Mail über Settings

**Decision:** Admin-E-Mail-Adresse wird über Django Settings konfiguriert.

```python
# settings/base.py
LEADERBOARD_ADMIN_EMAIL = env("LEADERBOARD_ADMIN_EMAIL", default="")
```

**Rationale:**
- Konsistent mit anderen Konfigurationen
- Einfache Änderung ohne Code-Deployment
- Unterstützt verschiedene Umgebungen (Dev/Prod)

### 4. E-Mail-Service Klasse

**Decision:** Zentrale `EmailService` Klasse für alle E-Mail-Operationen.

```python
class EmailService:
    @staticmethod
    def send_leaderboard_to_admin() -> bool: ...

    @staticmethod
    def send_prediction_reminder(user: User, matches: list[Match]) -> bool: ...
```

**Rationale:**
- Wiederverwendbar
- Zentrale Fehlerbehandlung
- Einfach zu mocken in Tests

### 5. 24-Stunden-Fenster für Reminder

**Decision:** Reminder werden für Spiele gesendet, die in den nächsten 24 Stunden starten.

**Rationale:**
- Genug Zeit zum Reagieren
- Nicht zu früh (Nutzer vergessen wieder)
- Klar definiertes Zeitfenster

### 6. Daemon mit Daily-Tracking

**Decision:** Daemon trackt per Datum ob E-Mails heute schon gesendet wurden.

```python
self.last_leaderboard_date = None
self.last_reminder_date = None
```

**Rationale:**
- Verhindert doppelte E-Mails bei Daemon-Neustart am selben Tag
- Einfache In-Memory Lösung ausreichend
- Kein DB-State nötig

### 7. Aktuellster Snapshot

**Decision:** Der neueste `LeaderboardSnapshot` wird für den E-Mail-Report verwendet.

```python
snapshot = LeaderboardSnapshot.objects.order_by('-created_at').first()
```

**Rationale:**
- Einfach und klar
- Keine zusätzliche Logik für Snapshot-Auswahl nötig
- Wenn kein Snapshot existiert, wird kein E-Mail gesendet

## Technical Design

### Neue Dateistruktur

```
notifications/
├── __init__.py
├── admin.py           # Leer (keine Admin-Models)
├── apps.py
├── services.py        # EmailService Klasse
├── management/
│   ├── __init__.py
│   └── commands/
│       ├── __init__.py
│       ├── notification_daemon.py  # Endlos-Daemon wie update_matches
│       └── test_email.py           # Manuelles SMTP-Testing
├── migrations/
│   └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── test_email_service.py
│   └── test_notification_daemon.py
└── templates/
    └── notifications/
        └── emails/
            ├── leaderboard_report.txt
            ├── leaderboard_report.html
            ├── prediction_reminder.txt
            └── prediction_reminder.html
```

### Settings Erweiterungen

```python
# tipapp/settings/base.py
LEADERBOARD_ADMIN_EMAIL = os.environ.get("LEADERBOARD_ADMIN_EMAIL", "")
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "noreply@shortytipp.de")
```

### EmailService Interface

```python
# notifications/services.py
from django.core.mail import send_mail
from django.template.loader import render_to_string

class EmailService:
    """Service for sending notification emails."""

    @staticmethod
    def send_leaderboard_to_admin() -> tuple[bool, str]:
        """
        Send latest leaderboard snapshot to configured admin email.

        Returns:
            Tuple of (success: bool, message: str)
        """
        ...

    @staticmethod
    def send_prediction_reminder(user: User, matches: list[Match]) -> tuple[bool, str]:
        """
        Send reminder to user about missing predictions.

        Args:
            user: User to notify
            matches: List of matches without predictions

        Returns:
            Tuple of (success: bool, message: str)
        """
        ...

    @staticmethod
    def get_users_with_missing_predictions() -> dict[User, list[Match]]:
        """
        Find users who haven't predicted for matches starting within 24h.

        Returns:
            Dict mapping users to their list of unpredicted matches
        """
        ...
```

### Notification Daemon Command

```python
# notification_daemon.py
class Command(BaseCommand):
    help = "Run notification daemon - sends daily emails"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.running = True
        self.last_leaderboard_date = None
        self.last_reminder_date = None

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Run once and exit")
        parser.add_argument("--interval", type=int, default=3600, help="Check interval seconds")
        parser.add_argument("--leaderboard-hour", type=int, default=20, help="Hour to send leaderboard (0-23)")
        parser.add_argument("--reminder-hour", type=int, default=10, help="Hour to send reminders (0-23)")

    def handle(self, *args, **options):
        signal.signal(signal.SIGTERM, self._shutdown)
        signal.signal(signal.SIGINT, self._shutdown)

        while self.running:
            now = timezone.now()
            today = now.date()

            # Leaderboard email - once per day at configured hour
            if (now.hour >= options["leaderboard_hour"]
                and self.last_leaderboard_date != today):
                EmailService.send_leaderboard_to_admin()
                self.last_leaderboard_date = today

            # Reminder email - once per day at configured hour
            if (now.hour >= options["reminder_hour"]
                and self.last_reminder_date != today):
                self._send_all_reminders()
                self.last_reminder_date = today

            if options["once"]:
                break

            time.sleep(options["interval"])

    def _shutdown(self, signum, frame):
        self.running = False
```

### E-Mail Templates

**Leaderboard Report (leaderboard_report.txt):**
```
Shortytipp Leaderboard - Stand {{ snapshot_date }}

Aktueller Punktestand:

{% for entry in rankings %}
{{ entry.rank }}. {{ entry.username }} - {{ entry.total_points }} Punkte
{% endfor %}

---
Automatisch generiert vom Shortytipp Tippspiel
```

**Prediction Reminder (prediction_reminder.txt):**
```
Hallo {{ user.username }},

Du hast noch nicht getippt für folgende Spiele:

{% for match in matches %}
- {{ match.team_home.name }} vs {{ match.team_away.name }} ({{ match.kickoff|date:"d.m.Y H:i" }})
{% endfor %}

Tippe jetzt: {{ site_url }}/predictions/

Viel Erfolg!
Dein Shortytipp Team
```

### Datenfluss

```
notification_daemon (Endlosschleife)
        |
        +-- Prüfe Uhrzeit + ob heute schon gesendet
        |
        +-- Falls leaderboard_hour erreicht + nicht heute gesendet:
        |       |
        |       +-- EmailService.send_leaderboard_to_admin()
        |       +-- last_leaderboard_date = today
        |
        +-- Falls reminder_hour erreicht + nicht heute gesendet:
        |       |
        |       +-- EmailService.get_users_with_missing_predictions()
        |       +-- For each user: EmailService.send_prediction_reminder()
        |       +-- last_reminder_date = today
        |
        +-- sleep(interval)
        |
        +-- Loop
```

## Risks

- **Risiko:** E-Mail wird als Spam markiert
  - **Mitigation:** Korrekte FROM-Adresse, SPF/DKIM auf Produktionsserver

- **Risiko:** Zu viele E-Mails bei vielen vergessenen Tipps
  - **Mitigation:** Ein E-Mail pro User mit allen fehlenden Tipps

- **Risiko:** SMTP-Fehler bei Production
  - **Mitigation:** Logging, Fehlerbehandlung in Commands

## Testing Strategy

- Unit Tests für EmailService mit gemocktem E-Mail-Backend
- Test für korrekte Filterung von Nutzern ohne Tipps
- Test für 24h-Fenster-Logik
- Test für leeren Leaderboard-Snapshot Fall
- Integration Test für Management Commands
