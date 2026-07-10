## ADDED Requirements

### Requirement: ruff linting and formatting

The system SHALL use ruff for code linting and formatting.

#### Scenario: ruff configuration
- **WHEN** the project is set up
- **THEN** a pyproject.toml section configures ruff
- **AND** it specifies target Python version 3.12

#### Scenario: Linting rules
- **WHEN** ruff is configured
- **THEN** it enables appropriate linting rules for Django projects
- **AND** it enforces consistent code style

#### Scenario: Running ruff
- **WHEN** ruff check is executed
- **THEN** it scans all Python files for issues
- **AND** it reports errors and warnings

#### Scenario: Auto-formatting
- **WHEN** ruff format is executed
- **THEN** it automatically formats all Python files
- **AND** it ensures consistent formatting across the codebase

### Requirement: mypy type checking

The system SHALL use mypy with django-stubs for static type checking.

#### Scenario: mypy configuration
- **WHEN** the project is set up
- **THEN** a mypy.ini or pyproject.toml section configures mypy
- **AND** django-stubs plugin is enabled

#### Scenario: Type checking enforcement
- **WHEN** mypy is run
- **THEN** it checks type hints in all Python files
- **AND** it reports type errors and inconsistencies

#### Scenario: Django integration
- **WHEN** mypy checks Django code
- **THEN** it understands Django ORM types via django-stubs
- **AND** it correctly handles Django model fields and querysets

#### Scenario: Strict mode configuration
- **WHEN** mypy configuration is reviewed
- **THEN** it enables strict checking for new code
- **AND** it allows gradual adoption without blocking development

### Requirement: Pre-commit hooks (optional)

The system SHOULD provide pre-commit hook configuration for automated checks.

#### Scenario: Pre-commit configuration
- **WHEN** pre-commit is configured
- **THEN** a .pre-commit-config.yaml file exists
- **AND** it includes hooks for ruff and mypy

#### Scenario: Running pre-commit
- **WHEN** pre-commit hooks are installed
- **THEN** they run automatically on git commit
- **AND** they prevent commits with linting or type errors

### Requirement: Code quality commands

The system SHALL provide simple commands for running code quality checks.

#### Scenario: Check all code quality
- **WHEN** a make command or script is run
- **THEN** it executes ruff check, ruff format --check, and mypy
- **AND** it reports all issues found

#### Scenario: Fix auto-fixable issues
- **WHEN** a fix command is run
- **THEN** it applies ruff format and ruff check --fix
- **AND** it auto-corrects formatting and simple linting issues

### Requirement: Import sorting

The system SHALL enforce consistent import ordering.

#### Scenario: Import organization
- **WHEN** ruff is configured
- **THEN** it includes import sorting rules (e.g., isort-compatible)
- **AND** it groups imports into stdlib, third-party, and first-party sections

#### Scenario: Django import conventions
- **WHEN** imports are sorted
- **THEN** Django imports are placed in the third-party section
- **AND** local app imports are in the first-party section
