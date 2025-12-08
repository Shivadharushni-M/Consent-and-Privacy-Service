# Consent & Privacy Preferences Service

A comprehensive backend service for managing user consent and privacy preferences with GDPR, CCPA, LGPD, and other regional compliance support.

## About

This service provides a complete solution for handling user consent management, privacy preferences, and data subject rights requests. It implements region-specific privacy regulations including GDPR (EU), CCPA (US), LGPD (Brazil), and supports other regions through a flexible policy engine.

## Key Features

- **JWT Authentication** - Secure token-based authentication for both users and admins
- **Consent Management** - Grant, revoke, and track user consent for various data processing purposes
- **Region-Based Decision Engine** - Automatically applies appropriate privacy rules based on user location (GDPR, CCPA, LGPD, etc.)
- **Subject Rights Requests** - Handle data export, deletion, access, and rectification requests
- **Immutable Audit Logging** - Complete audit trail for compliance and accountability
- **Policy Snapshots** - Captures policy state at the time of consent for historical compliance
- **Automated Retention** - Scheduled cleanup jobs for expired consents and anonymization of stale user data
- **IP-Based Region Detection** - Automatic region detection using MaxMind GeoIP database
- **Admin Dashboard** - Comprehensive admin endpoints for managing users, viewing audit logs, and policy snapshots

## Compliance Support

The service implements compliance logic for:

- **GDPR (EU)** - Requires explicit consent for sensitive purposes, right to erasure, data portability
- **CCPA (US)** - Opt-out model with default allow for non-sensitive purposes
- **LGPD (Brazil)** - Similar to GDPR with explicit consent requirements
- **Other Regions** - Flexible framework for additional regional regulations

## Technology Stack

Built with modern Python technologies:

- **FastAPI** - High-performance async web framework
- **SQLAlchemy 2.0** - Modern ORM with type hints
- **PostgreSQL** - Robust relational database
- **JWT** - Secure authentication tokens
- **MaxMind GeoIP** - IP-based region detection
- **pytest** - Comprehensive test suite

## License

MIT
