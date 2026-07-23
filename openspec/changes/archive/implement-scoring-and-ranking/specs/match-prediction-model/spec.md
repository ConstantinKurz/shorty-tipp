## ADDED Requirements

### Requirement: Points and exact match populated by scoring

The system SHALL populate points_earned and is_exact_match via scoring service.

#### Scenario: Fields set when match scored
- **WHEN** match result is entered
- **THEN** scoring service calculates and sets points_earned and is_exact_match for all predictions

#### Scenario: Fields updated on re-scoring
- **WHEN** match result changes
- **THEN** scoring service recalculates and updates points_earned and is_exact_match

#### Scenario: Fields remain NULL until scored
- **WHEN** prediction exists for unfinished match
- **THEN** points_earned and is_exact_match remain NULL until match has result
