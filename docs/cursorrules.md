alwaysApply: true
.cursorrules - test5

This .cursorrules file serves as the AI assistant knowledge index.
Whenever working in Cursor, the following documents must be preloaded
and treated as the base architectural context:

## Mandatory Reference Documents

[docs/architecture.md](docs/architecture.md) - System architecture and design patterns
[docs/structure.md](docs/structure.md) - Project organization and folder structure
[docs/code.md](docs/code.md) - Code patterns and conventions
[docs/dataflow.md](docs/dataflow.md) - Data flow and system boundaries
[docs/decisions.md](docs/decisions.md) - Architectural decisions and rationale
[docs/glossary.md](docs/glossary.md) - Domain terminology and definitions
[docs/risk.md](docs/risk.md) - Security and risk management

---

## Purpose: Mandatory Context for Development

These documentation packs collectively describe the complete system architecture, design patterns, coding standards, data flows, security requirements, and risk management strategies. They serve as the single source of truth for:

- **Architecture & Design**: System boundaries, component interactions, design patterns (Config, ConnectionManager, SessionHandler patterns)
- **Coding Standards**: PEP 8 compliance, docstring requirements, naming conventions, type hints
- **Data Flows**: Azure authentication flows, credential handling, session state management, API interactions
- **Security & Risk**: Credential management, secret handling, Azure authentication patterns, token lifecycle
- **Operational Patterns**: Logging standards, error handling, connection lifecycle management

**These documents are MANDATORY reading before:**
- Developing new features or modules
- Debugging or refactoring existing code
- Making architectural decisions
- Modifying authentication or credential handling
- Changing data flow patterns

---

## Cursor Development Rules

### Context-First Development
- [ ] Parse all mandatory reference documents before making code recommendations
- [ ] Treat /docs as authoritative for architecture, standards, dataflows, and security
- [ ] Cross-check ambiguous code details against documentation before proceeding
- [ ] Verify all assumptions against actual codebase patterns using search_code or read_file

### Single Source of Truth
- [ ] Architecture decisions documented in docs/decisions.md are binding
- [ ] Code patterns in existing modules (config.py, connection_manager.py, session_handler.py) are templates for new code
- [ ] Security patterns in docs/risk.md override convenience in implementation
- [ ] Logging standards from utils/logger.py must be applied to all modules

### Documentation as Code
- [ ] Every new feature requires corresponding documentation updates in /docs
- [ ] API changes must update docs/structure.md and relevant architecture docs
- [ ] New modules must include docstrings matching the pattern: module docstring, class docstrings, method docstrings with Args/Returns
- [ ] Configuration changes must be documented in examples/config.yaml

### Task Management & Tracking
- [ ] Break down complex tasks into subtasks with [ ] checkboxes
- [ ] Track completion with [x] for done, [ ] for pending, [-] for blocked/deferred
- [ ] Link subtasks to specific files or functions
- [ ] Update task status before requesting review

### No Hallucination - Verification Required
- [ ] Only suggest APIs, classes, or functions present in the codebase or /docs
- [ ] Verify Azure SDK methods exist in azure-identity, azure-mgmt-desktopvirtualization, azure-mgmt-compute, azure-mgmt-network
- [ ] Confirm configuration keys exist in Config class before suggesting their use
- [ ] Check test patterns in tests/ before writing new tests

### Verification-First Approach
- [ ] Use CodeTools-search_code to find existing implementations before suggesting new ones
- [ ] Use CodeTools-read_file to examine actual patterns before recommending changes
- [ ] Verify method signatures against actual Azure SDK documentation
- [ ] Confirm error handling patterns match existing code (try/except with logging)

### Consistency Requirements
- [ ] All changes must align with architecture.md design patterns
- [ ] Code structure must follow structure.md folder organization
- [ ] Naming conventions must match code.md standards
- [ ] Error handling must follow existing patterns (exception → logger.error → return False/None)

