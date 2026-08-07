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
- rule page stimmt noch nicht ganz:
3 min vor spiel kann man noch eingeben. icons stimmen nicht etc.
Stimmt das:
🔒 Privacy Protection

You can only see other players' predictions after the match has started. This prevents copying predictions before kickoff!
- kann das ranking nicht zwischen predictions und ranking service geteilt werden.

Trenne Validation Service von Globalen Services(Ranking, Scoring, Statistics)
- Scraper + Scoring Setup:
  - Django Management Commands (kein Celery/Redis nötig)
  - Command 1: `scrape_results` - holt Match-Ergebnisse von API
  - Command 2 (eingebetten in 1): `calculate_rankings` - berechnet Punkte + Rankings, schreibt LeaderboardSnapshot und Punkte in Tipps.
  - Spieltag punkte auch in DB speichern!
  - Commands prüfen Match-Zeit selbst (10 min vor bis 10 min nach = jede Minute, sonst alle 10 min)
  - Hosting: Render.com ($15/Monat - Web + Postgres + native Cron Jobs in UI)
  - Alternative Dev: Railway ($5 Free Credits/Monat, aber kein natives Cron)
  - Cron triggert Commands, htmx pollt dann Updates auf Frontend 
- hier nochmal einen prompt als senior engineer laufen lassen und schauen was so gefunden wird
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