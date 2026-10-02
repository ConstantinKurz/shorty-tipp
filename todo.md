- User Page done
- Home Page mit Ranking und nächste Spiele done
- wieso gibt es javascript und wird nicht über htmx erledigt. done
- 3 min vor start keine eingabe mehr. Done
HTMX-Aufgaben: Server-getriebene HTML-Swaps (Formular speichern, Aktualisierungen)
JavaScript-Aufgaben: Client-seitige UX (Filter, Navigation, Auto-Save-Logik)
- htmx für ranking napassungen (ranking wird nicht aktualisiert) done
- RegelnPage done
- champion flags per htmx setzen done
- leaderboard weekly? plus alle tipps done
- admin page link done
- dedicated page for alle tipps done
- kriegt die page mit wenn sich predictions ändern?

Trenne Validation Service von Globalen Services(Ranking, Scoring, Statistics)
- API-Call + Scoring Setup:
- https://www.football-data.org/about

Die Deployment-Strategie für deine Tipp-App ist bewusst einfach gehalten: Die Anwendung besteht aus drei Containern. Ein Django-Webcontainer liefert die Website mit HTMX und Bootstrap aus, verwaltet Logins, Tipps, Ranglisten und Statistiken. Eine PostgreSQL-Datenbank speichert alle Nutzer, Spiele, Tipps und Rankings. Zusätzlich läuft ein separater Updater-Service, der regelmäßig die Fußball-Ergebnisse über die football-data.org API abfragt und die Datenbank aktualisiert. Die API stellt dafür kostenlose Zugriffe auf Wettbewerbe, Spiele und Ergebnisse bereit.

Der Updater läuft dauerhaft in einer einfachen while-Schleife. Wenn keine laufenden Spiele existieren, schläft er beispielsweise 10 Minuten. Sobald ein Spiel läuft, verkürzt er das Intervall auf etwa 30 Sekunden und holt regelmäßig neue Ergebnisse. Nach jeder Aktualisierung prüft er, ob ein Spiel beendet wurde. Nur dann werden Punkte, Spieltagswertungen und das Gesamtranking neu berechnet. Dadurch bleiben die API-Aufrufe niedrig und das kostenlose Limit wird problemlos eingehalten.

Deployen würdest du das zunächst auf Render oder Railway, später möglicherweise auf einem kleinen Hetzner-Cloud-Server mit Docker Compose. Die gesamte Architektur bleibt dabei einfach: Django für die Benutzerinteraktion, PostgreSQL für die Speicherung und ein separater Updater-Service für die Fußball-Daten. Kein Celery, kein Redis, kein Kubernetes und kein Scraping notwendig

Done

- hier nochmal einen prompt als senior engineer laufen lassen und schauen was so gefunden wird done
- feedback ob tipp gespeichert wurde done
- kann das ranking nicht zwischen predictions und ranking service geteilt werden. done olympisches ranking wird geteilt.
- predictions componenten verinheitlichen auf home und match predcitions 
- chat gpt empfehlungen nochmal anschauen
    - ich brauche kein is champion flag api gibt matchwinner wieder.


-  rule page korrigiert:
  - Locktime auf "3 Minuten vor Kickoff" geändert (war falsch: "before match starts")
  - Privacy Protection entfernt (war falsch: predictions sind IMMER sichtbar)

done
- Email mit leaderboard und predictions
Ist da aber daten sind momentan noch leer
done
- könnte ich nicht doch das globale ranking zentral berechnen und in user ranks speichern und einfach nur ordnen? anstelle in predictions/vioews.py und ranking_service?
Bei ~100 Usern und ~64 Matches: Kein echter Performance-Gewinn, mehr Code, mehr Bugs.

- alles mal aufräumen (from import noch in funktionen. viele klassen in einer datei.)

==============================
- Tipp app programmierbar machen (Spiel um Platz 3, Wieviele Tipps in Gruppenphase )
- e2e tests (python manage.py create_wm2026_testdata --clear)
 - kann ich die wm per test mal durchmodelieren?

# UI polishing
- UI polishing (Menu Punkte besser sichtbar. Logout als Icon? Eigenen User highlighten.)
+ light dark mode besser 
- css klassen
- frontend aufeinander abstimmen?
- "error": "Limit erreicht: Max. 36 Gruppenphasen-Tipps erlaubt."


# New Features
- Forum
- security check
- prod ready (email notifier für cron job aufbereiten. match update als worker da 24/7)
- last test?