### Security-First Analysis
- [ ] Analyze all credential handling against docs/risk.md
- [ ] Verify no secrets are hardcoded (use Config class and environment variables)
- [ ] Check Azure authentication flows use DefaultAzureCredential or ClientSecretCredential
- [ ] Validate all external API calls are properly authenticated
- [ ] Ensure sensitive data (subscription_id, resource_group, credentials) are never logged at INFO level

### Performance Considerations
- [ ] Evaluate API call batching opportunities (list operations should be paginated)
- [ ] Check for unnecessary repeated Azure API calls
- [ ] Verify connection pooling for multiple operations
- [ ] Assess logging overhead (avoid excessive DEBUG logging in production paths)
- [ ] Consider caching for frequently accessed host pool/session data

---

## Project-Specific Verification Rules

### Python Code Quality Standards
- **Linting**: PEP 8 compliance (follow existing code style)
- **Type Safety**: Use type hints in function signatures (see config.py, connection_manager.py patterns)
- **Docstrings**: Triple-quoted docstrings for all modules, classes, and public methods
  - Module level: `"""Description of module purpose."""`
  - Class level: `"""Description of class responsibility."""`
  - Method level: Include Args, Returns, Raises sections
- **Complexity**: Keep functions focused and under 50 lines where possible
- **Test Coverage**: Minimum 80% coverage for new code (see tests/ structure)
- **Imports**: Organize as stdlib, third-party, local (see existing imports)

