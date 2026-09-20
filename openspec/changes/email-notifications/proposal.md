# Email Notifications

## Why

Das Tippspiel braucht zwei automatisierte E-Mail-Funktionen:

1. **Admin Leaderboard Report**: Admins sollen den aktuellsten Leaderboard-Snapshot per E-Mail erhalten können. Dies ermöglicht schnelle Übersicht über den Spielstand ohne Login.

2. **Tipper Reminder**: Nutzer vergessen manchmal für anstehende Spiele zu tippen. Eine automatische Erinnerungs-E-Mail 24 Stunden vor Spielbeginn hilft, verpasste Tipps zu vermeiden und erhöht das Engagement.

Beide Funktionen verbessern die Nutzererfahrung und reduzieren manuellen Aufwand für Admins.

## What Changes

- Neues `notifications/` Django App für E-Mail-Logik
- `notification_daemon` Management Command als Endlosschleife (wie `update_matches`)
- Täglicher Leaderboard-Report an Admin-E-Mail zu konfigurierbarer Uhrzeit
- Tägliche Tipp-Erinnerungen an Nutzer zu konfigurierbarer Uhrzeit
- E-Mail-Templates für beide Nachrichtentypen
- Konfigurierbare Admin-E-Mail-Adresse über Settings

## Capabilities

### New Capabilities

- `leaderboard-email-report`: Versenden des aktuellsten Leaderboard-Snapshots per E-Mail an eine konfigurierte Admin-Adresse (Gmail)
- `prediction-reminder-email`: Erinnerungsmail an Nutzer für Spiele ohne Tipp in den nächsten 24 Stunden

## Impact

- Keine Breaking Changes an bestehender Funktionalität
- Neue E-Mail-Abhängigkeit für Production (SMTP-Konfiguration erforderlich)
- Optionale Cron-Jobs für automatische Ausführung der Commands

## Out of Scope

- Cron-Jobs (Daemon läuft kontinuierlich wie `update_matches`)
- Push-Notifications
- SMS-Benachrichtigungen
- E-Mail-Preferences pro Nutzer (alle aktiven Nutzer erhalten Reminder)
