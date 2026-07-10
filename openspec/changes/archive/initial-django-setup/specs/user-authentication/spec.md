## ADDED Requirements

### Requirement: Custom user model

The system SHALL implement a custom user model extending AbstractUser from the start.

#### Scenario: Custom user model exists
- **WHEN** the users app is created
- **THEN** a User model exists extending AbstractUser
- **AND** AUTH_USER_MODEL setting points to 'users.User'

#### Scenario: User model fields
- **WHEN** examining the User model
- **THEN** it inherits all AbstractUser fields (username, email, password, etc.)
- **AND** it can be extended with additional fields in future changes

#### Scenario: Initial migration
- **WHEN** migrations are created
- **THEN** the first migration creates the users_user table
- **AND** all Django auth tables reference the custom user model

### Requirement: Authentication views

The system SHALL provide basic authentication views for login and logout.

#### Scenario: Login view exists
- **WHEN** a user visits the login URL
- **THEN** a login form is displayed
- **AND** valid credentials authenticate the user

#### Scenario: Logout functionality
- **WHEN** an authenticated user logs out
- **THEN** the user session is terminated
- **AND** the user is redirected to a public page

#### Scenario: Password validation
- **WHEN** a user sets or changes a password
- **THEN** Django password validators are applied
- **AND** weak passwords are rejected

### Requirement: User administration

The system SHALL enable user management through Django admin interface.

#### Scenario: User admin registration
- **WHEN** the admin site is accessed
- **THEN** the User model is registered
- **AND** users can be created, updated, and deleted through the admin

#### Scenario: Admin user creation
- **WHEN** an admin user is created via manage.py createsuperuser
- **THEN** the user can access the admin site
- **AND** the user has all permissions

### Requirement: Authentication middleware

The system SHALL configure Django authentication middleware.

#### Scenario: Middleware configuration
- **WHEN** Django is configured
- **THEN** AuthenticationMiddleware is included in MIDDLEWARE
- **AND** SessionMiddleware is included before AuthenticationMiddleware

#### Scenario: User session support
- **WHEN** a user logs in
- **THEN** a session is created
- **AND** request.user is populated in views
