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



==============================

- ✅ rule page korrigiert:
  - Locktime auf "3 Minuten vor Kickoff" geändert (war falsch: "before match starts")
  - Privacy Protection entfernt (war falsch: predictions sind IMMER sichtbar)

- Email mit leaderboard
- chat gpt empfehlungen:
    - ich brauche kein is champion flag api gibt matchwinner wieder.
- alles mal aufräumen
- last test
- Tipp app programmierbar machen (Spiel um Platz 3, Wieviele Tipps in Gruppenphase )
- css klassen
- frontend aufeinander abstimmen?
- "error": "Limit erreicht: Max. 36 Gruppenphasen-Tipps erlaubt."
- Forum
- UI polishing (Menu Punkte besser sichtbar. Logout als Icon? Eigenen User highlighten.)
+ light dark mode besser 
- security check
- prod ready (email notifier für cron job aufbereiten. match update als worker da 24/7)

chat gpt empfehlungen:

Ich würde Copilot jetzt nicht die Architektur neu bauen lassen, sondern gezielt die folgenden Punkte abarbeiten lassen. Das ist nach unserem gesamten Review die bereinigte Liste:

Review the existing Django tipapp and implement the following improvements.

Important: preserve the current overall architecture. Do not introduce Redis, Celery, WebSockets, Kafka, queues, or other infrastructure unless absolutely necessary.

Current architecture:

football-data.org
        ↓
single match updater management command
        ↓
Match database updates
        ↓
match_result_entered signal
        ↓
ScoringService / champion scoring
        ↓
persisted User scoring aggregates
        ↓
RankingService
        ↓
HTMX frontend polling
The HTMX frontend is read-only regarding scoring. It polls different partial endpoints such as ranking, matches, statistics and live predictions.


1. HIGH – Fix champion bonus handling in

recalculate_user_score()

User.total_points is defined as:

"Cached total points from all scored predictions (including champion bonus)"
Therefore this invariant must always hold:

user.total_points == (
    sum_of_scored_match_prediction_points
    + user.champion_bonus_points
)
RankingService.recalculate_user_score() currently calculates match points and then does:

user.total_points = total_points
This would remove an existing champion bonus.

Change it to preserve the bonus:

user.total_points = total_points + user.champion_bonus_points
Before changing it, search the whole codebase for usages of:

recalculate_user_score
Report whether this method is currently actually used.

Add a regression test.


2. MEDIUM-HIGH – Fix match updater polling around kickoff

The match updater currently uses:

status="live"
for frequent polling and otherwise searches scheduled matches using:

kickoff__gt=now
This creates a gap if kickoff has already passed but football-data.org still reports the match as scheduled.

Example:

kickoff = 20:00
current time = 20:01
status = scheduled
The match is then neither live nor a future match.

Implement a simple active match window, approximately:

kickoff - 30 minutes
until
kickoff + 3 hours
During this window poll frequently even if the local status has not yet switched to live.

Keep the adaptive polling simple.

Suggested intervals:

live / active match window    -> 30 seconds
< 30 minutes before kickoff   -> 60 seconds
< 2 hours before kickoff      -> 5 minutes
otherwise                     -> 10 minutes
no upcoming matches           -> 30 minutes

3. MEDIUM-HIGH – Add strong tests for scoring aggregates

The following User fields are intentionally persisted aggregates:

total_points
exact_match_count
jokers_used
champion_bonus_points
Do NOT remove them.

They allow leaderboard requests to simply sort User rows instead of recalculating all predictions for every HTMX request.

Add or verify tests for:

first scoring:
0 -> 6
total_points +6

unchanged rescoring:
6 -> 6
delta 0

changed result:
6 -> 3
total_points -3

non-exact -> exact:
exact_match_count +1

exact -> non-exact:
exact_match_count -1

joker first scored:
jokers_used +1

same joker prediction rescored:
jokers_used must not increase again

champion bonus:
match points + champion bonus = total_points

provisional champion changes:
old bonus is removed
new bonus is awarded
normal match points are preserved

recalculate_user_score():
champion bonus remains included
The most important invariant is:

User.total_points == (
    Sum(scored MatchPrediction.points_earned)
    + User.champion_bonus_points
)

4. MEDIUM – Use football-data.org winner information if available

Review sync_matches_from_api() and the Match model.

football-data.org provides winner information for matches.

Check whether the API response’s winner field is already stored or processed.

If it is available and reliable for knockout matches including penalty shootouts, prefer using that information to determine the final winner instead of relying on:

Team.objects.get(is_champion=True)
Do not blindly redesign the models.

First report:

- whether winner is already parsed
- whether Match currently has a winner field
- what change would be required
If adding a winner_team field to Match is straightforward and clearly improves correctness, implement it.

Otherwise keep the current solution and document the limitation.


