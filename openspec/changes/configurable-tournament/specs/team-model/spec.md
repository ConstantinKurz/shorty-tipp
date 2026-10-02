## MODIFIED Requirements

### Requirement: Champion bonus points per team

The system SHALL store the champion bonus as an explicit point value on each team.

Previously the bonus was derived from `Team.odds_category`, a two-value field (`A` or `B`) mapped to
a hardcoded `CHAMPION_POINTS = {"A": 20, "B": 30}` dictionary. The category and the dictionary are
removed and replaced by a single integer field.

#### Scenario: Setting champion points

- **WHEN** an administrator sets a team's `champion_points` to 45
- **THEN** the value is stored
- **AND** a user who predicted that team as champion receives exactly 45 bonus points when it wins

#### Scenario: Default is no bonus

- **WHEN** a team is created without champion points
- **THEN** `champion_points` is 0
- **AND** predicting that team as champion awards no bonus

#### Scenario: Previous category scheme remains expressible

- **WHEN** eight teams are set to 20 points and the remaining teams to 30
- **THEN** the behaviour is identical to the previous A/B category scheme

#### Scenario: Editing champion points in bulk

- **WHEN** an administrator opens the team changelist
- **THEN** `champion_points` is editable inline for all teams on the page
- **AND** a single save applies all changes

#### Scenario: Backfill from the previous categories

- **WHEN** the migration runs on a database with existing teams
- **THEN** teams in category A receive 20 points
- **AND** teams in category B receive 30 points
- **AND** teams with no category receive 0 points

## REMOVED Requirements

### Requirement: Team championship points

**Reason:** The `points` field declared with `help_text="Championship points"` was never read or
written by any production code path. Its name is reused for `champion_points`, which carries the
champion bonus that `odds_category` previously encoded.

**Migration:** The field is renamed to `champion_points` and given new semantics. No data is lost,
because no data was ever written.

### Requirement: Champion prediction odds categories

**Reason:** Two fixed categories worth 20 and 30 points cannot express a per-team bonus, and force a
code change whenever the point values differ between tournaments. `docs/rules/wm2026-rules.md`
section 8 is updated accordingly, and open clarification 3 in section 15 — the inconsistency between
the documented maximum score of 802 and a category-B champion worth 30 — is resolved by making the
value explicit per team.

**Migration:** `Team.odds_category` and `Team.ODDS_CATEGORY_CHOICES` are removed after
`champion_points` has been backfilled from them. Administrators who want the previous behaviour set
the eight top teams to 20 and the rest to 30.