### Development Workflow
- **Branch Strategy**: feature/*, bugfix/*, docs/* prefixes
- **Commit Standards**: Descriptive messages, reference issues, one logical change per commit
- **PR Requirements**:
  - All tests passing (python -m unittest discover tests)
  - Code follows PEP 8
  - Documentation updated
  - No hardcoded credentials or secrets
  - Docstrings added for new functions/classes

### Python/Azure SDK Best Practices
- **Azure Authentication**:
  - Use DefaultAzureCredential for local development and managed identity in production
  - Support ClientSecretCredential for service principal authentication
  - Never hardcode credentials; use Config class with environment variables
  - Follow AzureAuthenticator pattern in utils/auth.py
- **Client Management**:
  - Initialize clients (DesktopVirtualizationMgmtClient, ComputeManagementClient, NetworkManagementClient) in connect() method
  - Implement proper disconnect() cleanup
  - Handle ConnectionError exceptions when clients not initialized
- **Configuration Management**:
  - Use Config class for all configuration (YAML files + environment variable override)
  - Validate required fields before use (subscription_id, resource_group)
  - Support both file-based and environment-based configuration
- **Logging**:
  - Use get_logger(__name__) from utils/logger.py in all modules
  - Log at INFO level for major operations, DEBUG for details
  - Never log credentials, secrets, or sensitive data
  - Use consistent format: "Operation description" or "Operation failed: {error}"
- **Error Handling**:
  - Wrap Azure API calls in try/except blocks
  - Log errors with logger.error()
  - Return False/None on failure (don't raise exceptions for expected failures)
  - Raise exceptions only for unexpected/unrecoverable errors

### Security Requirements
- **Credential Management**:
  - All credentials loaded via Config class from environment variables or YAML
  - Never log credentials at any level
  - Use DefaultAzureCredential or ClientSecretCredential from azure.identity
  - Validate tenant_id, client_id, client_secret before use
- **Authentication**:
  - Implement authenticate() method before connect()
  - Handle authentication failures gracefully
  - Support multiple credential types (default, service principal)
- **Data Protection**:
  - Sensitive fields: subscription_id, resource_group, tenant_id, client_id, client_secret
  - Never include in debug output or logs
  - Validate input parameters before Azure API calls
- **Dependency Management**:
  - Pin versions in requirements.txt (see current versions)
  - Use azure-identity >= 1.15.0, azure-mgmt-desktopvirtualization >= 1.0.0
  - Keep dependencies up to date; monitor for security patches

### Performance Guidelines
- **API Optimization**:
  - Use list() to materialize Azure SDK iterables
  - Implement pagination for large result sets
  - Cache host pool and session data when appropriate
  - Batch operations where possible
- **Connection Management**:
  - Reuse ConnectionManager instances across operations
  - Implement connection pooling for multiple sequential operations
  - Call disconnect() to clean up resources
- **Logging Performance**:
  - Use INFO level for production (default in get_logger)
  - Avoid logging in tight loops
  - Use lazy string formatting (f-strings) for efficiency
- **Monitoring**:
  - Log session counts and operation timing
  - Track API call success/failure rates
  - Monitor connection establishment time

---

## Verification Checklist

### Before Committing Code

**Compilation & Syntax**
- [ ] Python syntax is valid (no SyntaxError)
- [ ] All imports are resolvable (no ImportError)
- [ ] Module can be imported without errors
- [ ] No circular import dependencies

**Code Quality**
- [ ] Code follows PEP 8 style guidelines
- [ ] No debug print() statements left in code
- [ ] No commented-out code blocks
- [ ] Variable and function names are descriptive
- [ ] Functions have docstrings with Args/Returns
- [ ] Classes have docstrings describing responsibility
- [ ] Module has docstring at top

**Logging & Debugging**
- [ ] No credentials logged at any level
- [ ] No sensitive data in log messages
- [ ] Appropriate log levels used (INFO for operations, DEBUG for details)
- [ ] Error messages are descriptive and actionable
- [ ] No print() statements (use logger instead)

**Security**
- [ ] No hardcoded credentials or secrets
- [ ] All credentials loaded from Config class
- [ ] Environment variables used for sensitive data
- [ ] No API keys or tokens in code
- [ ] Authentication errors handled gracefully

### Before Submitting PR

**Testing**
- [ ] All existing tests pass: `python -m unittest discover tests`
- [ ] New tests written for new functionality
- [ ] Test coverage >= 80% for new code
- [ ] Mock Azure API calls in tests (see test_connection_manager.py pattern)
- [ ] Edge cases tested (missing config, auth failure, API errors)

**Code Review Readiness**
- [ ] Code follows existing patterns in codebase
- [ ] Naming conventions match existing code
- [ ] Error handling matches existing patterns
- [ ] Logging follows existing standards
- [ ] No breaking changes to public APIs

**Manual Testing**
- [ ] Feature tested locally with valid Azure credentials
- [ ] Configuration loading tested (YAML and environment variables)
- [ ] Error scenarios tested (invalid config, auth failure, API errors)
- [ ] Logging output verified (appropriate levels, no secrets)

**Documentation Requirements**
- [ ] README.md updated if adding features
- [ ] Docstrings added for all new functions/classes
- [ ] examples/config.yaml updated if new config options added
- [ ] examples/basic_usage.py updated if new APIs added
- [ ] CONTRIBUTING.md updated if workflow changes

### Security Verification

**Credential Handling**
- [ ] No credentials in code or config files
- [ ] Config class used for all configuration
- [ ] Environment variables used for secrets
- [ ] .env file in .gitignore
- [ ] No credentials in example files

**Authentication**
- [ ] DefaultAzureCredential or ClientSecretCredential used
- [ ] Authentication errors logged without exposing credentials
- [ ] Credential validation before use
- [ ] Proper exception handling for auth failures

**Data Protection**
- [ ] Sensitive fields never logged
- [ ] Input validation before Azure API calls
- [ ] No SQL injection or command injection vulnerabilities
- [ ] Proper error messages (no stack traces with sensitive data)

**Dependency Security**
- [ ] No known vulnerabilities in dependencies
- [ ] Versions pinned in requirements.txt
- [ ] Regular dependency updates planned
- [ ] Security patches applied promptly

### Performance Validation

**API Efficiency**
- [ ] Azure API calls minimized (no unnecessary calls)
- [ ] Pagination implemented for large result sets
- [ ] Connection reused across operations
- [ ] Batch operations used where applicable

**Resource Management**
- [ ] Connections properly closed (disconnect() called)
- [ ] No resource leaks in error paths
- [ ] Memory usage reasonable for expected data sizes
- [ ] Logging doesn't impact performance

**Scalability**
- [ ] Code handles large numbers of host pools
- [ ] Code handles large numbers of sessions
- [ ] Timeout handling for long-running operations
- [ ] Graceful degradation on API rate limits

### Code Review Checklist

**Architecture & Design**
- [ ] Changes align with architecture.md patterns
- [ ] No architectural violations or shortcuts
- [ ] Design patterns used appropriately
- [ ] Separation of concerns maintained

**Maintainability**
- [ ] Code is readable and self-documenting
- [ ] Complex logic explained in comments
- [ ] DRY principle followed (no duplication)
- [ ] Functions have single responsibility

**Error Handling**
- [ ] All exceptions caught and handled
- [ ] Errors logged with context
- [ ] User-friendly error messages
- [ ] Graceful failure modes

**Logging & Observability**
- [ ] Appropriate log levels used
- [ ] Key operations logged
- [ ] Errors logged with full context
- [ ] No excessive logging in loops

### Pre-Deployment

**CI/CD Pipeline**
- [ ] All tests pass in CI environment
- [ ] Code quality checks pass
- [ ] Security scans pass (no known vulnerabilities)
- [ ] Build artifacts generated successfully

**Staging Validation**
- [ ] Feature tested in staging environment
- [ ] Configuration validated in staging
- [ ] Azure API calls verified with staging resources
- [ ] Performance acceptable in staging

**Deployment Preparation**
- [ ] Deployment procedure documented
- [ ] Rollback plan prepared
- [ ] Configuration for production prepared
- [ ] Monitoring/alerting configured

**Migration & Compatibility**
- [ ] No breaking changes to existing APIs
- [ ] Backward compatibility maintained
- [ ] Data migration tested (if applicable)
- [ ] Upgrade path documented

### Post-Deployment

**Health Checks**
- [ ] Application starts without errors
- [ ] Configuration loads correctly
- [ ] Azure authentication successful
- [ ] Initial API calls successful

**Error Rate Monitoring**
- [ ] No unexpected errors in logs
- [ ] Authentication failures monitored
- [ ] API call failures monitored
- [ ] Error rates within acceptable range

**Performance Metrics**
- [ ] API response times acceptable
- [ ] Connection establishment time acceptable
- [ ] Resource usage within expected range
- [ ] No memory leaks detected

**Monitoring & Alerting**
- [ ] Alerts configured for critical errors
- [ ] Logging aggregation working
- [ ] Performance metrics collected
- [ ] Dashboards updated with new metrics

---

## Critical Rules - Non-Negotiable

1. **PRESERVE all existing documentation links** - Do NOT remove or modify the mandatory reference documents list at the top
2. **Context-first always** - Never suggest code without verifying against /docs and existing patterns
3. **No hallucination** - Only use APIs, classes, and functions that exist in the codebase or are documented
4. **Security-first** - All credential handling must follow docs/risk.md patterns; no exceptions
5. **Documentation parity** - Features are only "done" when both code AND /docs are updated
6. **Verification before action** - Use CodeTools to verify patterns before recommending changes
7. **Consistency required** - All changes must align with architecture.md, structure.md, and code.md
8. **Test coverage** - New code must have tests; minimum 80% coverage
9. **No secrets in code** - All credentials via Config class and environment variables only
10. **Logging standards** - Use get_logger(__name__), never log credentials, follow existing patterns

---

## Project Tech Stack Summary

- **Language**: Python 3.8+
- **Azure SDKs**: azure-identity, azure-mgmt-desktopvirtualization, azure-mgmt-compute, azure-mgmt-network
- **Configuration**: YAML (PyYAML), Environment variables (python-dotenv)
- **HTTP**: requests library
- **Testing**: unittest (standard library)
- **Logging**: Python logging module
- **Package Management**: setuptools, pip

## Key Modules & Patterns

- **Config**: YAML + environment variable configuration with validation
- **ConnectionManager**: Azure authentication and multi-client management
- **SessionHandler**: AVD session and host pool operations
- **AzureAuthenticator**: Flexible credential handling (default + service principal)
- **Logger**: Centralized logging with console output

---

**Last Updated**: Based on codebase analysis of test5 project
**Scope**: Azure Virtual Desktop Manager (AVD) - Python-based management tool
**Audience**: AI assistants and developers working in Cursor IDE
```