5. MEDIUM – Reject invalid round codes

Currently:

ROUND_MULTIPLIERS.get(match_round, 1)
silently uses multiplier 1 for unknown round codes.

This could silently award incorrect points.

Replace the fallback with explicit validation or failure.

Valid rounds are:

group
r32
r16
qf
sf
3rd
final
An unsupported round must raise a clear error rather than silently receive multiplier 1.

Add a test.


6. LOW – Remove unnecessary database query

Inside ScoringService.score_prediction() remove:

MatchPredictionModel.objects.filter(user=user).exists()
The result is unused and it does not enforce anything.

Remove the import too if it becomes unnecessary.


7. LOW – Simplify Olympic ranking abstraction

Search the complete project for usages of:

apply_olympic_ranking
create_tiebreaker_from_keys
If RankingService is the only actual consumer, remove the unnecessary generic core.ranking abstraction.

Move the ranking logic into RankingService, for example:

RankingService._apply_olympic_ranking()
Preserve exactly these ranking criteria:

1. total_points descending
2. exact_match_count descending
3. jokers_used ascending
Preserve Olympic ranking:

100 -> rank 1
95  -> rank 2
95  -> rank 2
90  -> rank 4
Do not convert it to dense ranking 1, 2, 2, 3.


8. LOW – Review concurrency, but do not overengineer

The HTMX frontend only reads data and therefore does not itself create scoring race conditions.

The current expected deployment has one match updater process.

Do NOT automatically add select_for_update() everywhere.

Search for all code paths that can write scoring or match results:

- match updater
- Django admin
- manual management commands
- background workers
- direct calls to score_prediction()
If there is genuinely only one scoring writer, keep the current simple implementation.

If multiple concurrent writers are realistically possible, explain the risk first and then make the minimum necessary scoring operation idempotent/concurrency-safe.


9. LOW – Optional historical leaderboard cleanup

The round-specific leaderboard currently annotates:

filtered_total_points
filtered_exact_count
filtered_jokers_used
and then temporarily assigns these values to User model attributes.

Consider directly creating leaderboard dictionaries from the annotated values instead.

Prefer:

annotated queryset
→ dictionaries
→ ranking
over:

annotated queryset
→ temporarily mutate User instances
→ dictionaries
Only change this if the result is clearly simpler.


10. LOW – Improve HTMX polling distribution with jitter

Different pages/components poll:

ranking
matches
statistics
live predictions / points
Polling frequency is already adaptive based on whether a match is running.

Preserve this.

Do not make all pages poll constantly every few seconds.

Suggested client behavior:

match live      -> approximately 10–20 seconds
match soon      -> 30–60 seconds
no live match   -> significantly slower
Add a small random jitter so that 100 browsers do not all fire their requests at exactly the same moment.

For example:

base interval 30s
jitter +/- 5s
→ actual interval roughly 25–35s
Prefer a reusable JavaScript polling helper rather than duplicating jitter logic across multiple templates.

Also randomize the initial delay so users do not immediately synchronize after opening the page.

Do not introduce WebSockets or SSE for this.


11. LOW – Avoid unnecessary polling

For components that only change during live matches, especially live predictions, avoid frequent polling when no relevant match is running.

Examples:

live predictions:
poll frequently only while relevant matches are live

ranking:
can poll more slowly outside live matches

match results:
poll frequently around/live after kickoff
Keep endpoints separate if they are displayed on different pages.

Do not combine everything into one giant endpoint just for optimization.


12. Preserve efficient leaderboard architecture

Do NOT move leaderboard ordering into JavaScript.

The backend should continue doing:

User.objects.filter(is_active=True).order_by(
    "-total_points",
    "-exact_match_count",
    "jokers_used",
)
and then calculate Olympic rank numbers.

This is intentional.

For approximately 100 users, even with HTMX polling, this is a lightweight query and does not need Redis or a separate leaderboard cache.


Priority

Work in this order:

1. HIGH
   Fix champion bonus in recalculate_user_score()

2. MEDIUM-HIGH
   Fix match updater kickoff polling gap

3. MEDIUM-HIGH
   Add/verify scoring aggregate tests

4. MEDIUM
   Review football-data.org winner handling

5. MEDIUM
   Reject unsupported round codes

6. LOW
   Remove useless exists() query

7. LOW
   Simplify core.ranking if it only has one consumer

8. LOW
   Review real scoring write paths before adding concurrency locks

9. LOW
   Add reusable HTMX polling jitter

10. LOW
    Reduce unnecessary polling outside live matches

11. LOW
    Optional historical leaderboard cleanup
Before making large changes, inspect the relevant existing code and prefer the smallest modification that solves each issue.

Do not redesign working parts just because another architecture would also be possible.



Von meinem iPhone gesendet