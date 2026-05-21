# Architecture Decision Records: Azure Virtual Desktop Manager (`avd_manager`)

**Document Version:** 2.0
**Package Version:** 0.1.0 (Alpha)
**Author:** QA Test Team
**Related Documents:** [architecture.md](architecture.md) · [structure.md](structure.md) · [code.md](code.md)

---

## Table of Contents

1. [ADR-001: Python as the Implementation Language](#adr-001-python-as-the-implementation-language)
2. [ADR-002: Azure SDK Libraries as the Integration Layer](#adr-002-azure-sdk-libraries-as-the-integration-layer)
3. [ADR-003: Layered Architecture with Separation of Concerns](#adr-003-layered-architecture-with-separation-of-concerns)
4. [ADR-004: Facade Pattern for Azure SDK Complexity](#adr-004-facade-pattern-for-azure-sdk-complexity)
5. [ADR-005: Dependency Injection for ConnectionManager into SessionHandler](#adr-005-dependency-injection-for-connectionmanager-into-sessionhandler)
6. [ADR-006: Dual Configuration Strategy — YAML File and Environment Variables](#adr-006-dual-configuration-strategy--yaml-file-and-environment-variables)
7. [ADR-007: Dual Authentication Strategy — DefaultAzureCredential and ClientSecretCredential](#adr-007-dual-authentication-strategy--defaultazurecredential-and-clientsecretcredential)
8. [ADR-008: Python Standard Library `logging` with a Centralised Factory Function](#adr-008-python-standard-library-logging-with-a-centralised-factory-function)
9. [ADR-009: Defensive Error Handling — Swallow-and-Return-Empty vs. Raise](#adr-009-defensive-error-handling--swallow-and-return-empty-vs-raise)
10. [ADR-010: `setuptools` for Packaging and Distribution](#adr-010-setuptools-for-packaging-and-distribution)
11. [ADR-011: Python `unittest` with `unittest.mock` as the Testing Framework](#adr-011-python-unittest-with-unittestmock-as-the-testing-framework)
12. [ADR-012: No Persistent Local Storage — Azure ARM as the System of Record](#adr-012-no-persistent-local-storage--azure-arm-as-the-system-of-record)
13. [ADR-013: No Dedicated API Layer — Library-First Design](#adr-013-no-dedicated-api-layer--library-first-design)
14. [ADR-014: Minimum Python Version Set to 3.8](#adr-014-minimum-python-version-set-to-38)
15. [ADR-015: PEP 8 Code Style and Docstring Convention](#adr-015-pep-8-code-style-and-docstring-convention)
16. [ADR-016: AzureAuthenticator Utility Class as an Optional Strategy Selector](#adr-016-azureauthenticator-utility-class-as-an-optional-strategy-selector)
17. [ADR-017: Config.save() Method for Configuration Persistence](#adr-017-configsave-method-for-configuration-persistence)
18. [ADR-018: Utilities Sub-package Boundary and Module Organization](#adr-018-utilities-sub-package-boundary-and-module-organization)
19. [ADR-019: Sequential N+1 Query Pattern in monitor_sessions()](#adr-019-sequential-n1-query-pattern-in-monitor_sessions)
20. [ADR-020: Null-Assignment Disconnect Strategy](#adr-020-null-assignment-disconnect-strategy)
21. [ADR-021: ARM Resource ID String Parsing via Split](#adr-021-arm-resource-id-string-parsing-via-split)
22. [ADR-022: load_dotenv() Embedded in Config Constructor](#adr-022-load_dotenv-embedded-in-config-constructor)
23. [ADR-023: Unused requests Dependency](#adr-023-unused-requests-dependency)
24. [ADR-024: Unused datetime Import in SessionHandler](#adr-024-unused-datetime-import-in-sessionhandler)
25. [ADR-025: PyYAML Library Choice](#adr-025-pyyaml-library-choice)
26. [ADR-026: python-dotenv Library Choice](#adr-026-python-dotenv-library-choice)
27. [ADR-027: setuptools.find_packages() Scope and Test Inclusion](#adr-027-setuptoolsfind_packages-scope-and-test-inclusion)
28. [ADR-028: StreamHandler Output to sys.stdout](#adr-028-streamhandler-output-to-sysstdout)
29. [ADR-029: setup.py Metadata Omissions](#adr-029-setuppy-metadata-omissions)
30. [ADR-030: Dual Authentication Implementation Paths](#adr-030-dual-authentication-implementation-paths)
31. [ADR-031: Context Manager Pattern Not Implemented](#adr-031-context-manager-pattern-not-implemented)
32. [ADR-032: Repeated Pre-condition Guard Pattern](#adr-032-repeated-pre-condition-guard-pattern)
33. [ADR-033: Public active_sessions Dictionary](#adr-033-public-active_sessions-dictionary)
34. [ADR-034: Singleton Logger via Python Registry](#adr-034-singleton-logger-via-python-registry)
35. [ADR-035: Error Handling Inconsistency in basic_usage.py](#adr-035-error-handling-inconsistency-in-basic_usagepy)
36. [ADR-036: Partial Configuration Validation](#adr-036-partial-configuration-validation)
37. [ADR-037: Unused Compute and Network Clients](#adr-037-unused-compute-and-network-clients)
38. [ADR-038: Root Logger Attachment in setup_file_logging()](#adr-038-root-logger-attachment-in-setup_file_logging)
39. [ADR-039: Legacy setup.py Format vs. Modern pyproject.toml](#adr-039-legacy-setuppy-format-vs-modern-pyprojecttoml)
40. [ADR-040: Python Version Classifier Ceiling](#adr-040-python-version-classifier-ceiling)

---

## ADR-001: Python as the Implementation Language

**Status:** Accepted
**Date:** Inferred from repository state (v0.1.0 Alpha)

### Context

A management tool for Azure Virtual Desktop must interact with the Azure Resource Manager (ARM) REST API. The choice of language determines the availability of first-party SDK support, the breadth of the contributor community, and the ease of scripting and automation integration.

### Decision

Python 3.8+ was chosen as the sole implementation language. All 12 source files in the repository are `.py` files.

**Evidence:**
- `setup.py` declares `python_requires=">=3.8"` and lists Python 3.8, 3.9, and 3.10 as supported classifiers.
- `requirements.txt` and `setup.py` `install_requires` list exclusively Python packages (`azure-identity`, `azure-mgmt-*`, `pyyaml`, `python-dotenv`, `requests`).
- `CONTRIBUTING.md` instructs contributors to create a Python virtual environment (`python -m venv venv`) and install via `pip`.
- The `README.md` states "Python 3.8+" under Requirements.

### Consequences

**Positive:**
- Microsoft publishes and maintains first-party Azure Python SDKs (`azure-identity`, `azure-mgmt-desktopvirtualization`, etc.), providing type-safe, versioned access to ARM APIs without hand-crafting HTTP calls.
- Python's ecosystem (PyPI, `setuptools`, `unittest`) provides a complete, well-understood toolchain.
- Python is widely used in DevOps and cloud automation, lowering the barrier for contributors.

**Negative:**
- Python's GIL and dynamic typing can introduce subtle runtime errors that a statically typed language (e.g., Go, TypeScript) would catch at compile time.
- No type annotations are present in the codebase, reducing IDE support and static analysis capability.
- Performance-sensitive workloads (e.g., polling thousands of sessions in a tight loop) may be slower than compiled alternatives.

---

## ADR-002: Azure SDK Libraries as the Integration Layer

**Status:** Accepted

### Context

Azure Virtual Desktop resources are managed through the Azure Resource Manager REST API. The team needed to decide whether to call the ARM REST API directly (using `requests`) or to use Microsoft's official Python SDK wrappers.

### Decision

The official Microsoft Azure Python SDK packages are used exclusively for all ARM interactions. Four SDK packages are declared as dependencies:

| Package | Version Pinned (requirements.txt) | Version Floor (setup.py) | Purpose |
|---|---|---|---|
| `azure-identity` | `1.15.0` | `>=1.15.0` | Credential acquisition |
| `azure-mgmt-desktopvirtualization` | `1.0.0` | `>=1.0.0` | AVD host pools, session hosts, user sessions |
| `azure-mgmt-compute` | `30.5.0` | `>=30.5.0` | VM-level compute operations |
| `azure-mgmt-network` | `25.2.0` | `>=25.2.0` | Network resource operations |

**Evidence from `connection_manager.py`:**
```python
from azure.identity import DefaultAzureCredential
from azure.mgmt.desktopvirtualization import DesktopVirtualizationMgmtClient
from azure.mgmt.compute import ComputeManagementClient
from azure.mgmt.network import NetworkManagementClient
```

The `requests` library is listed in `requirements.txt` but is not imported in any source module, suggesting it is reserved for future use or was included speculatively. See ADR-023 for detailed analysis.

### Consequences

**Positive:**
- SDK clients handle authentication token refresh, retry logic, and serialisation/deserialisation of ARM responses automatically.
- API surface is versioned and documented by Microsoft, reducing maintenance burden.
- `DesktopVirtualizationMgmtClient`, `ComputeManagementClient`, and `NetworkManagementClient` provide strongly typed response objects.

**Negative:**
- The project takes on three large transitive dependency trees (`azure-mgmt-*`), increasing install size and the attack surface for supply-chain vulnerabilities.
- `requests==2.31.0` is pinned in `requirements.txt` but unused in source code, creating unnecessary dependency noise.
- SDK major version bumps (e.g., `azure-mgmt-compute` is already at v30) may introduce breaking changes requiring periodic maintenance.

---

## ADR-003: Layered Architecture with Separation of Concerns

**Status:** Accepted

### Context

The codebase must handle three distinct concerns: configuration management, Azure connectivity, and session-level operations. Mixing these responsibilities into a single module would reduce testability and maintainability.

### Decision

A three-layer architecture is implemented, with each layer encapsulated in its own module:

1. **Configuration Layer** — `avd_manager/config.py` (`Config` class): reads YAML files and environment variables; validates required fields.
2. **Connection Layer** — `avd_manager/connection_manager.py` (`ConnectionManager` class): authenticates with Azure and instantiates SDK clients.
3. **Session Layer** — `avd_manager/session_handler.py` (`SessionHandler` class): performs session-level operations by delegating to the connection layer.
4. **Utilities Sub-package** — `avd_manager/utils/` (`auth.py`, `logger.py`): cross-cutting concerns shared by all layers.

**Evidence from `avd_manager/__init__.py`:**
```python
from .connection_manager import ConnectionManager
from .session_handler import SessionHandler
from .config import Config

__all__ = ["ConnectionManager", "SessionHandler", "Config"]
```

The public API surface is explicitly controlled via `__all__`, exposing only the three primary layer classes.

### Consequences

**Positive:**
- Each layer can be tested in isolation (evidenced by `test_config.py` and `test_connection_manager.py` testing their respective layers independently).
- Callers can use `Config` without instantiating `ConnectionManager`, and `ConnectionManager` without `SessionHandler`.
- The utility sub-package (`utils/`) prevents duplication of logging and auth logic across layers.

**Negative:**
- `SessionHandler` directly accesses `connection_manager.avd_client` (an internal attribute), creating tight coupling between the session and connection layers:
  ```python
  # session_handler.py
  if not self.connection_manager.avd_client:
      raise ConnectionError("Not connected to Azure services")
  ```
  This violates the Law of Demeter and makes the internal structure of `ConnectionManager` part of the implicit contract.

---

## ADR-004: Facade Pattern for Azure SDK Complexity

**Status:** Accepted

### Context

The Azure SDK clients (`DesktopVirtualizationMgmtClient`, `ComputeManagementClient`, `NetworkManagementClient`) expose large, complex APIs. Callers should not need to know which SDK client handles which operation, nor should they need to manage credential lifecycle.

### Decision

`ConnectionManager` acts as a **Facade** over the three SDK clients, presenting a simplified interface (`connect()`, `list_host_pools()`, `get_host_pool()`, `disconnect()`) that hides SDK instantiation and credential management.

**Evidence from `connection_manager.py`:**
```python
def connect(self):
    """Establish connections to Azure services."""
    if not self.credential:
        if not self.authenticate():
            raise ConnectionError("Failed to authenticate")

    self.avd_client = DesktopVirtualizationMgmtClient(...)
    self.compute_client = ComputeManagementClient(...)
    self.network_client = NetworkManagementClient(...)
```

Callers in `basic_usage.py` interact only with `manager.connect()` and `manager.list_host_pools()`, never directly with any SDK client.

### Consequences

**Positive:**
- Consumers of the library are insulated from SDK version changes; only `ConnectionManager` needs updating when SDK APIs change.
- Authentication and client initialisation are handled in one place, reducing boilerplate for callers.

**Negative:**
- The facade currently exposes only a small subset of the AVD SDK's capabilities (host pool listing and retrieval). Extending the facade for every SDK operation would require ongoing additions to `ConnectionManager`.
- `compute_client` and `network_client` are initialised in `connect()` but never used in any current method, indicating over-provisioning of the facade. See ADR-037 for detailed analysis.

---

## ADR-005: Dependency Injection for ConnectionManager into SessionHandler

**Status:** Accepted

### Context

`SessionHandler` requires access to an authenticated Azure client to perform session operations. The team needed to decide whether `SessionHandler` should create its own connection or receive one from the caller.

### Decision

`SessionHandler` receives a `ConnectionManager` instance via constructor injection (Dependency Injection pattern).

**Evidence from `session_handler.py`:**
```python
class SessionHandler:
    def __init__(self, connection_manager):
        """
        Args:
            connection_manager: ConnectionManager instance
        """
        self.connection_manager = connection_manager
```

**Evidence from `basic_usage.py`:**
```python
manager = ConnectionManager(config.get('subscription_id'), config.get('resource_group'))
manager.connect()
session_handler = SessionHandler(manager)
```

**Evidence from `test_connection_manager.py`:** The `ConnectionManager` is tested independently with a mocked `DefaultAzureCredential`, confirming the injection boundary is respected in tests.

### Consequences

**Positive:**
- `SessionHandler` can be unit-tested by injecting a mock `ConnectionManager`, avoiding real Azure API calls.
- A single authenticated `ConnectionManager` can be shared across multiple `SessionHandler` instances, avoiding redundant authentication round-trips.
- The lifecycle of the connection is controlled by the caller, not by `SessionHandler`.

**Negative:**
- The caller is responsible for ensuring `manager.connect()` is called before passing the manager to `SessionHandler`. There is no enforcement of this ordering at the type level; failures surface only at runtime as `ConnectionError`.

---

## ADR-006: Dual Configuration Strategy — YAML File and Environment Variables

**Status:** Accepted

### Context

The library must support multiple deployment contexts: local development (where a config file is convenient), CI/CD pipelines (where environment variables are the standard), and containerised deployments (where secrets are injected as environment variables). A single configuration mechanism would not serve all contexts.

### Decision

The `Config` class implements a **two-source, environment-overrides-file** strategy:

1. If a YAML file path is provided and the file exists, it is loaded first using `yaml.safe_load()`.
2. Environment variables (`AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_TENANT_ID`, `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`) are always applied on top, overriding any file-based values.
3. `.env` files are supported via `python-dotenv`'s `load_dotenv()`, called unconditionally at `Config.__init__` time.

**Evidence from `config.py`:**
```python
def _load_config(self):
    if self.config_file and Path(self.config_file).exists():
        with open(self.config_file, 'r') as f:
            self.config = yaml.safe_load(f)

    # Override with environment variables
    self.config['subscription_id'] = os.getenv(
        'AZURE_SUBSCRIPTION_ID',
        self.config.get('subscription_id')
    )
    ...
```

**Evidence from `examples/config.yaml`:** The example YAML file includes a comment explicitly noting that authentication fields are "Optional - can use environment variables instead."

**Evidence from `test_config.py`:**
```python
@patch.dict(os.environ, {'AZURE_SUBSCRIPTION_ID': 'env-sub-id', ...})
def test_load_from_environment(self):
    config = Config()
    self.assertEqual(config.get('subscription_id'), 'env-sub-id')
```

### Consequences

**Positive:**
- Supports the full spectrum from local development (YAML file) to production CI/CD (environment variables) without code changes.
- `python-dotenv` allows `.env` files to be used in development without polluting the shell environment.
- `yaml.safe_load()` (not `yaml.load()`) is used, preventing arbitrary Python object deserialisation from YAML — a security best practice.

**Negative:**
- Environment variables always win over file values, which may surprise users who set a value in YAML and then have a stale environment variable override it silently.
- Secrets (`client_secret`) are stored in plain text in both the YAML file and environment variables. There is no integration with a secrets manager (e.g., Azure Key Vault, HashiCorp Vault).
- `Config.validate()` only checks `subscription_id` and `resource_group` as required fields, meaning a missing `tenant_id` or `client_secret` will not be caught until authentication is attempted at runtime. See ADR-036 for detailed analysis.

---

## ADR-007: Dual Authentication Strategy — DefaultAzureCredential and ClientSecretCredential

**Status:** Accepted

### Context

The library must authenticate to Azure in at least two distinct scenarios: interactive/managed-identity environments (developer workstations, Azure-hosted VMs with managed identity) and automated/headless environments (CI/CD pipelines, service accounts). A single credential type would not cover both.

### Decision

The `AzureAuthenticator` class in `utils/auth.py` implements a **strategy-selection** pattern: it automatically selects between `DefaultAzureCredential` and `ClientSecretCredential` based on whether service principal credentials are fully configured.

**Evidence from `utils/auth.py`:**
```python
def get_credential(self):
    if all([self.tenant_id, self.client_id, self.client_secret]):
        return self.get_service_principal_credential()
    else:
        return self.get_default_credential()
```

`DefaultAzureCredential` (from `azure-identity`) itself chains multiple credential providers (environment variables, managed identity, Azure CLI, etc.), providing broad compatibility.

`ConnectionManager.authenticate()` uses `DefaultAzureCredential` directly (not via `AzureAuthenticator`), indicating that `AzureAuthenticator` is a utility class available for callers who need explicit credential control, while `ConnectionManager` takes the simpler default path.

**Evidence from `connection_manager.py`:**
```python
from azure.identity import DefaultAzureCredential
...
def authenticate(self):
    self.credential = DefaultAzureCredential()
```

### Consequences

**Positive:**
- `DefaultAzureCredential` provides zero-configuration authentication in Azure-hosted environments (managed identity) and developer environments (Azure CLI login), reducing operational burden.
- `ClientSecretCredential` provides explicit, auditable service principal authentication for CI/CD pipelines.
- The strategy selection in `AzureAuthenticator.get_credential()` is automatic, reducing the risk of misconfiguration.

**Negative:**
- `ConnectionManager` and `AzureAuthenticator` both implement authentication logic independently. `ConnectionManager.authenticate()` does not use `AzureAuthenticator`, creating a duplication of credential acquisition logic. See ADR-030 for detailed analysis.
- `ClientSecretCredential` requires `client_secret` to be available in plaintext at runtime. Certificate-based authentication (`CertificateCredential`) is not implemented, which is the more secure option for production service principals.
- There is no token caching or refresh logic beyond what `azure-identity` provides internally.

---

## ADR-008: Python Standard Library `logging` with a Centralised Factory Function

**Status:** Accepted

### Context

All modules require structured, consistent log output for debugging and operational monitoring. The team needed to decide between the Python standard library `logging` module and a third-party logging library (e.g., `structlog`, `loguru`).

### Decision

Python's built-in `logging` module is used exclusively. A centralised factory function `get_logger(name, level=logging.INFO)` in `utils/logger.py` is the single point of logger creation across the entire codebase. An optional `setup_file_logging()` function adds file output.

**Evidence from `utils/logger.py`:**
```python
def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger
```

Every module acquires its logger at module level using `logger = get_logger(__name__)`, ensuring logger names reflect the module hierarchy (e.g., `avd_manager.connection_manager`).

**Evidence of consistent usage across all modules:**
- `config.py`: `logger = get_logger(__name__)`
- `connection_manager.py`: `logger = get_logger(__name__)`
- `session_handler.py`: `logger = get_logger(__name__)`
- `utils/auth.py`: `logger = get_logger(__name__)`

### Consequences

**Positive:**
- No additional dependency is required; `logging` is part of the Python standard library.
- The `if not logger.handlers:` guard prevents duplicate handler registration when `get_logger` is called multiple times for the same logger name.
- Using `__name__` as the logger name creates a hierarchical namespace that allows callers to configure log levels per module.
- `setup_file_logging()` allows file output to be added at runtime without changing module code.

**Negative:**
- Log output is unstructured plain text, not JSON. This makes log aggregation and querying in cloud-native log management systems (Azure Monitor, Splunk, ELK) more difficult.
- The log level is hardcoded to `INFO` as the default; there is no runtime mechanism (e.g., environment variable `LOG_LEVEL`) to change verbosity without modifying code.
- `setup_file_logging()` attaches a handler to the root logger, which will capture logs from all libraries (including Azure SDK internals), potentially producing very verbose log files. See ADR-038 for detailed analysis.

---

## ADR-009: Defensive Error Handling — Swallow-and-Return-Empty vs. Raise

**Status:** Accepted

### Context

Azure API calls can fail for many reasons (network errors, permission issues, resource not found). The team needed a consistent policy for how errors are surfaced to callers.

### Decision

A **mixed error-handling strategy** is used, with the boundary determined by the type of failure:

- **Pre-condition failures** (not connected to Azure): raise `ConnectionError` immediately.
- **Azure API call failures** (network errors, SDK exceptions): catch `Exception`, log the error, and return a safe empty value (`[]`, `False`, or `None`).

**Evidence from `session_handler.py` (illustrating both patterns):**
```python
def list_session_hosts(self, host_pool_name):
    if not self.connection_manager.avd_client:
        raise ConnectionError("Not connected to Azure services")  # Pre-condition: raise

    try:
        session_hosts = list(...)
        return session_hosts
    except Exception as e:
        logger.error(f"Failed to list session hosts: {str(e)}")
        return []  # API failure: swallow and return empty
```

The same pattern is applied in `connection_manager.py` (`list_host_pools`, `get_host_pool`) and `utils/auth.py` (`get_default_credential` re-raises, `get_service_principal_credential` re-raises).

### Consequences

**Positive:**
- Callers can safely iterate over the return value of list operations (`list_host_pools()`, `list_session_hosts()`) without wrapping every call in a try/except.
- Pre-condition errors (not connected) are raised immediately, preventing silent data corruption from operating on a `None` client.

**Negative:**
- Swallowing `Exception` broadly masks the specific cause of failure. A permission error, a network timeout, and a resource-not-found error all produce the same empty-list return, making it impossible for callers to distinguish and handle them differently.
- `disconnect_user_session()` returns `False` on failure, but callers in `basic_usage.py` do not check this return value, meaning silent failures are possible in the example code.
- `get_session_host_status()` returns `None` on failure; callers must perform a `None` check before accessing the returned dictionary, which is not enforced by the type system. See ADR-035 for detailed analysis of inconsistency in `basic_usage.py`.

---

## ADR-010: `setuptools` for Packaging and Distribution

**Status:** Accepted

### Context

The project is intended to be an installable Python library (`avd-manager`). A packaging mechanism is required to declare metadata, dependencies, and the installable package boundary.

### Decision

`setuptools` with a `setup.py` script is used as the build and packaging system. `find_packages()` is used to automatically discover all packages under the repository root.

**Evidence from `setup.py`:**
```python
from setuptools import setup, find_packages

setup(
    name="avd-manager",
    version="0.1.0",
    description="Azure Virtual Desktop Management Tool",
    packages=find_packages(),
    install_requires=[
        "azure-identity>=1.15.0",
        ...
    ],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        ...
    ],
)
```

`CONTRIBUTING.md` instructs development installation via `pip install -e .` (editable install), confirming `setuptools` is the intended development workflow.

### Consequences

**Positive:**
- `setup.py` with `install_requires` ensures all dependencies are automatically installed when the package is installed via `pip`.
- `find_packages()` automatically includes `avd_manager` and `avd_manager.utils` without manual enumeration.
- The `Development Status :: 3 - Alpha` classifier correctly signals the package's maturity level to potential users.

**Negative:**
- `setup.py` is the legacy packaging format. The modern Python packaging standard (`pyproject.toml` with `[build-system]`, `[project]`) is not used. This may cause compatibility issues with newer build tools and PEP 517/518 compliant build frontends. See ADR-039 for detailed analysis.
- There is no `MANIFEST.in` or `package_data` declaration, meaning non-Python files (e.g., the example `config.yaml`) would not be included in a source distribution.
- `requirements.txt` pins exact versions (e.g., `azure-identity==1.15.0`) while `setup.py` uses minimum-version floors (e.g., `>=1.15.0`). This dual-file approach is correct practice (pinned for reproducible environments, floors for library compatibility), but the two files are not automatically kept in sync.

---

## ADR-011: Python `unittest` with `unittest.mock` as the Testing Framework

**Status:** Accepted

### Context

The library interacts with external Azure APIs that cannot be called in a unit test environment. A testing framework and mocking strategy must be chosen.

### Decision

Python's built-in `unittest` framework is used as the test runner and base class. `unittest.mock` (specifically `Mock`, `patch`, and `patch.dict`) is used to isolate tests from Azure API calls and environment state.

**Evidence from `tests/test_connection_manager.py`:**
```python
import unittest
from unittest.mock import Mock, patch
from avd_manager.connection_manager import ConnectionManager

class TestConnectionManager(unittest.TestCase):
    @patch('avd_manager.connection_manager.DefaultAzureCredential')
    def test_authenticate_success(self, mock_credential):
        mock_credential.return_value = Mock()
        result = self.manager.authenticate()
        self.assertTrue(result)
```

**Evidence from `tests/test_config.py`:**
```python
@patch.dict(os.environ, {'AZURE_SUBSCRIPTION_ID': 'env-sub-id', ...})
def test_load_from_environment(self):
    config = Config()
    self.assertEqual(config.get('subscription_id'), 'env-sub-id')
```

The test runner command documented in both `README.md` and `CONTRIBUTING.md` is:
```bash
python -m unittest discover tests
```

`CONTRIBUTING.md` explicitly mandates: "Use mocking for Azure API calls."

### Consequences

**Positive:**
- `unittest` is part of the Python standard library, requiring no additional test dependencies.
- `patch` at the import path level (`avd_manager.connection_manager.DefaultAzureCredential`) correctly intercepts the credential class where it is used, not where it is defined — a correct mocking practice.
- `patch.dict(os.environ, ...)` cleanly isolates environment variable state between tests without side effects.

**Negative:**
- Only two test files exist (`test_config.py`, `test_connection_manager.py`), covering `Config` and `ConnectionManager` only. `SessionHandler` and `AzureAuthenticator` have no test coverage.
- No integration tests are present. There is no test that exercises the full `Config → ConnectionManager → SessionHandler` chain, even with mocked Azure clients.
- No test coverage measurement tool (e.g., `coverage.py`) is configured, despite `CONTRIBUTING.md` stating "Aim for high test coverage."
- Third-party alternatives (`pytest`) offer more expressive assertions, fixtures, and parametrisation, but were not adopted — likely to keep the dependency footprint minimal.

---

## ADR-012: No Persistent Local Storage — Azure ARM as the System of Record

**Status:** Accepted

### Context

Session and host pool data could be cached locally to reduce API call frequency and improve performance. The team needed to decide whether to introduce a local data store.

### Decision

No local database, cache, or persistent storage mechanism is used. All data is fetched live from the Azure Resource Manager API on every call. The only local state maintained is the in-memory `active_sessions = {}` dictionary on `SessionHandler`, which is never populated by any current method.

**Evidence:** No database library (SQLite, Redis, SQLAlchemy, etc.) appears in `requirements.txt` or `setup.py`. No file-based cache is written in any module. The `active_sessions` dict in `session_handler.py` is initialised but never written to:
```python
self.active_sessions = {}  # Initialised but never populated
```

### Consequences

**Positive:**
- No data consistency or cache invalidation problems; the data returned always reflects the current Azure state.
- No additional infrastructure (database server, cache server) is required to run the library.
- Simplifies deployment and reduces operational overhead.

**Negative:**
- Every call to `monitor_sessions()` makes N+1 Azure API calls (one to list session hosts, then one per host to list sessions), which may be slow for large host pools. See ADR-019 for detailed analysis.
- The unused `active_sessions` dict suggests caching was considered but not implemented, leaving a potential future inconsistency if it is populated without a proper invalidation strategy. See ADR-033 for detailed analysis.
- There is no rate-limiting or back-off logic beyond what the Azure SDK provides internally.

---

## ADR-013: No Dedicated API Layer — Library-First Design

**Status:** Accepted

### Context

The functionality could be exposed as a REST API (Flask/FastAPI), a CLI tool (Click/argparse), or a Python library. The team needed to choose the primary consumption model.

### Decision

`avd_manager` is designed exclusively as an **importable Python library**. There is no HTTP server, no CLI entry point, and no `console_scripts` declaration in `setup.py`.

**Evidence:**
- `setup.py` contains no `entry_points` key, meaning no CLI command is registered on installation.
- The `__all__` in `avd_manager/__init__.py` exports only classes (`ConnectionManager`, `SessionHandler`, `Config`), not a CLI runner.
- `examples/basic_usage.py` demonstrates consumption as a library via `from avd_manager import ConnectionManager, SessionHandler, Config`.
- No web framework (`flask`, `fastapi`, `django`) appears in `requirements.txt`.

### Consequences

**Positive:**
- Library design maximises reusability; callers can integrate `avd_manager` into their own scripts, automation pipelines, or web services.
- No server infrastructure is required to use the library.
- The public API surface is minimal and explicit, controlled by `__all__`.

**Negative:**
- There is no CLI, so non-Python users or operators cannot use the tool without writing Python code.
- There is no REST API, so the functionality cannot be consumed by non-Python systems or exposed as a microservice without additional wrapping.
- Operational use cases (e.g., "disconnect all sessions in pool X") require writing a Python script rather than running a single command.

---

## ADR-014: Minimum Python Version Set to 3.8

**Status:** Accepted

### Context

Python 3.8 reached end-of-life in October 2024. The team needed to balance broad compatibility with access to newer language features.

### Decision

Python 3.8 is set as the minimum supported version in `setup.py` (`python_requires=">=3.8"`), with explicit support declared for 3.8, 3.9, and 3.10 via PyPI classifiers.

**Evidence from `setup.py`:**
```python
python_requires=">=3.8",
classifiers=[
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
],
```

The codebase uses f-strings (Python 3.6+) and `pathlib.Path` (Python 3.4+), both of which are compatible with the 3.8 floor. No walrus operator (`:=`, Python 3.8+) or `match` statement (Python 3.10+) is used.

### Consequences

**Positive:**
- Python 3.8 was a widely deployed LTS-equivalent version at the time of development, maximising the number of environments where the library can be installed without a Python upgrade.

**Negative:**
- Python 3.8 is now end-of-life and no longer receives security patches. Continuing to support it may expose users to unpatched Python vulnerabilities.
- Python 3.11+ performance improvements and 3.10+ structural pattern matching are not available.
- The classifier list stops at 3.10, meaning the library is not officially declared compatible with Python 3.11, 3.12, or 3.13, even though it likely is. See ADR-040 for detailed analysis.

---

## ADR-015: PEP 8 Code Style and Docstring Convention

**Status:** Accepted

### Context

A consistent code style reduces cognitive overhead for contributors and reviewers. The team needed to establish and enforce a style standard.

### Decision

PEP 8 is adopted as the code style standard. All public classes and functions include Google-style docstrings with `Args:` and `Returns:` sections. This is mandated in `CONTRIBUTING.md`.

**Evidence from `CONTRIBUTING.md`:**
> - Follow PEP 8 guidelines
> - Use meaningful variable and function names
> - Add docstrings to all functions and classes
> - Keep functions focused and concise

**Evidence of consistent docstring style across the codebase (from `utils/auth.py`):**
```python
def get_service_principal_credential(self):
    """Get service principal credential.

    Returns:
        ClientSecretCredential instance
    """
```

**Evidence of consistent docstring style (from `connection_manager.py`):**
```python
def __init__(self, subscription_id, resource_group):
    """Initialize the connection manager.

    Args:
        subscription_id: Azure subscription ID
        resource_group: Resource group name
    """
```

### Consequences

**Positive:**
- Consistent docstrings enable automatic documentation generation (e.g., Sphinx, `pydoc`).
- PEP 8 compliance is verifiable with standard tools (`flake8`, `pylint`, `ruff`).
- Clear `Args:` and `Returns:` sections reduce the need to read implementation code to understand a function's contract.

**Negative:**
- No linter or formatter (`flake8`, `black`, `ruff`) is configured in the repository (no `.flake8`, `pyproject.toml`, or `tox.ini` file exists), meaning PEP 8 compliance is enforced only by convention and code review, not by automated tooling.
- No type annotations are used anywhere in the codebase, despite Python 3.8 supporting them fully. This limits the value of static analysis tools like `mypy`.
- `CONTRIBUTING.md` mentions "Ensure CI checks pass," but no CI configuration file (`.github/workflows/`, `.gitlab-ci.yml`, `Jenkinsfile`) is present in the repository, meaning there is no automated enforcement of the stated standards.

---

## ADR-016: AzureAuthenticator Utility Class as an Optional Strategy Selector

**Status:** Accepted

### Context

The library needs to support both interactive/managed-identity authentication and service principal authentication. The team needed to decide whether to expose a reusable strategy selector as a public utility or keep it internal.

### Decision

`AzureAuthenticator` is implemented as a public utility class in `utils/auth.py` and exported via `avd_manager/utils/__init__.py`, providing a reusable strategy selector for callers who need explicit credential control. However, `ConnectionManager` does not use `AzureAuthenticator`; instead, it directly instantiates `DefaultAzureCredential`.

**Evidence from `avd_manager/utils/__init__.py`:**
```python
from .logger import get_logger
from .auth import AzureAuthenticator

__all__ = ["get_logger", "AzureAuthenticator"]
```

**Evidence from `utils/auth.py`:**
```python
class AzureAuthenticator:
    """Handles Azure authentication methods."""

    def get_credential(self):
        """Get appropriate credential based on configuration."""
        if all([self.tenant_id, self.client_id, self.client_secret]):
            return self.get_service_principal_credential()
        else:
            return self.get_default_credential()
```

**Evidence from `connection_manager.py`:**
```python
from .utils.auth import AzureAuthenticator  # Imported but not used

def authenticate(self):
    """Authenticate with Azure using default credentials."""
    try:
        self.credential = DefaultAzureCredential()  # Direct instantiation, not via AzureAuthenticator
        logger.info("Authentication successful")
        return True
```

### Consequences

**Positive:**
- `AzureAuthenticator` provides a reusable, testable strategy selector for library consumers who need to choose between credential types programmatically.
- The automatic strategy selection in `get_credential()` reduces the risk of misconfiguration for advanced users.
- Exporting `AzureAuthenticator` via `__all__` makes it a first-class public API, signalling its intended use.

**Negative:**
- `AzureAuthenticator` is imported in `connection_manager.py` but never used, creating dead code and confusion about the intended authentication path.
- Two parallel, non-integrated authentication paths exist: `ConnectionManager.authenticate()` (direct `DefaultAzureCredential`) and `AzureAuthenticator.get_credential()` (strategy selection). This duplication violates DRY and creates an undocumented architectural inconsistency. See ADR-030 for detailed analysis.
- Callers may be uncertain whether to use `ConnectionManager` directly or to instantiate `AzureAuthenticator` themselves, as the relationship between the two is not documented.

---

## ADR-017: Config.save() Method for Configuration Persistence

**Status:** Accepted

### Context

Configuration objects may need to be persisted back to disk for operational workflows (e.g., saving updated credentials after a refresh). The team needed to decide whether to support configuration serialisation.

### Decision

The `Config` class includes a `save(output_file)` method that serialises the in-memory configuration dictionary back to a YAML file using `yaml.dump()`.

**Evidence from `config.py`:**
```python
def save(self, output_file):
    """Save configuration to YAML file."""
    with open(output_file, 'w') as f:
        yaml.dump(self.config, f, default_flow_style=False)
    logger.info(f"Configuration saved to {output_file}")
```

### Consequences

**Positive:**
- Callers can persist updated configuration (e.g., after refreshing credentials) without manually serialising the dictionary.
- The method uses `yaml.dump()` with `default_flow_style=False`, producing human-readable YAML output.

**Negative:**
- **Security Risk:** The `save()` method writes the entire configuration dictionary to disk, including plaintext `client_secret`. This is a significant security decision that is not documented in ADR-006 or ADR-009, with no documented threat model or intended use case.
- The method does not preserve comments or formatting from the original YAML file; round-tripping a config file through `load()` and `save()` will lose all comments.
- There is no example or test demonstrating the intended use case for `save()`, leaving its purpose ambiguous.
- Callers may inadvertently commit configuration files containing secrets to version control.

---

## ADR-018: Utilities Sub-package Boundary and Module Organization

**Status:** Accepted

### Context

Cross-cutting concerns (logging, authentication) are shared across multiple layers. The team needed to decide whether to place these utilities in the main package or in a dedicated sub-package.

### Decision

A `utils/` sub-package is created under `avd_manager/` to house cross-cutting concerns. Two modules are included: `logger.py` (logging factory) and `auth.py` (authentication strategy selector). Both are exported via `utils/__init__.py` as first-class public APIs.

**Evidence from `avd_manager/utils/__init__.py`:**
```python
from .logger import get_logger
from .auth import AzureAuthenticator

__all__ = ["get_logger", "AzureAuthenticator"]
```

**Evidence from module structure:**
- `avd_manager/utils/logger.py` — contains `get_logger()` and `setup_file_logging()` functions
- `avd_manager/utils/auth.py` — contains `AzureAuthenticator` class

### Consequences

**Positive:**
- Separating utilities into a sub-package prevents the main `avd_manager/` directory from becoming cluttered with cross-cutting concerns.
- The `utils/` namespace clearly signals that these are shared utilities, not domain-specific logic.
- Exporting utilities via `__all__` makes them discoverable and signals their public API status.

**Negative:**
- The boundary between what belongs in `utils/` and what belongs in the main package is not explicitly documented. Why are `logger.py` and `auth.py` in `utils/` but `config.py` is not?
- Both `get_logger()` and `setup_file_logging()` are module-level functions rather than methods on a class, creating an inconsistent API surface (functions vs. classes).
- The `AzureAuthenticator` class is exported from `utils/__init__.py`, but `ConnectionManager` imports it directly from `utils.auth` and never uses it, creating confusion about the intended API boundary.

---

## ADR-019: Sequential N+1 Query Pattern in monitor_sessions()

**Status:** Accepted

### Context

The `monitor_sessions()` method needs to retrieve all active sessions across all session hosts in a host pool. The team needed to decide between sequential API calls and concurrent/bulk operations.

### Decision

`monitor_sessions()` implements a sequential loop that calls `list_session_hosts()` once, then calls `get_user_sessions()` once per session host, producing N+1 Azure API calls.

**Evidence from `session_handler.py`:**
```python
def monitor_sessions(self, host_pool_name):
    """Monitor all sessions in a host pool."""
    session_hosts = self.list_session_hosts(host_pool_name)  # 1 API call
    all_sessions = []

    for host in session_hosts:  # N iterations
        host_name = host.name.split('/')[-1]
        sessions = self.get_user_sessions(host_pool_name, host_name)  # 1 API call per host
        all_sessions.extend(sessions)

    logger.info(f"Monitoring {len(all_sessions)} total sessions in {host_pool_name}")
    return all_sessions
```

### Consequences

**Positive:**
- Sequential execution is simple to understand and debug.
- No additional concurrency libraries or complexity are required.
- Error handling is straightforward; a failure on one host does not prevent querying other hosts.

**Negative:**
- For a host pool with 100 session hosts, this pattern results in 101 Azure API calls (1 list + 100 individual queries), which is inefficient and slow.
- No concurrent execution is used, despite Python's `concurrent.futures.ThreadPoolExecutor` being available in the standard library.
- The Azure SDK may support bulk or paginated APIs that could reduce the number of calls, but this is not explored or documented.
- No rate-limiting or back-off logic is implemented beyond what the Azure SDK provides internally.

---

## ADR-020: Null-Assignment Disconnect Strategy

**Status:** Accepted

### Context

The `ConnectionManager` manages Azure SDK client lifecycle. The team needed to decide how to clean up resources when disconnecting.

### Decision

The `disconnect()` method nullifies all four client references (`avd_client`, `compute_client`, `network_client`, `credential`) by assigning `None` to each, without calling any SDK-level close or cleanup methods.

**Evidence from `connection_manager.py`:**
```python
def disconnect(self):
    """Close all connections."""
    self.avd_client = None
    self.compute_client = None
    self.network_client = None
    self.credential = None
    logger.info("Disconnected from Azure services")
```

### Consequences

**Positive:**
- Simple and straightforward; no SDK-specific cleanup logic is required.
- Python's garbage collector will eventually reclaim the client objects.
- The Azure SDK clients do not expose explicit `close()` or `cleanup()` methods, so there is no SDK-level cleanup to call.

**Negative:**
- The method does not call any SDK-level cleanup, which may leave resources (e.g., HTTP connections, token refresh threads) in an undefined state.
- There is no documentation explaining whether the Azure SDK clients require explicit teardown or whether null-assignment is sufficient.
- The method does not validate that clients are actually connected before attempting to disconnect; calling `disconnect()` twice is a no-op.

---

## ADR-021: ARM Resource ID String Parsing via Split

**Status:** Accepted

### Context

Azure Resource Manager resource IDs are hierarchical paths (e.g., `/subscriptions/{id}/resourceGroups/{rg}/providers/Microsoft.DesktopVirtualization/hostPools/{pool}`). The team needed to decide how to extract the resource name from the full ID.

### Decision

Resource names are extracted from ARM IDs by splitting on `/` and taking the last segment using `host.name.split('/')[-1]`.

**Evidence from `session_handler.py`:**
```python
def monitor_sessions(self, host_pool_name):
    """Monitor all sessions in a host pool."""
    session_hosts = self.list_session_hosts(host_pool_name)
    all_sessions = []

    for host in session_hosts:
        host_name = host.name.split('/')[-1]  # Extract name from ARM ID
        sessions = self.get_user_sessions(host_pool_name, host_name)
        all_sessions.extend(sessions)
```

**Evidence from `examples/basic_usage.py`:**
```python
if host_pools:
    pool_name = host_pools[0].name.split('/')[-1]  # Extract name from ARM ID
    pool_details = manager.get_host_pool(pool_name)
```

### Consequences

**Positive:**
- Simple and concise; no additional parsing libraries are required.
- Works correctly for the expected ARM ID format.

**Negative:**
- Fragile; the pattern assumes the resource name is always the last segment after splitting on `/`. If the ARM ID format changes or contains trailing slashes, the parsing will fail silently.
- The Azure SDK may provide utilities for parsing ARM IDs (e.g., `azure.core.utils.parse_resource_id()`), but these are not used.
- No error handling; if the split produces an empty string, the method will fail at the next API call with a cryptic error.
- The pattern is repeated in multiple places (`session_handler.py` and `basic_usage.py`), violating DRY.

---

## ADR-022: load_dotenv() Embedded in Config Constructor

**Status:** Accepted

### Context

The `.env` file loading mechanism needs to be integrated into the configuration system. The team needed to decide where to call `load_dotenv()`.

### Decision

`load_dotenv()` is called unconditionally inside `Config.__init__()`, ensuring that `.env` files are loaded whenever a `Config` object is instantiated.

**Evidence from `config.py`:**
```python
def __init__(self, config_file=None):
    """Initialize configuration."""
    load_dotenv()  # Called unconditionally in constructor
    self.config_file = config_file
    self.config = {}
    self._load_config()
    logger.info("Configuration loaded successfully")
```

### Consequences

**Positive:**
- Automatic; callers do not need to remember to call `load_dotenv()` separately.
- Ensures `.env` files are loaded before any configuration is read.

**Negative:**
- **Side Effect:** `load_dotenv()` is called on every `Config` instantiation, which may be unexpected for library consumers who do not use `.env` files.
- **Implicit Behavior:** Library consumers may not be aware that instantiating `Config` has the side effect of loading `.env` files from the current working directory.
- **No Control:** There is no way for callers to opt out of `.env` file loading or to specify a custom `.env` file path.
- **Precedence Confusion:** `load_dotenv()` by default does NOT override existing environment variables (`override=False`), which is the opposite of the YAML-vs-env precedence rule documented in ADR-006 (where environment variables override YAML values). This creates an undocumented inconsistency: if a variable is set in both `.env` and the shell environment, the shell environment wins; but if it's set in both `.env` and a YAML file, the `.env` value wins (because `load_dotenv()` runs first, then `_load_config()` overrides with environment variables).

---

## ADR-023: Unused requests Dependency

**Status:** Accepted

### Context

The `requests` library is a common HTTP client for Python. The team needed to decide whether to include it as a dependency.

### Decision

`requests==2.31.0` is pinned in `requirements.txt` and `requests>=2.31.0` is listed in `setup.py install_requires`, but the library is not imported or used in any of the 7 source `.py` files.

**Evidence from `requirements.txt`:**
```
requests==2.31.0
```

**Evidence from `setup.py`:**
```python
install_requires=[
    ...
    "requests>=2.31.0",
],
```

**Evidence from code search:** No source file imports `requests`.

### Consequences

**Positive:**
- The dependency is available if future functionality requires direct HTTP calls (e.g., calling non-SDK ARM endpoints).
- Pinning the version in `requirements.txt` ensures reproducible builds.

**Negative:**
- Unused dependencies increase the install size and the attack surface for supply-chain vulnerabilities.
- The presence of `requests` without documentation creates confusion about whether it is intended for future use or was included speculatively.
- The Azure SDK clients already handle all HTTP communication via their own internal HTTP clients, making `requests` redundant for current functionality.
- Maintaining an unused dependency creates maintenance burden; version updates must be evaluated even though the library is not used.

**Recommendation:** Either document the planned use case for `requests` or remove it from dependencies.

---

## ADR-024: Unused datetime Import in SessionHandler

**Status:** Accepted

### Context

The `datetime` module is imported at the top of `session_handler.py` but is never referenced anywhere in the module.

### Decision

`from datetime import datetime` is included in `session_handler.py` despite not being used.

**Evidence from `session_handler.py`:**
```python
"""Azure Virtual Desktop Session Handler."""

from datetime import datetime  # Imported but never used
from .utils.logger import get_logger

logger = get_logger(__name__)
```

### Consequences

**Positive:**
- The import is harmless and does not affect runtime behavior.

**Negative:**
- Dead code; the import suggests that timestamp functionality was planned but not implemented.
- Creates confusion about whether timestamps are intended to be added to session monitoring.
- Violates PEP 8 (unused imports should be removed).
- A linter like `flake8` would flag this as an unused import.

**Recommendation:** Either remove the import or implement the timestamp functionality it was intended for (e.g., adding a `timestamp` field to the `monitor_sessions()` return value).

---

## ADR-025: PyYAML Library Choice

**Status:** Accepted

### Context

YAML configuration files need to be parsed. The team needed to decide which YAML library to use.

### Decision

`pyyaml>=6.0.1` is used as the YAML parsing library. The code uses `yaml.safe_load()` to parse YAML files and `yaml.dump()` to serialize configuration back to YAML.

**Evidence from `config.py`:**
```python
import yaml

def _load_config(self):
    if self.config_file and Path(self.config_file).exists():
        with open(self.config_file, 'r') as f:
            self.config = yaml.safe_load(f)  # Safe parsing

def save(self, output_file):
    with open(output_file, 'w') as f:
        yaml.dump(self.config, f, default_flow_style=False)
```

### Consequences

**Positive:**
- `yaml.safe_load()` is used (not `yaml.load()`), preventing arbitrary Python object deserialisation — a critical security best practice.
- PyYAML is the de facto standard YAML library for Python, with broad compatibility and community support.
- Version 6.0.1+ addresses known security vulnerabilities in earlier versions.

**Negative:**
- PyYAML is slower than some alternatives (e.g., `ruamel.yaml`, which also preserves comments and formatting).
- `ruamel.yaml` would be a better choice if round-tripping YAML files (load → modify → save) is important, as it preserves comments and formatting. The current `Config.save()` implementation loses all comments from the original file.
- No alternative YAML libraries were evaluated or documented; the choice of PyYAML is implicit.
- The `yaml.dump()` call in `save()` does not preserve the original YAML structure or comments, making it unsuitable for workflows where configuration files are edited by humans and then reloaded.

---

## ADR-026: python-dotenv Library Choice

**Status:** Accepted

### Context

The `.env` file loading mechanism needs to be implemented. The team needed to decide which library to use.

### Decision

`python-dotenv>=1.0.0` is used to load environment variables from `.env` files. The `load_dotenv()` function is called unconditionally in `Config.__init__()`.

**Evidence from `config.py`:**
```python
from dotenv import load_dotenv

def __init__(self, config_file=None):
    load_dotenv()  # Load .env file
```

### Consequences

**Positive:**
- `python-dotenv` is the de facto standard for `.env` file loading in Python, with broad compatibility and community support.
- The library is lightweight and has no additional dependencies.
- Version 1.0.0+ is stable and well-maintained.

**Negative:**
- `load_dotenv()` by default does NOT override existing environment variables (`override=False`), which is the opposite of the YAML-vs-env precedence rule documented in ADR-006. This creates an undocumented inconsistency. See ADR-022 for detailed analysis.
- Alternative libraries (`environs`, `decouple`, `pydantic-settings`) offer more features (e.g., type coercion, validation) but were not evaluated or documented.
- No configuration option is provided to customize the `.env` file path or to disable `.env` loading entirely.
- The library is called unconditionally in the constructor, creating an implicit side effect that may surprise library consumers. See ADR-022 for detailed analysis.

---

## ADR-027: setuptools.find_packages() Scope and Test Inclusion

**Status:** Accepted

### Context

The `setup.py` script uses `find_packages()` to automatically discover packages. The team needed to decide whether to include test packages in the distribution.

### Decision

`find_packages()` is called without an `exclude` argument, meaning all packages under the repository root are included in the built distribution, including the `tests/` package.

**Evidence from `setup.py`:**
```python
packages=find_packages(),  # No exclude argument
```

### Consequences

**Positive:**
- Automatic discovery reduces the risk of forgetting to include a package.
- Simple and concise; no manual package enumeration is required.

**Negative:**
- **Unintended Inclusion:** The `tests/` package is included in the built distribution, which is not standard practice. Test files should not be shipped to end users.
- **Larger Distribution:** Including test files increases the size of the installed package.
- **Potential Confusion:** Users may be confused by the presence of test files in their installed package.
- **Security:** Test files may contain sensitive information (e.g., mock credentials, test data) that should not be distributed.

**Recommendation:** Use `find_packages(exclude=['tests', 'tests.*'])` to exclude test packages from the distribution.

---

## ADR-028: StreamHandler Output to sys.stdout

**Status:** Accepted

### Context

The logging system needs to output log messages to the console. The team needed to decide whether to use `sys.stdout` or `sys.stderr`.

### Decision

`logging.StreamHandler(sys.stdout)` is used to route all log output to standard output, rather than the conventional `sys.stderr`.

**Evidence from `utils/logger.py`:**
```python
def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        console_handler = logging.StreamHandler(sys.stdout)  # Output to stdout
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger
```

### Consequences

**Positive:**
- Explicit choice; the code clearly specifies `sys.stdout` rather than relying on `StreamHandler` defaults.
- All log output is mixed with application output, which may be desired in some contexts.

**Negative:**
- **Unconventional:** Python logging convention (and POSIX convention) is to send log output to `sys.stderr`, not `sys.stdout`. This deviation from convention may surprise users and make it difficult to separate log output from application output in shell pipelines.
- **Pipeline Issues:** In shell pipelines, `stdout` is typically used for application output and `stderr` for diagnostic output. Sending logs to `stdout` makes it difficult to redirect logs separately from application output (e.g., `python script.py 2>errors.log` will not capture logs).
- **CI/CD Integration:** Many CI/CD systems and log aggregation tools expect logs on `stderr` and application output on `stdout`. This choice may complicate integration with such systems.

**Recommendation:** Change to `logging.StreamHandler(sys.stderr)` to follow Python and POSIX conventions.

---

## ADR-029: setup.py Metadata Omissions

**Status:** Accepted

### Context

The `setup.py` script declares package metadata for PyPI distribution. The team needed to decide which metadata fields to include.

### Decision

The `setup.py` script omits several standard metadata fields: `long_description`, `long_description_content_type`, and `url`.

**Evidence from `setup.py`:**
```python
setup(
    name="avd-manager",
    version="0.1.0",
    description="Azure Virtual Desktop Management Tool",
    author="QA Test Team",
    author_email="qa@example.com",
    packages=find_packages(),
    install_requires=[...],
    python_requires=">=3.8",
    classifiers=[...],
    # Missing: long_description, long_description_content_type, url
)
```

### Consequences

**Positive:**
- Minimal metadata reduces the complexity of `setup.py`.
- The package can still be installed and used without these fields.

**Negative:**
- **PyPI Presentation:** Without `long_description` and `long_description_content_type`, the PyPI package page will only show the short `description` field, providing minimal information to potential users.
- **Discoverability:** Users browsing PyPI will see only a one-line description, making it difficult to understand the package's purpose and features.
- **Missing URL:** Without a `url` field, the PyPI page will not link to the project's repository or documentation, making it difficult for users to find the source code or report issues.
- **Not Ready for PyPI:** These omissions suggest the package is not yet ready for publication on PyPI, but this is not documented.

**Recommendation:** Add `long_description` (from `README.md`), `long_description_content_type="text/markdown"`, and `url` (to the repository) to prepare the package for PyPI publication.

---

## ADR-030: Dual Authentication Implementation Paths

**Status:** Accepted

### Context

The library needs to support both interactive/managed-identity authentication and service principal authentication. The team needed to decide whether to implement a single unified authentication path or multiple parallel paths.

### Decision

Two parallel, non-integrated authentication paths are implemented:

1. **ConnectionManager Path:** `ConnectionManager.authenticate()` directly instantiates `DefaultAzureCredential`.
2. **AzureAuthenticator Path:** `AzureAuthenticator.get_credential()` implements strategy selection between `DefaultAzureCredential` and `ClientSecretCredential`.

**Evidence from `connection_manager.py`:**
```python
from .utils.auth import AzureAuthenticator  # Imported but not used

def authenticate(self):
    """Authenticate with Azure using default credentials."""
    try:
        self.credential = DefaultAzureCredential()  # Direct instantiation
        logger.info("Authentication successful")
        return True
```

**Evidence from `utils/auth.py`:**
```python
class AzureAuthenticator:
    def get_credential(self):
        """Get appropriate credential based on configuration."""
        if all([self.tenant_id, self.client_id, self.client_secret]):
            return self.get_service_principal_credential()
        else:
            return self.get_default_credential()
```

### Consequences

**Positive:**
- `ConnectionManager` provides a simple, zero-configuration path for users who only need `DefaultAzureCredential`.
- `AzureAuthenticator` provides a reusable strategy selector for users who need explicit credential control.
- Both paths are available, providing flexibility for different use cases.

**Negative:**
- **Duplication:** Authentication logic is duplicated across two classes, violating DRY. Both `ConnectionManager.authenticate()` and `AzureAuthenticator.get_default_credential()` instantiate `DefaultAzureCredential`.
- **Inconsistency:** `ConnectionManager` does not use `AzureAuthenticator`, creating an undocumented architectural inconsistency. Callers may be uncertain which path to use.
- **Dead Code:** `AzureAuthenticator` is imported in `connection_manager.py` but never used, creating dead code.
- **No Integration:** There is no way to use `ConnectionManager` with `AzureAuthenticator`'s strategy selection; `ConnectionManager` always uses `DefaultAzureCredential`.

**Recommendation:** Refactor `ConnectionManager.authenticate()` to delegate to `AzureAuthenticator.get_credential()`, eliminating duplication and creating a single unified authentication path.

---

## ADR-031: Context Manager Pattern Not Implemented

**Status:** Accepted

### Context

`ConnectionManager` manages Azure SDK client lifecycle (connect/disconnect). Python's context manager protocol (`__enter__`/`__exit__`) provides a standard way to ensure cleanup code is called even on exceptions.

### Decision

`ConnectionManager` does not implement the context manager protocol. Callers must manually call `disconnect()` to clean up resources.

**Evidence from `basic_usage.py`:**
```python
manager = ConnectionManager(
    config.get('subscription_id'),
    config.get('resource_group')
)

if not manager.connect():
    print("Failed to connect to Azure")
    return

# ... use manager ...

manager.disconnect()  # Manual cleanup; not guaranteed on exception
```

### Consequences

**Positive:**
- Simple and explicit; callers can see exactly when cleanup happens.
- No additional complexity is required.

**Negative:**
- **Error-Prone:** If an exception occurs between `connect()` and `disconnect()`, the cleanup code will not be called, leaving resources in an undefined state.
- **Unconventional:** Python's context manager protocol is the standard way to manage resource lifecycle. Not implementing it violates the principle of least surprise.
- **Example Code Risk:** The example code in `basic_usage.py` calls `disconnect()` only on the happy path, not in exception handlers. This is a poor example for library users.

**Recommendation:** Implement `__enter__()` and `__exit__()` methods on `ConnectionManager` to support the `with` statement:
```python
with ConnectionManager(sub_id, rg) as manager:
    manager.connect()
    # ... use manager ...
    # disconnect() is guaranteed to be called, even on exception
```

---

## ADR-032: Repeated Pre-condition Guard Pattern

**Status:** Accepted

### Context

Multiple methods in `SessionHandler` check the same pre-condition: whether the connection manager's AVD client is available.

### Decision

The pre-condition check is repeated in every public method of `SessionHandler`:

**Evidence from `session_handler.py`:**
```python
def list_session_hosts(self, host_pool_name):
    if not self.connection_manager.avd_client:
        raise ConnectionError("Not connected to Azure services")
    # ... implementation ...

def get_user_sessions(self, host_pool_name, session_host_name):
    if not self.connection_manager.avd_client:
        raise ConnectionError("Not connected to Azure services")
    # ... implementation ...

def disconnect_user_session(self, host_pool_name, session_host_name, session_id):
    if not self.connection_manager.avd_client:
        raise ConnectionError("Not connected to Azure services")
    # ... implementation ...

def get_session_host_status(self, host_pool_name, session_host_name):
    if not self.connection_manager.avd_client:
        raise ConnectionError("Not connected to Azure services")
    # ... implementation ...
```

### Consequences

**Positive:**
- Explicit; each method clearly documents its pre-condition.
- Simple and straightforward; no decorator or base class magic is required.

**Negative:**
- **Code Duplication:** The same 3-line guard is repeated 5 times, violating DRY.
- **Maintenance Burden:** If the guard logic needs to change (e.g., to check multiple conditions), all 5 methods must be updated.
- **Inconsistency Risk:** If one method's guard is updated and others are not, the class behavior becomes inconsistent.

**Recommendation:** Extract the guard into a shared method or decorator:
```python
def _ensure_connected(self):
    if not self.connection_manager.avd_client:
        raise ConnectionError("Not connected to Azure services")

def list_session_hosts(self, host_pool_name):
    self._ensure_connected()
    # ... implementation ...
```

---

## ADR-033: Public active_sessions Dictionary

**Status:** Accepted

### Context

`SessionHandler` maintains local state about active sessions. The team needed to decide whether to expose this state as a public attribute.

### Decision

`SessionHandler.__init__()` initialises `self.active_sessions = {}` as a public instance attribute, but no method ever writes to it.

**Evidence from `session_handler.py`:**
```python
class SessionHandler:
    def __init__(self, connection_manager):
        """Initialize the session handler."""
        self.connection_manager = connection_manager
        self.active_sessions = {}  # Initialised but never populated
        logger.info("Initialized SessionHandler")
```

### Consequences

**Positive:**
- Subclasses can override the attribute to implement custom caching logic.
- Callers can inspect the dictionary to understand the intended data structure.

**Negative:**
- **Unused:** The dictionary is never populated by any method, creating dead code and confusion about its purpose.
- **Undocumented:** There is no documentation explaining what the dictionary is intended to store or when it should be populated.
- **Implicit API Contract:** The presence of the public attribute creates an implicit API contract that subclasses or callers may rely on, even though it is not used in the current implementation.
- **Future Inconsistency Risk:** If the dictionary is populated in the future without a proper invalidation strategy, it could become stale and cause subtle bugs.

**Recommendation:** Either remove the attribute or implement the caching logic it was intended for, with proper documentation and invalidation strategy.

---

## ADR-034: Singleton Logger via Python Registry

**Status:** Accepted

### Context

The logging system needs to ensure that each named logger is created only once, avoiding duplicate handler registration.

### Decision

The `get_logger()` function uses Python's global logger registry (via `logging.getLogger(name)`) combined with a handler-check guard to implement a singleton pattern for each logger name.

**Evidence from `utils/logger.py`:**
```python
def get_logger(name, level=logging.INFO):
    logger = logging.getLogger(name)  # Returns singleton from registry
    
    if not logger.handlers:  # Guard against duplicate handlers
        logger.setLevel(level)
        console_handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(...)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    
    return logger
```

### Consequences

**Positive:**
- Leverages Python's built-in logger registry, which is thread-safe and well-tested.
- The handler-check guard prevents duplicate handler registration when `get_logger` is called multiple times for the same logger name.
- Simple and idiomatic Python logging pattern.

**Negative:**
- **Thread Safety:** The `if not logger.handlers:` check is not atomic. In a multi-threaded environment, two threads could both pass the check and both add handlers, resulting in duplicate handlers. Python's GIL provides some protection, but this is not guaranteed.
- **Implicit Singleton:** The singleton pattern is implicit via Python's logger registry, which may surprise callers unfamiliar with Python's logging module.
- **Global State:** The logger registry is global, meaning all loggers are shared across the entire process. This can cause issues in tests or in applications that use multiple independent instances of the library.

---

## ADR-035: Error Handling Inconsistency in basic_usage.py

**Status:** Accepted

### Context

The example code in `basic_usage.py` demonstrates how to use the library. The team needed to decide how to handle errors in the example.

### Decision

The example code calls `manager.get_host_pool(pool_name)` and immediately accesses the `name` attribute without checking for `None`, despite the method returning `None` on failure.

**Evidence from `basic_usage.py`:**
```python
if host_pools:
    pool_name = host_pools[0].name.split('/')[-1]
    pool_details = manager.get_host_pool(pool_name)  # Returns None on failure
    print(f"Host Pool Details: {pool_details.name}")  # Accesses .name without None check
    print(f"  Type: {pool_details.host_pool_type}")
    print(f"  Load Balancer: {pool_details.load_balancer_type}")
```

**Evidence from `connection_manager.py`:**
```python
def get_host_pool(self, host_pool_name):
    """Get details of a specific host pool."""
    if not self.avd_client:
        raise ConnectionError("Not connected to Azure services")

    try:
        host_pool = self.avd_client.host_pools.get(...)
        logger.info(f"Retrieved host pool: {host_pool_name}")
        return host_pool
    except Exception as e:
        logger.error(f"Failed to get host pool {host_pool_name}: {str(e)}")
        return None  # Returns None on failure
```

### Consequences

**Positive:**
- The example code is concise and easy to read.

**Negative:**
- **Error-Prone:** If `get_host_pool()` fails and returns `None`, the example code will crash with `AttributeError: 'NoneType' object has no attribute 'name'`.
- **Poor Example:** The example code does not demonstrate proper error handling, which may lead library users to write unsafe code.
- **Inconsistency:** ADR-009 documents the error-handling policy (swallow and return empty), but the example code does not follow this policy by checking for `None`.

**Recommendation:** Add a `None` check in the example code:
```python
pool_details = manager.get_host_pool(pool_name)
if pool_details:
    print(f"Host Pool Details: {pool_details.name}")
else:
    print(f"Failed to retrieve host pool details for {pool_name}")
```

---

## ADR-036: Partial Configuration Validation

**Status:** Accepted

### Context

The `Config` class needs to validate that required configuration values are present. The team needed to decide which fields are required.

### Decision

The `validate()` method checks only two fields as required: `subscription_id` and `resource_group`. The authentication fields (`tenant_id`, `client_id`, `client_secret`) are not validated.

**Evidence from `config.py`:**
```python
def validate(self):
    """Validate required configuration values."""
    required_fields = ['subscription_id', 'resource_group']
    missing_fields = [field for field in required_fields if not self.config.get(field)]

    if missing_fields:
        error_msg = f"Missing required configuration: {', '.join(missing_fields)}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.info("Configuration validation passed")
    return True
```

### Consequences

**Positive:**
- Allows flexibility; callers can use `DefaultAzureCredential` without providing service principal credentials.
- Validation is fast and simple; only two fields are checked.

**Negative:**
- **Incomplete Validation:** If a caller provides `client_id` and `client_secret` but forgets `tenant_id`, the validation will pass, but authentication will fail later at runtime.
- **Two-Tier Validation:** The validation model is unclear: why are infrastructure fields (`subscription_id`, `resource_group`) required but authentication fields are not?
- **Late Error Detection:** Missing authentication fields are not caught until `authenticate()` is called, making debugging more difficult.
- **No Guidance:** There is no documentation explaining which fields are required for which authentication scenarios.

**Recommendation:** Implement a more sophisticated validation model that checks authentication fields based on the intended credential type:
```python
def validate(self, require_service_principal=False):
    required_fields = ['subscription_id', 'resource_group']
    if require_service_principal:
        required_fields.extend(['tenant_id', 'client_id', 'client_secret'])
    # ... check required_fields ...
```

---

## ADR-037: Unused Compute and Network Clients

**Status:** Accepted

### Context

`ConnectionManager` instantiates three Azure SDK clients: `DesktopVirtualizationMgmtClient`, `ComputeManagementClient`, and `NetworkManagementClient`. The team needed to decide whether to instantiate all three or only the ones currently used.

### Decision

All three clients are instantiated in `connect()`, but only `DesktopVirtualizationMgmtClient` (stored as `avd_client`) is used in any current method. `ComputeManagementClient` and `NetworkManagementClient` are instantiated but never used.

**Evidence from `connection_manager.py`:**
```python
def connect(self):
    """Establish connections to Azure services."""
    if not self.credential:
        if not self.authenticate():
            raise ConnectionError("Failed to authenticate")

    try:
        self.avd_client = DesktopVirtualizationMgmtClient(...)  # Used
        self.compute_client = ComputeManagementClient(...)  # Not used
        self.network_client = NetworkManagementClient(...)  # Not used
        logger.info("Successfully connected to Azure services")
        return True
```

### Consequences

**Positive:**
- The clients are available for future functionality without requiring changes to `connect()`.
- Callers can access the clients directly if needed (e.g., `manager.compute_client.virtual_machines.list(...)`).

**Negative:**
- **Wasted Resources:** Instantiating unused clients adds latency to `connect()` and consumes memory.
- **SDK Initialization Overhead:** Each SDK client instantiation may trigger network activity (e.g., metadata endpoint discovery), adding latency.
- **Confusing API:** The presence of unused clients in the facade violates the principle of least surprise. Callers may assume these clients are used internally.
- **Over-Provisioning:** The facade is over-provisioned for current functionality, which contradicts ADR-004's goal of simplifying the API.

**Recommendation:** Remove the unused clients from `connect()` and add them only when needed for future functionality.

---

## ADR-038: Root Logger Attachment in setup_file_logging()

**Status:** Accepted

### Context

The `setup_file_logging()` function adds file-based logging to the application. The team needed to decide which logger to attach the file handler to.

### Decision

`setup_file_logging()` attaches a `FileHandler` to the root logger (via `logging.getLogger()` with no arguments), which captures log output from all loggers in the process, including those from third-party libraries.

**Evidence from `utils/logger.py`:**
```python
def setup_file_logging(log_file, level=logging.INFO):
    """Setup file logging for the application."""
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(level)
    
    formatter = logging.Formatter(...)
    file_handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()  # Root logger
    root_logger.addHandler(file_handler)  # Captures all loggers
```

### Consequences

**Positive:**
- Captures all log output from all libraries, providing a comprehensive log file.
- Simple and straightforward; no filtering is required.

**Negative:**
- **Verbose Logs:** The log file will capture logs from all libraries (Azure SDK, urllib3, etc.), which may be very verbose and difficult to parse.
- **Unintended Capture:** Logs from third-party libraries that the user did not intend to capture are included, making the log file larger and harder to analyze.
- **No Control:** There is no way to filter or exclude logs from specific libraries.

**Recommendation:** Attach the file handler to the `avd_manager` package logger specifically:
```python
def setup_file_logging(log_file, level=logging.INFO):
    # ... setup file_handler ...
    package_logger = logging.getLogger('avd_manager')
    package_logger.addHandler(file_handler)
```

---

## ADR-039: Legacy setup.py Format vs. Modern pyproject.toml

**Status:** Accepted

### Context

Python packaging has evolved from `setup.py` to the modern `pyproject.toml` format (PEP 517/518). The team needed to decide which format to use.

### Decision

The legacy `setup.py` format is used exclusively. No `pyproject.toml` file is present, and no `[build-system]` table is defined.

**Evidence from `setup.py`:**
```python
from setuptools import setup, find_packages

setup(
    name="avd-manager",
    version="0.1.0",
    # ... metadata ...
)
```

### Consequences

**Positive:**
- Familiar to developers who have used Python packaging for many years.
- Works with older build tools and CI/CD systems.

**Negative:**
- **Legacy Format:** `setup.py` is the old packaging format. PEP 517/518 compliant build frontends (`build`, `pip` with `--no-build-isolation`) may behave differently than expected.
- **No Build System Declaration:** Without a `[build-system]` table in `pyproject.toml`, the build system is implicit (assumed to be `setuptools`), which may cause issues with modern build tools.
- **Maintenance Burden:** The `setup.py` format is less maintainable than `pyproject.toml`, which uses declarative TOML syntax.
- **Future Incompatibility:** Python packaging tools are moving away from `setup.py`. Future versions of `pip` and other tools may drop support for `setup.py` without a `pyproject.toml`.

**Recommendation:** Migrate to `pyproject.toml` with a `[build-system]` table:
```toml
[build-system]
requires = ["setuptools>=45", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "avd-manager"
version = "0.1.0"
description = "Azure Virtual Desktop Management Tool"
# ... other metadata ...
```

---

## ADR-040: Python Version Classifier Ceiling

**Status:** Accepted

### Context

The `setup.py` classifiers declare which Python versions the package supports. The team needed to decide which versions to list.

### Decision

The classifiers list only Python 3.8, 3.9, and 3.10, stopping at 3.10. Python 3.11, 3.12, and 3.13 are not listed, despite being currently active releases.

**Evidence from `setup.py`:**
```python
classifiers=[
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    # Missing: 3.11, 3.12, 3.13
],
```

### Consequences

**Positive:**
- Conservative; only versions that have been explicitly tested are declared as supported.
- Avoids making unsupported claims about compatibility.

**Negative:**
- **Ambiguous Compatibility:** Users browsing PyPI will not know whether the package works on Python 3.11, 3.12, or 3.13, even though it likely does.
- **Discoverability:** PyPI may not recommend the package to users on Python 3.11+, reducing discoverability.
- **Outdated:** Python 3.10 was released in October 2021. The classifier list has not been updated in over 2 years, suggesting the package is not actively maintained.
- **No Policy:** There is no documented policy for when new Python versions will be added to the classifier list.

**Recommendation:** Add classifiers for Python 3.11, 3.12, and 3.13 (after testing on those versions), and establish a policy for updating classifiers when new Python versions are released:
```python
classifiers=[
    ...
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Programming Language :: Python :: 3.13",
],
```

---

## Summary Table

| ADR | Decision | Status | Key Trade-off |
|---|---|---|---|
| ADR-001 | Python 3.8+ as implementation language | Accepted | Ecosystem richness vs. static typing |
| ADR-002 | Official Azure Python SDKs for ARM integration | Accepted | Convenience vs. large dependency footprint |
| ADR-003 | Three-layer architecture (Config / Connection / Session) | Accepted | Separation of concerns vs. cross-layer coupling |
| ADR-004 | Facade pattern over Azure SDK clients | Accepted | Simplified API vs. incomplete coverage |
| ADR-005 | Dependency injection of ConnectionManager into SessionHandler | Accepted | Testability vs. runtime ordering responsibility |
| ADR-006 | Dual config: YAML file + environment variables (env wins) | Accepted | Flexibility vs. silent override risk |
| ADR-007 | DefaultAzureCredential + ClientSecretCredential strategy | Accepted | Broad compatibility vs. duplicated auth logic |
| ADR-008 | stdlib `logging` with centralised factory | Accepted | Zero dependencies vs. unstructured log output |
| ADR-009 | Mixed error handling: raise on pre-condition, swallow on API failure | Accepted | Caller convenience vs. loss of error specificity |
| ADR-010 | `setuptools` / `setup.py` for packaging | Accepted | Familiarity vs. legacy format |
| ADR-011 | `unittest` + `unittest.mock` for testing | Accepted | Zero test dependencies vs. limited coverage |
| ADR-012 | No local storage; Azure ARM as system of record | Accepted | Simplicity vs. N+1 API call performance |
| ADR-013 | Library-first design; no CLI or REST API | Accepted | Reusability vs. operator accessibility |
| ADR-014 | Minimum Python version 3.8 | Accepted | Broad compatibility vs. EOL security risk |
| ADR-015 | PEP 8 + Google-style docstrings, no automated enforcement | Accepted | Readability vs. no linter/CI guardrails |
| ADR-016 | AzureAuthenticator as optional strategy selector | Accepted | Flexibility vs. duplication with ConnectionManager |
| ADR-017 | Config.save() for configuration persistence | Accepted | Convenience vs. security risk (plaintext secrets) |
| ADR-018 | Utilities sub-package for cross-cutting concerns | Accepted | Organization vs. unclear boundary |
| ADR-019 | Sequential N+1 query pattern in monitor_sessions() | Accepted | Simplicity vs. performance (101 API calls) |
| ADR-020 | Null-assignment disconnect strategy | Accepted | Simplicity vs. undefined resource state |
| ADR-021 | ARM resource ID string parsing via split | Accepted | Simplicity vs. fragility |
| ADR-022 | load_dotenv() embedded in Config constructor | Accepted | Convenience vs. implicit side effects |
| ADR-023 | Unused requests dependency | Accepted | Future-proofing vs. supply-chain risk |
| ADR-024 | Unused datetime import in SessionHandler | Accepted | Placeholder for future feature vs. dead code |
| ADR-025 | PyYAML library choice | Accepted | Standard library vs. comment preservation |
| ADR-026 | python-dotenv library choice | Accepted | Standard library vs. precedence confusion |
| ADR-027 | setuptools.find_packages() includes tests | Accepted | Automatic discovery vs. unintended inclusion |
| ADR-028 | StreamHandler output to sys.stdout | Accepted | Explicit choice vs. unconventional |
| ADR-029 | setup.py metadata omissions | Accepted | Minimal metadata vs. PyPI discoverability |
| ADR-030 | Dual authentication implementation paths | Accepted | Flexibility vs. duplication and inconsistency |
| ADR-031 | Context manager pattern not implemented | Accepted | Simplicity vs. error-prone resource cleanup |
| ADR-032 | Repeated pre-condition guard pattern | Accepted | Explicit vs. code duplication |
| ADR-033 | Public active_sessions dictionary | Accepted | Extensibility vs. unused dead code |
| ADR-034 | Singleton logger via Python registry | Accepted | Idiomatic vs. thread-safety concerns |
| ADR-035 | Error handling inconsistency in basic_usage.py | Accepted | Conciseness vs. poor example |
| ADR-036 | Partial configuration validation | Accepted | Flexibility vs. incomplete validation |
| ADR-037 | Unused compute and network clients | Accepted | Future-proofing vs. wasted resources |
| ADR-038 | Root logger attachment in setup_file_logging() | Accepted | Comprehensive logging vs. verbose logs |
| ADR-039 | Legacy setup.py format vs. modern pyproject.toml | Accepted | Familiarity vs. future incompatibility |
| ADR-040 | Python version classifier ceiling at 3.10 | Accepted | Conservative vs. ambiguous compatibility |

---

## Document Revision History

| Version | Date | Changes |
|---|---|---|
| 1.0 | Initial | Original 15 ADRs |
| 2.0 | Updated | Added 25 new ADRs (ADR-016 through ADR-040) addressing all TODO items with real code evidence |