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

- hier nochmal einen prompt als senior engineer laufen lassen und schauen was so gefunden wird 
- feedback ob tipp gespeichert wurde done
- predictions componenten verinheitlichen auf home und match predcitions
- rule page stimmt noch nicht ganz:
3 min vor spiel kann man noch eingeben. icons stimmen nicht etc.
Stimmt das:
🔒 Privacy Protection

You can only see other players' predictions after the match has started. This prevents copying predictions before kickoff! Done!
- kann das ranking nicht zwischen predictions und ranking service geteilt werden.
- Email mit leaderboard
- Tipp app programmierbar machen (Spiel um Platz 3, Wieviele Tipps in Gruppenphase )
- css klassen
- python klassen in eigenen dateien schreiben?
- frontend aufeinander abstimmen?
- "error": "Limit erreicht: Max. 36 Gruppenphasen-Tipps erlaubt."
- Forum
- UI polishing (Menu Punkte besser sichtbar. Logout als Icon? Eigenen User highlighten.)
+ light dark mode besser 
- security check