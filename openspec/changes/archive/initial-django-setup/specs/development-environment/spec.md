## ADDED Requirements

### Requirement: uv dependency management

The system SHALL use uv for Python dependency management and virtual environment.

#### Scenario: uv configuration file
- **WHEN** the project is set up
- **THEN** a pyproject.toml file exists
- **AND** it declares Python version 3.12 or higher

#### Scenario: Dependency declaration
- **WHEN** dependencies are managed
- **THEN** Django 5.2 and other dependencies are listed in pyproject.toml or requirements.txt
- **AND** version constraints are specified

#### Scenario: Development dependencies
- **WHEN** development tools are needed
- **THEN** dev dependencies are separated from production dependencies
- **AND** they include pytest, ruff, mypy, and django-stubs

### Requirement: Environment variable configuration

The system SHALL use environment variables for configuration values.

#### Scenario: Environment file template
- **WHEN** the project is set up
- **THEN** a .env.example file exists with all required variables
- **AND** a .gitignore excludes the actual .env file

#### Scenario: Required environment variables
- **WHEN** the application starts
- **THEN** it reads SECRET_KEY from environment
- **AND** it reads database connection details from environment
- **AND** it reads DEBUG setting from environment

#### Scenario: Development defaults
- **WHEN** environment variables are missing in development
- **THEN** reasonable default values are used
- **AND** a warning is logged for missing production-critical variables

### Requirement: Docker development environment

The system SHALL provide Docker configuration for the full development stack.

#### Scenario: Multi-service Docker Compose
- **WHEN** the Docker environment is started
- **THEN** PostgreSQL service is started
- **AND** Django development server can run in a container or locally

#### Scenario: Volume mounting
- **WHEN** Docker Compose is configured
- **THEN** source code is mounted as a volume
- **AND** code changes are reflected without rebuilding

#### Scenario: Service dependencies
- **WHEN** Docker services are started
- **THEN** Django waits for PostgreSQL to be ready
- **AND** migrations can run after database is available

### Requirement: Virtual environment

The system SHALL provide instructions for local virtual environment setup.

#### Scenario: Virtual environment creation
- **WHEN** a developer sets up the project locally
- **THEN** they can create a virtual environment with uv venv
- **AND** they can activate it following standard conventions

#### Scenario: Dependency installation
- **WHEN** dependencies need to be installed
- **THEN** uv pip install can install from pyproject.toml or requirements.txt
- **AND** all dependencies are installed in the virtual environment
