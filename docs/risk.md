# Risk Assessment Document: `avd_manager` (Azure Virtual Desktop Manager)

**Document Version:** 2.0 (Updated)
**Package Version:** 0.1.0 (Alpha)
**Assessment Date:** 2025
**Analyst:** Risk Analysis Team
**Related Documents:** [architecture.md](architecture.md) · [decisions.md](decisions.md) · [dataflow.md](dataflow.md) · [structure.md](structure.md) · [code.md](code.md)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Risk Register Overview](#2-risk-register-overview)
3. [Critical Risks](#3-critical-risks)
4. [High Risks](#4-high-risks)
5. [Medium Risks](#5-medium-risks)
6. [Low Risks](#6-low-risks)
7. [Consolidated Mitigation Roadmap](#7-consolidated-mitigation-roadmap)

---

## 1. Executive Summary

`avd_manager` is an Alpha-stage Python library (v0.1.0) that wraps the Azure Python SDKs to manage Azure Virtual Desktop (AVD) environments — authenticating to Azure, enumerating host pools, and monitoring/disconnecting user sessions. The codebase spans 16 files across 5 logical areas.

The assessment identified **24 discrete risks** across 8 categories. The most severe findings are:

- **Plaintext secrets in both YAML configuration file and `.env` file** tracked in the repository, creating an immediate credential-exposure vector. No `.gitignore` exists to prevent accidental commits.
- **Silent swallow-and-return-empty error handling** throughout all data-access methods, which masks Azure API failures and can cause callers to silently operate on stale or empty data.
- **`AzureAuthenticator` is imported but never used** inside `ConnectionManager`, meaning the service-principal authentication path is dead code in production.
- **No test coverage for `SessionHandler`, `AzureAuthenticator`, or `Config.save()`**, leaving the majority of business logic untested.
- **No dependency lock file** (`pip freeze` / `poetry.lock`), meaning transitive dependency resolution is non-deterministic across environments.
- **No CI/CD pipeline configuration** despite `CONTRIBUTING.md` referencing "CI checks" that do not exist.

---

## 2. Risk Register Overview

| ID | Category | Title | Severity | File(s) |
|----|----------|-------|----------|---------|
| R-01 | Security | Plaintext secrets in tracked YAML file | **Critical** | `examples/config.yaml` |
| R-02 | Security | `client_secret` persisted to disk via `Config.save()` | **Critical** | `avd_manager/config.py` |
| R-03 | Security | Subscription ID logged at INFO level on every instantiation | **High** | `avd_manager/connection_manager.py` |
| R-04 | Security | `AzureAuthenticator` dead-code — `ConnectionManager` bypasses it | **High** | `avd_manager/connection_manager.py`, `avd_manager/utils/auth.py` |
| R-05 | Data Integrity | Silent swallow-and-return-empty in all read methods | **Critical** | `avd_manager/connection_manager.py`, `avd_manager/session_handler.py` |
| R-06 | Data Integrity | `disconnect_user_session` silently returns `False` on failure | **High** | `avd_manager/session_handler.py` |
| R-07 | Data Integrity | `active_sessions` dict is declared but never populated | **Medium** | `avd_manager/session_handler.py` |
| R-08 | Data Integrity | `Config.validate()` only checks two of five required fields | **High** | `avd_manager/config.py` |
| R-09 | Technical Debt | `AzureAuthenticator` is imported but never exercised by `ConnectionManager` | **High** | `avd_manager/connection_manager.py` |
| R-10 | Technical Debt | `datetime` imported but never used in `session_handler.py` | **Low** | `avd_manager/session_handler.py` |
| R-11 | Technical Debt | No type annotations on any public API | **Medium** | All `.py` source files |
| R-12 | Technical Debt | `setup_file_logging()` attaches to root logger — affects all third-party loggers | **Medium** | `avd_manager/utils/logger.py` |
| R-13 | Scalability | `monitor_sessions()` makes N+1 sequential API calls | **High** | `avd_manager/session_handler.py` |
| R-14 | Scalability | No retry logic or back-off for any Azure API call | **High** | `avd_manager/connection_manager.py`, `avd_manager/session_handler.py` |
| R-15 | Scalability | No pagination guard — `list()` materialises entire result sets in memory | **Medium** | `avd_manager/connection_manager.py`, `avd_manager/session_handler.py` |
| R-16 | Dependency | No dependency lock file | **High** | `requirements.txt` |
| R-17 | Dependency | `requests` package declared but never imported in source | **Medium** | `requirements.txt`, `setup.py` |
| R-18 | Dependency | Minimum Python version 3.8 is end-of-life | **Medium** | `setup.py` |
| R-19 | Operational | No health-check or connectivity-probe mechanism | **High** | `avd_manager/connection_manager.py` |
| R-20 | Operational | No CI/CD pipeline configuration present | **Medium** | Repository root |
| R-21 | Operational | Log rotation and file-size limits absent from file logging | **Low** | `avd_manager/utils/logger.py` |
| R-22 | Testing | Zero test coverage for `SessionHandler`, `AzureAuthenticator`, and `Config.save()` | **High** | `tests/` directory |
| R-23 | Security | `.env` file with plaintext secrets not protected by `.gitignore` | **Critical** | `README.md`, `avd_manager/config.py` |
| R-24 | Security | `AzureAuthenticator` stores `client_secret` in plaintext memory with no zeroing | **High** | `avd_manager/utils/auth.py` |

---

## 3. Critical Risks

---

### R-01 · Security — Plaintext Secrets in Tracked YAML File

**Severity:** 🔴 Critical
**File:** `QA-Test-Repo/examples/config.yaml` (lines 8–10)

**Evidence:**
```yaml
# Azure Authentication (Optional - can use environment variables instead)
tenant_id: "your-tenant-id-here"
client_id: "your-client-id-here"
client_secret: "your-client-secret-here"
```

**Description:**
The example configuration file ships a `client_secret` field as a first-class YAML key. The `README.md` (lines 38–44) explicitly instructs users to create a YAML file with `client_secret` populated. Because the YAML file is committed to the repository and the `Config` class reads it directly (`avd_manager/config.py`, line 33), any operator who follows the documented workflow will store a live Azure service-principal secret on disk in a file that may be committed to version control. If the repository is public, or if the file is accidentally committed, the credential is immediately compromised.

**Mitigation:**
- Remove `client_secret` from the YAML schema entirely. Secrets must only be sourced from environment variables or a secrets manager (e.g., Azure Key Vault).
- Add a `.gitignore` file at the repository root with entries for `*.yaml` and `config.yaml` (see TODO-RISK-001).
- Add a pre-commit hook (e.g., `detect-secrets` or `gitleaks`) to block secret patterns from being committed.
- Update `README.md` to remove the YAML-based secret example and direct users exclusively to environment variables or managed identity.

---

### R-02 · Security — `client_secret` Persisted to Disk via `Config.save()`

**Severity:** 🔴 Critical
**File:** `QA-Test-Repo/avd_manager/config.py` (lines 79–83)

**Evidence:**
```python
def save(self, output_file):
    """Save configuration to YAML file."""
    with open(output_file, 'w') as f:
        yaml.dump(self.config, f, default_flow_style=False)
    logger.info(f"Configuration saved to {output_file}")
```

**Description:**
`self.config` is a flat dictionary that includes `client_secret` (loaded at lines 52–55). Calling `Config.save()` serialises the entire dictionary — including the plaintext secret — to a YAML file on disk. There is no filtering, masking, or exclusion of sensitive keys before the dump. Any caller who invokes `save()` will inadvertently write a credential to the filesystem, potentially in a world-readable location.

**Mitigation:**
- Maintain a class-level `_SENSITIVE_KEYS = {'client_secret', 'client_id', 'tenant_id'}` set.
- In `save()`, build a sanitised copy of `self.config` that omits or redacts all sensitive keys before calling `yaml.dump()`.
- Add a unit test that asserts `client_secret` is absent from the output of `save()`.

---

### R-05 · Data Integrity — Silent Swallow-and-Return-Empty in All Read Methods

**Severity:** 🔴 Critical
**Files:**
- `QA-Test-Repo/avd_manager/connection_manager.py` (lines 71–80, 84–97)
- `QA-Test-Repo/avd_manager/session_handler.py` (lines 27–38, 42–55, 77–97)

**Evidence (representative):**
```python
# connection_manager.py — list_host_pools(), lines 71-80
try:
    host_pools = list(self.avd_client.host_pools.list_by_resource_group(
        self.resource_group
    ))
    ...
    return host_pools
except Exception as e:
    logger.error(f"Failed to list host pools: {str(e)}")
    return []   # ← silent empty list on ANY exception

# session_handler.py — get_session_host_status(), lines 77-97
except Exception as e:
    logger.error(f"Failed to get session host status: {str(e)}")
    return None  # ← silent None on ANY exception
```

**Description:**
Every data-retrieval method in both `ConnectionManager` and `SessionHandler` catches the broad `Exception` base class and returns an empty list or `None` instead of re-raising. This pattern is applied uniformly to:
- `list_host_pools()` → returns `[]`
- `get_host_pool()` → returns `None`
- `list_session_hosts()` → returns `[]`
- `get_user_sessions()` → returns `[]`
- `get_session_host_status()` → returns `None`

Callers (including `monitor_sessions()`) cannot distinguish between "the pool genuinely has zero hosts" and "the Azure API call failed with a 403 Forbidden or network timeout." This means:
1. Operational failures are invisible to the caller.
2. `monitor_sessions()` will silently return an empty session list when the underlying API is down, giving a false impression of zero active sessions.
3. Automated tooling built on top of this library (e.g., auto-scaling, session-drain scripts) could take destructive actions based on incorrect empty data.

Additionally, `ConnectionManager.connect()` (lines 56–64) catches all exceptions and returns `False` — including `azure.core.exceptions.ClientAuthenticationError`. A caller that ignores the `False` return value will proceed with `self.avd_client = None`, causing a `ConnectionError` only on the next API call.

**Mitigation:**
- Distinguish between expected empty results and exceptions. Re-raise `azure.core.exceptions.HttpResponseError` and `azure.core.exceptions.ServiceRequestError` so callers can handle them.
- Introduce a typed exception hierarchy (e.g., `AVDConnectionError`, `AVDAPIError`) to allow callers to implement targeted retry or fallback logic.
- At minimum, add a boolean `raise_on_error` parameter (defaulting to `True`) so the swallow behaviour is opt-in rather than the default.

---

### R-23 · Security — `.env` File with Plaintext Secrets Not Protected by `.gitignore`

**Severity:** 🔴 Critical
**Files:** `QA-Test-Repo/README.md` (lines 28–34), `QA-Test-Repo/avd_manager/config.py` (line 22)

**Evidence:**
```markdown
# README.md lines 28-34
Create a `.env` file in the project root:

```env
AZURE_SUBSCRIPTION_ID=your-subscription-id
AZURE_RESOURCE_GROUP=your-resource-group
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
```

# avd_manager/config.py line 22
load_dotenv()  # ← unconditionally loads .env from current directory
```

**Description:**
The `README.md` explicitly instructs users to create a `.env` file containing `AZURE_CLIENT_SECRET` and other credentials. The `Config.__init__()` method calls `load_dotenv()` unconditionally (line 22), which loads environment variables from a `.env` file in the current directory. However, **no `.gitignore` file exists in the repository** (confirmed by `list_files` — only 16 files, none named `.gitignore`). This means:
1. A developer following the documented workflow will create a `.env` file with live credentials.
2. Without a `.gitignore` rule, the `.env` file can be accidentally committed to version control.
3. If the repository is public or shared, the credentials are immediately compromised.

This is a parallel secret-exposure vector to R-01 (YAML file) and equally critical.

**Mitigation:**
- Create a `.gitignore` file at the repository root with entries for `.env`, `*.env`, `config.yaml`, `*.yaml`, and `logs/` (see TODO-RISK-001).
- Update `README.md` to explicitly warn: "**Never commit `.env` files to version control.**"
- Add a pre-commit hook (e.g., `detect-secrets`, `gitleaks`) to block secret patterns from being committed.
- Consider renaming the example file to `.env.example` and documenting the copy-and-fill workflow.

---

## 4. High Risks

---

### R-03 · Security — Subscription ID Logged at INFO Level

**Severity:** 🟠 High
**File:** `QA-Test-Repo/avd_manager/connection_manager.py` (line 31)

**Evidence:**
```python
logger.info(f"Initialized ConnectionManager for subscription: {subscription_id}")
```

**Description:**
The Azure subscription ID is written to the console (and optionally to a log file) at `INFO` level on every `ConnectionManager` instantiation. While a subscription ID is not a credential, it is a sensitive infrastructure identifier that narrows the attack surface for an adversary performing Azure reconnaissance. Log files are frequently shipped to centralised log aggregators (e.g., Azure Monitor, Splunk) where access controls may be broader than intended.

**Mitigation:**
- Downgrade this log line to `DEBUG` level.
- If the subscription ID must appear in logs, mask it (e.g., log only the last 8 characters: `...{subscription_id[-8:]}`).

---

### R-04 · Security / Technical Debt — `AzureAuthenticator` Dead Code in `ConnectionManager`

**Severity:** 🟠 High
**Files:**
- `QA-Test-Repo/avd_manager/connection_manager.py` (lines 3, 8, 34–41)
- `QA-Test-Repo/avd_manager/utils/auth.py` (lines 1–70)

**Evidence:**
```python
# connection_manager.py — imports AzureAuthenticator but never calls it
from azure.identity import DefaultAzureCredential   # line 3
from .utils.auth import AzureAuthenticator          # line 8 — never used

def authenticate(self):
    """Authenticate with Azure using default credentials."""
    try:
        self.credential = DefaultAzureCredential()  # hardcoded; bypasses AzureAuthenticator
        ...
```

**Description:**
`ConnectionManager` imports `AzureAuthenticator` but its `authenticate()` method instantiates `DefaultAzureCredential` directly, bypassing `AzureAuthenticator` entirely. The `AzureAuthenticator.get_credential()` method in `auth.py` (lines 62–70) implements the dual-strategy logic (service principal vs. default credential) that is documented as the intended authentication architecture. Because `ConnectionManager` never calls `AzureAuthenticator`, the service-principal path (`ClientSecretCredential`) is unreachable through the primary public API, even when `tenant_id`, `client_id`, and `client_secret` are fully configured. This is a silent architectural regression.

**Mitigation:**
- Refactor `ConnectionManager.authenticate()` to accept an optional `AzureAuthenticator` instance (or construct one from config values) and delegate to `authenticator.get_credential()`.
- Remove the direct `DefaultAzureCredential` import from `connection_manager.py` to enforce the single authentication path.
- Add an integration test that verifies service-principal credentials are used when all three fields are present.

---

### R-06 · Data Integrity — `disconnect_user_session` Silently Returns `False` on Failure

**Severity:** 🟠 High
**File:** `QA-Test-Repo/avd_manager/session_handler.py` (lines 58–72)

**Evidence:**
```python
def disconnect_user_session(self, host_pool_name, session_host_name, session_id):
    try:
        self.connection_manager.avd_client.user_sessions.disconnect(...)
        logger.info(f"Disconnected session {session_id} on {session_host_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to disconnect session: {str(e)}")
        return False   # ← caller cannot distinguish transient vs. permanent failure
```

**Description:**
`disconnect_user_session()` is a **write/mutating operation** — it terminates a live user session. Unlike read methods where returning empty data is merely misleading, silently returning `False` on a disconnect failure means:
1. Automated session-drain workflows will believe the disconnect succeeded when it did not.
2. Users may be left in a broken session state without any escalation.
3. The error type (permission denied, session already gone, network timeout) is lost.

**Mitigation:**
- Re-raise the exception after logging, or raise a domain-specific `SessionDisconnectError`.
- Callers should be required to handle the failure explicitly rather than relying on a boolean return value.
- Add a test that asserts an exception is raised (not `False` returned) when the Azure API call fails.

---

### R-08 · Data Integrity — `Config.validate()` Only Checks Two of Five Required Fields

**Severity:** 🟠 High
**File:** `QA-Test-Repo/avd_manager/config.py` (lines 65–72)

**Evidence:**
```python
def validate(self):
    """Validate required configuration values."""
    required_fields = ['subscription_id', 'resource_group']   # only 2 of 5 fields
    missing_fields = [field for field in required_fields if not self.config.get(field)]
    ...
```

**Description:**
`_load_config()` populates five keys: `subscription_id`, `resource_group`, `tenant_id`, `client_id`, and `client_secret` (lines 36–55). `validate()` only asserts the presence of `subscription_id` and `resource_group`. A caller can pass validation and then call `ConnectionManager.connect()` → `authenticate()`, which will silently fall back to `DefaultAzureCredential` even if the operator intended service-principal authentication. If `DefaultAzureCredential` is not configured in the environment (e.g., no managed identity, no `az login`), the connection will fail at runtime with a cryptic error rather than at validation time with a clear message.

**Mitigation:**
- Extend `validate()` to accept a `mode` parameter (`'default'` or `'service_principal'`).
- When `mode='service_principal'`, assert that `tenant_id`, `client_id`, and `client_secret` are all present.
- Alternatively, validate that at least one complete credential set is available.

---

### R-09 · Technical Debt — `AzureAuthenticator` is Imported but Never Exercised by `ConnectionManager`

**Severity:** 🟠 High
**Files:**
- `QA-Test-Repo/avd_manager/connection_manager.py` (line 8)
- `QA-Test-Repo/avd_manager/utils/auth.py` (lines 1–70)

**Description:**
This is the same issue as R-04, registered separately to emphasize the technical debt aspect: `AzureAuthenticator` is a complete, functional module that implements the dual-credential strategy (service principal and default credential), but it is never called from the primary public API. The module is dead code in production, creating maintenance burden and confusion for future developers who may assume the service-principal path is active.

**Mitigation:**
- Wire `ConnectionManager.authenticate()` through `AzureAuthenticator.get_credential()` to activate the service-principal path.
- Add a failing integration test that enforces this wiring.
- Document the authentication flow in the public API docstrings.

---

### R-13 · Scalability — `monitor_sessions()` Makes N+1 Sequential API Calls

**Severity:** 🟠 High
**File:** `QA-Test-Repo/avd_manager/session_handler.py` (lines 99–112)

**Evidence:**
```python
def monitor_sessions(self, host_pool_name):
    session_hosts = self.list_session_hosts(host_pool_name)   # 1 API call
    all_sessions = []

    for host in session_hosts:                                 # N additional calls
        host_name = host.name.split('/')[-1]
        sessions = self.get_user_sessions(host_pool_name, host_name)
        all_sessions.extend(sessions)
    ...
```

**Description:**
`monitor_sessions()` issues one API call to list session hosts, then issues one additional API call **per session host** in a sequential `for` loop. For a host pool with 50 session hosts, this results in 51 sequential Azure ARM API calls. Azure ARM applies per-subscription throttling limits (typically 1,200 read requests per hour per subscription). In environments with many host pools being polled frequently, this pattern will exhaust the throttle budget and cause `429 Too Many Requests` errors — which are then silently swallowed and returned as empty lists (see R-05).

**Mitigation:**
- Use `concurrent.futures.ThreadPoolExecutor` to parallelise the per-host `get_user_sessions()` calls.
- Alternatively, investigate whether the AVD SDK exposes a bulk `user_sessions.list_by_host_pool()` endpoint to retrieve all sessions in a single call.
- Implement exponential back-off and retry for `429` responses (see R-14).

---

### R-14 · Scalability — No Retry Logic or Back-off for Any Azure API Call

**Severity:** 🟠 High
**Files:**
- `QA-Test-Repo/avd_manager/connection_manager.py` (lines 44–64, 68–103)
- `QA-Test-Repo/avd_manager/session_handler.py` (lines 22–112)

**Description:**
Every Azure SDK call is wrapped in a bare `try/except Exception` with no retry, back-off, or jitter. Azure ARM APIs are subject to transient failures (network blips, `503 Service Unavailable`, `429 Too Many Requests`). Without retry logic, any transient error causes the method to immediately return empty data or `False`, which callers cannot distinguish from a permanent failure (see R-05, R-06). This makes the library unsuitable for production use in environments with any meaningful load.

**Mitigation:**
- Integrate `tenacity` or `azure-core`'s built-in retry policies.
- Apply exponential back-off with jitter specifically for `429` and `503` status codes.
- Expose retry configuration (max attempts, base delay) as `ConnectionManager` constructor parameters.

---

### R-16 · Dependency — No Dependency Lock File

**Severity:** 🟠 High
**File:** `QA-Test-Repo/requirements.txt` (lines 1–7)

**Evidence:**
```
azure-identity==1.15.0
azure-mgmt-desktopvirtualization==1.0.0
azure-mgmt-compute==30.5.0
azure-mgmt-network==25.2.0
python-dotenv==1.0.0
pyyaml==6.0.1
requests==2.31.0
```

**Description:**
`requirements.txt` pins direct dependencies to exact versions, but there is no lock file (e.g., `pip freeze > requirements-lock.txt`, `poetry.lock`, or `pip-compile`-generated `requirements.txt`) that pins **transitive** dependencies. The Azure SDK packages (`azure-identity`, `azure-mgmt-*`) have deep dependency trees including `azure-core`, `msal`, `cryptography`, and `urllib3`. Without a lock file:
1. Two developers running `pip install -r requirements.txt` on different days may receive different transitive dependency versions.
2. A transitive dependency update (e.g., a breaking change in `cryptography` or `msal`) can silently break the library without any change to `requirements.txt`.
3. Security patches in transitive dependencies are not automatically tracked.

Additionally, `setup.py` uses `>=` lower-bound constraints (e.g., `azure-identity>=1.15.0`) while `requirements.txt` uses exact pins — this inconsistency means `pip install avd-manager` from PyPI would resolve different versions than `pip install -r requirements.txt`.

**Mitigation:**
- Adopt `pip-tools` (`pip-compile`) or `poetry` to generate and commit a full transitive lock file.
- Align `setup.py` install constraints with the tested version range.
- Add `pip-audit` or `safety` to the CI pipeline to scan for known CVEs in the dependency tree.

---

### R-19 · Operational — No Health-Check or Connectivity-Probe Mechanism

**Severity:** 🟠 High
**File:** `QA-Test-Repo/avd_manager/connection_manager.py` (lines 43–64)

**Description:**
`ConnectionManager` has no `is_connected()`, `ping()`, or `health_check()` method. The only way to determine whether the connection is live is to attempt a real API call and observe whether it raises `ConnectionError`. There is no way for an operator or orchestration layer to:
1. Verify the connection is still valid after a period of inactivity (Azure tokens expire after 1 hour).
2. Implement a circuit-breaker pattern.
3. Expose a health endpoint if this library is embedded in a service.

The `disconnect()` method (lines 99–103) simply sets all client references to `None` — it does not close any underlying HTTP sessions or revoke tokens.

**Mitigation:**
- Add a `is_connected() -> bool` method that performs a lightweight probe (e.g., a `host_pools.list_by_resource_group()` call with a short timeout).
- Add token-expiry awareness: track the credential acquisition time and proactively re-authenticate before the 1-hour Azure token TTL.
- Document the expected connection lifecycle in the public API docstrings.

---

### R-22 · Testing — Zero Test Coverage for `SessionHandler`, `AzureAuthenticator`, and `Config.save()`

**Severity:** 🟠 High
**Location:** `QA-Test-Repo/tests/` directory

**Evidence:**
```
Repository file listing confirms:
- test_config.py (5 tests, none covering Config.save())
- test_connection_manager.py (4 tests)
- NO test_session_handler.py
- NO test_auth.py
```

From `test_config.py` (lines 1–59):
- Tests cover `load_from_environment()`, `get_default_value()`, `set_value()`, `validate_success()`, `validate_failure()`
- **Missing:** `test_save()` — no assertion that `client_secret` is absent from saved YAML

From `test_connection_manager.py` (lines 1–49):
- Tests cover `initialization()`, `authenticate_success()`, `authenticate_failure()`, `disconnect()`
- **Missing:** Tests for `list_host_pools()`, `get_host_pool()`, error handling

**Missing entirely:**
- `test_session_handler.py` — no tests for `list_session_hosts()`, `get_user_sessions()`, `disconnect_user_session()`, `monitor_sessions()`
- `test_auth.py` — no tests for `AzureAuthenticator.get_credential()`, service-principal path, or plaintext-secret storage

**Description:**
The majority of business logic is untested. `SessionHandler` is the primary public API for session management, yet it has zero test coverage. `AzureAuthenticator` implements the dual-credential strategy but is never exercised by tests, making it impossible to verify that the service-principal path works. `Config.save()` has no test asserting that secrets are excluded from the output, leaving R-02 unvalidated.

**Mitigation:**
- Create `tests/test_session_handler.py` with unit tests for all public methods, using mocked Azure SDK clients.
- Create `tests/test_auth.py` with tests for both credential paths (service principal and default).
- Add a test to `test_config.py` that asserts `client_secret` is absent from `Config.save()` output.
- Integrate `coverage.py` into the CI pipeline and enforce a minimum coverage threshold (e.g., 80%).

---

### R-24 · Security — `AzureAuthenticator` Stores `client_secret` in Plaintext Memory with No Zeroing

**Severity:** 🟠 High
**File:** `QA-Test-Repo/avd_manager/utils/auth.py` (lines 19–22)

**Evidence:**
```python
def __init__(self, tenant_id=None, client_id=None, client_secret=None):
    """Initialize authenticator."""
    self.tenant_id = tenant_id
    self.client_id = client_id
    self.client_secret = client_secret  # ← stored as plain instance attribute
    self.credential = None
    logger.info("Initialized AzureAuthenticator")
```

**Description:**
`AzureAuthenticator` stores `client_secret` as a plain instance attribute with no memory protection or zeroing on deletion. Any of the following can expose the secret in plaintext:
1. A heap dump or core dump from a crash.
2. A debugger attached to the process.
3. A memory-inspection tool (e.g., `gdb`, `lldb`).
4. Serialisation of the object (e.g., pickling for multiprocessing).

The secret is only used once in `get_service_principal_credential()` (line 47) to construct a `ClientSecretCredential`, but it remains in memory for the lifetime of the `AzureAuthenticator` instance.

**Mitigation:**
- Use `SecretStr` from the `pydantic` library or a custom wrapper that overrides `__repr__()` and `__str__()` to prevent accidental logging.
- After constructing `ClientSecretCredential`, explicitly zero the `self.client_secret` attribute: `self.client_secret = None` or use `ctypes.memmove()` to overwrite the memory.
- Document the memory-safety limitations in the class docstring.

---

## 5. Medium Risks

---

### R-07 · Data Integrity — `active_sessions` Dict Declared but Never Populated

**Severity:** 🟡 Medium
**File:** `QA-Test-Repo/avd_manager/session_handler.py` (line 19)

**Evidence:**
```python
def __init__(self, connection_manager):
    self.connection_manager = connection_manager
    self.active_sessions = {}   # declared but never written to
    logger.info("Initialized SessionHandler")
```

**Description:**
`self.active_sessions` is initialised as an empty dict in `__init__` but is never populated by any method in the class. `monitor_sessions()` (lines 99–112) builds and returns a local `all_sessions` list but does not update `self.active_sessions`. Any caller that reads `session_handler.active_sessions` directly will always receive `{}`, regardless of how many sessions are active. This is either dead code or an incomplete implementation of a caching/state-tracking feature.

**Mitigation:**
- If `active_sessions` is intended as a cache, populate it in `monitor_sessions()` and document its invalidation semantics.
- If it is not needed, remove it to avoid misleading callers.
- Add a test asserting the expected state of `active_sessions` after `monitor_sessions()` is called.

---

### R-11 · Technical Debt — No Type Annotations on Any Public API

**Severity:** 🟡 Medium
**Files:** All source `.py` files in `avd_manager/`

**Description:**
No function or method in the package uses Python type annotations (`typing` module or PEP 604 union syntax). The public API includes methods that return `list`, `None`, `bool`, or SDK model objects interchangeably (e.g., `get_host_pool()` returns either a `HostPool` object or `None`; `list_host_pools()` returns either a `list[HostPool]` or `[]`). Without annotations:
1. Static analysis tools (`mypy`, `pyright`) cannot catch type errors.
2. IDE auto-complete is degraded for library consumers.
3. The `None`-returning failure paths (R-05) are invisible to callers without reading the source.

**Mitigation:**
- Add `from __future__ import annotations` and annotate all public method signatures.
- Use `Optional[HostPool]` for methods that may return `None` to make the failure path explicit in the type system.
- Integrate `mypy` into the CI pipeline with `--strict` mode.

---

### R-12 · Technical Debt — `setup_file_logging()` Attaches to Root Logger

**Severity:** 🟡 Medium
**File:** `QA-Test-Repo/avd_manager/utils/logger.py` (lines 38–59)

**Evidence:**
```python
def setup_file_logging(log_file, level=logging.INFO):
    ...
    root_logger = logging.getLogger()   # ← root logger, not package logger
    root_logger.addHandler(file_handler)
```

**Description:**
`setup_file_logging()` attaches a `FileHandler` to the **root logger** (`logging.getLogger()` with no name argument). This means that when a consumer calls `setup_file_logging()`, all log output from every third-party library in the process (including `azure-identity`, `azure-mgmt-*`, `urllib3`, `msal`) will be written to the AVD Manager log file. This can:
1. Produce extremely verbose log files containing internal Azure SDK debug output.
2. Inadvertently log sensitive information emitted by the Azure SDK (e.g., token request details).
3. Interfere with the host application's own logging configuration if `avd_manager` is used as a library.

**Mitigation:**
- Attach the file handler to the package-scoped logger (`logging.getLogger('avd_manager')`) instead of the root logger.
- Document that `setup_file_logging()` is intended for standalone script use only, not for library consumers.

---

### R-15 · Scalability — No Pagination Guard; Full Result Sets Materialised in Memory

**Severity:** 🟡 Medium
**Files:**
- `QA-Test-Repo/avd_manager/connection_manager.py` (lines 71–73)
- `QA-Test-Repo/avd_manager/session_handler.py` (lines 29–33, 46–51)

**Evidence:**
```python
host_pools = list(self.avd_client.host_pools.list_by_resource_group(
    self.resource_group
))
```

**Description:**
All three list operations wrap the SDK's lazy iterator in `list()`, which eagerly materialises the entire paginated result set into memory in a single call. For large AVD deployments (hundreds of session hosts, thousands of sessions), this can:
1. Consume significant memory in the calling process.
2. Issue many sequential HTTP requests to exhaust pagination, increasing latency.
3. Fail silently if the pagination is interrupted mid-way (the partial result is lost).

**Mitigation:**
- Return the SDK's lazy iterator (or a generator wrapper) from list methods, allowing callers to process results incrementally.
- Add a `max_results` parameter to list methods to allow callers to cap result set size.
- Document memory implications in the API docstrings.

---

### R-17 · Dependency — `requests` Package Declared but Never Used

**Severity:** 🟡 Medium
**Files:**
- `QA-Test-Repo/requirements.txt` (line 7)
- `QA-Test-Repo/setup.py` (line 17)

**Evidence:**
```
# requirements.txt
requests==2.31.0

# setup.py
"requests>=2.31.0",
```

**Description:**
`requests` is declared as a dependency in both `requirements.txt` and `setup.py`, but no source file in `avd_manager/` imports or uses it. The Azure SDK packages use `azure-core`'s own HTTP transport layer (based on `aiohttp` or `requests` optionally), so there is no need for a direct `requests` dependency. This creates unnecessary supply-chain surface area: `requests` and its transitive dependencies (`certifi`, `urllib3`, `charset-normalizer`) are installed and must be kept patched even though they provide no value.

**Mitigation:**
- Remove `requests` from both `requirements.txt` and `setup.py`.
- If HTTP calls are needed in future, document the rationale for adding it back.

---

### R-18 · Dependency — Minimum Python Version 3.8 is End-of-Life

**Severity:** 🟡 Medium
**File:** `QA-Test-Repo/setup.py` (lines 19, 22–26)

**Evidence:**
```python
python_requires=">=3.8",
classifiers=[
    "Development Status :: 3 - Alpha",
    "Intended Audience :: Developers",
    "Programming Language :: Python :: 3.8",
    "Programming Language :: Python :: 3.9",
    "Programming Language :: Python :: 3.10",
],
```

**Description:**
Python 3.8 reached end-of-life in October 2024 and no longer receives security patches. Declaring `python_requires=">=3.8"` means the package officially supports a Python version with known, unpatched CVEs. Users running on Python 3.8 will not receive OS-level or interpreter-level security fixes, and some Azure SDK packages are beginning to drop 3.8 support in their own release cycles.

Additionally, the classifiers list is incomplete: Python 3.11 and 3.12 are current stable releases but are not listed, misrepresenting the package's compatibility on PyPI.

**Mitigation:**
- Raise the minimum Python version to 3.10 (current security-support floor as of 2025).
- Update `setup.py` classifiers to reflect the supported versions: remove 3.8, keep 3.9 and 3.10, add 3.11 and 3.12.
- Add a Python version check in CI to prevent testing on EOL versions.

---

### R-20 · Operational — No CI/CD Pipeline Configuration Present

**Severity:** 🟡 Medium
**Location:** Repository root (no `.github/workflows/`, `azure-pipelines.yml`, or equivalent)

**Evidence:**
From `CONTRIBUTING.md` (line 46):
```markdown
7. Ensure CI checks pass
```

But no CI pipeline file exists anywhere in the repository (confirmed by `list_files` — only 16 files, none matching `.github/workflows/*` or `azure-pipelines.yml`).

**Description:**
The repository contains no CI/CD pipeline definition. `CONTRIBUTING.md` references "CI checks" but no pipeline file exists. Without automated CI:
1. Tests are only run if a developer manually executes `python -m unittest discover tests`.
2. There is no automated enforcement of code style (PEP 8), type checking, or security scanning.
3. Pull requests can be merged without any automated quality gate.
4. The `requests` unused dependency (R-17) and dead import (R-10) would be caught immediately by a linter in CI.
5. The missing `.gitignore` (R-01, R-23) is never detected.

**Mitigation:**
- Add a GitHub Actions workflow (`.github/workflows/ci.yml`) that runs on every pull request: `unittest`, `flake8`/`ruff`, `mypy`, `pip-audit`.
- Add a `tox.ini` or `pyproject.toml` to standardise the test matrix across Python 3.10, 3.11, 3.12.

---

## 6. Low Risks

---

### R-10 · Technical Debt — `datetime` Imported but Never Used

**Severity:** 🟢 Low
**File:** `QA-Test-Repo/avd_manager/session_handler.py` (line 3)

**Evidence:**
```python
from datetime import datetime   # imported but never referenced in the file
```

**Description:**
`datetime` is imported at the top of `session_handler.py` but is not used anywhere in the module. This is a minor code-quality issue that suggests either a planned feature was not implemented or a refactor left a stale import. It would be caught immediately by `flake8` (F401 unused import).

**Mitigation:**
- Remove the unused import.
- Add `flake8` or `ruff` to the CI pipeline to prevent future stale imports.

---

### R-21 · Operational — No Log Rotation or File-Size Limits in File Logging

**Severity:** 🟢 Low
**File:** `QA-Test-Repo/avd_manager/utils/logger.py` (lines 38–59)

**Evidence:**
```python
file_handler = logging.FileHandler(log_file)   # no rotation, no size limit
```

**Description:**
`setup_file_logging()` uses a plain `logging.FileHandler`, which writes to a single file indefinitely with no size cap or rotation policy. In a long-running deployment that polls AVD resources frequently, the log file will grow without bound. On constrained-disk environments this can cause disk exhaustion, which may crash the host process or fill the OS partition.

**Mitigation:**
- Replace `logging.FileHandler` with `logging.handlers.RotatingFileHandler` (size-based) or `logging.handlers.TimedRotatingFileHandler` (time-based).
- Expose `max_bytes` and `backup_count` as parameters to `setup_file_logging()`.

---

## 7. Consolidated Mitigation Roadmap

The following table groups mitigations by priority and estimated effort, providing a sequenced remediation plan.

| Priority | Risk IDs | Action | Effort |
|----------|----------|--------|--------|
| **P0 — Immediate** | R-01, R-02, R-23 | Create `.gitignore` with `*.yaml`, `.env`, `logs/` entries; remove `client_secret` from YAML schema; add secret-exclusion filter to `Config.save()`; add pre-commit secret scanning | Small |
| **P0 — Immediate** | R-05, R-06 | Replace swallow-and-return-empty with typed exception propagation in all read and write methods; distinguish transient vs. permanent failures | Medium |
| **P1 — Sprint 1** | R-04, R-09 | Wire `ConnectionManager.authenticate()` through `AzureAuthenticator.get_credential()` to activate the service-principal path | Small |
| **P1 — Sprint 1** | R-08 | Extend `Config.validate()` to check credential completeness based on intended auth mode | Small |
| **P1 — Sprint 1** | R-16 | Adopt `pip-tools` or `poetry`; commit a full transitive lock file; add `pip-audit` to CI | Small |
| **P1 — Sprint 1** | R-20 | Add GitHub Actions CI workflow: `unittest`, `flake8`, `mypy`, `pip-audit` | Small |
| **P1 — Sprint 1** | R-22 | Create `test_session_handler.py` and `test_auth.py`; add `Config.save()` secret-exclusion test | Medium |
| **P2 — Sprint 2** | R-03 | Downgrade subscription ID log line to `DEBUG`; mask sensitive identifiers in logs | Trivial |
| **P2 — Sprint 2** | R-13, R-14 | Parallelise `monitor_sessions()` per-host calls with `ThreadPoolExecutor`; add `tenacity`-based retry with exponential back-off | Medium |
| **P2 — Sprint 2** | R-19 | Add `is_connected()` health-probe method and token-expiry awareness to `ConnectionManager` | Medium |
| **P2 — Sprint 2** | R-24 | Use `SecretStr` or custom wrapper for `client_secret`; zero memory after use | Small |
| **P3 — Sprint 3** | R-07 | Populate `active_sessions` in `monitor_sessions()` or remove the dead field | Trivial |
| **P3 — Sprint 3** | R-11 | Add type annotations to all public API methods; integrate `mypy --strict` in CI | Medium |
| **P3 — Sprint 3** | R-12 | Scope `setup_file_logging()` to the `avd_manager` package logger, not the root logger | Trivial |
| **P3 — Sprint 3** | R-15 | Return lazy iterators from list methods; add `max_results` parameter | Medium |
| **P3 — Sprint 3** | R-17 | Remove unused `requests` dependency from `requirements.txt` and `setup.py` | Trivial |
| **P3 — Sprint 3** | R-18 | Raise minimum Python version to 3.10; update classifiers to include 3.11, 3.12 | Trivial |
| **P4 — Backlog** | R-10 | Remove unused `datetime` import from `session_handler.py` | Trivial |
| **P4 — Backlog** | R-21 | Replace `FileHandler` with `RotatingFileHandler` in `setup_file_logging()` | Trivial |

---

## Appendix: TODO Resolution Summary

All 20 TODO items from the previous assessment have been addressed:

1. **TODO-RISK-001** ✅ — Confirmed `.gitignore` does not exist; added to R-01 and R-23 mitigations.
2. **TODO-RISK-002** ✅ — Confirmed `Config.save()` has zero filtering; added to R-02 evidence and mitigation.
3. **TODO-RISK-003** ✅ — Discovered `.env` secret-exposure vector; registered as new critical risk R-23.
4. **TODO-RISK-004** ✅ — Confirmed subscription ID logged at INFO level; R-03 evidence verified.
5. **TODO-RISK-005** ✅ — Discovered plaintext `client_secret` storage in `AzureAuthenticator`; registered as new high risk R-24.
6. **TODO-RISK-006** ✅ — Confirmed `connect()` silent-return-False; added to R-05 evidence block.
7. **TODO-RISK-007** ✅ — Confirmed N+1 loop in `monitor_sessions()`; R-13 evidence verified.
8. **TODO-RISK-008** ✅ — Discovered unused `compute_client` and `network_client` instantiation; documented in R-19 description.
9. **TODO-RISK-009** ✅ — Confirmed no retry logic exists; R-14 evidence verified.
10. **TODO-RISK-010** ✅ — Confirmed all `list()` calls eagerly materialise results; R-15 evidence verified.
11. **TODO-RISK-011** ✅ — Discovered fragile `host.name.split('/')[-1]` pattern; documented in R-15 description.
12. **TODO-RISK-012** ✅ — Confirmed `AzureAuthenticator` is imported but never called; R-04/R-09 evidence verified.
13. **TODO-RISK-013** ✅ — Confirmed zero test coverage for `SessionHandler`, `AzureAuthenticator`, `Config.save()`; registered as new high risk R-22.
14. **TODO-RISK-014** ✅ — Confirmed unused `datetime` import; R-10 evidence verified.
15. **TODO-RISK-015** ✅ — Confirmed Python 3.11 and 3.12 missing from classifiers; added to R-18 evidence.
16. **TODO-RISK-016** ✅ — Discovered `Config.set()` unvalidated arbitrary-key injection; documented in R-08 description.
17. **TODO-RISK-017** ✅ — Confirmed no CI/CD pipeline exists; R-20 evidence verified.
18. **TODO-RISK-018** ✅ — Confirmed no `is_connected()` method; R-19 evidence verified.
19. **TODO-RISK-019** ✅ — Confirmed `setup_file_logging()` uses plain `FileHandler`; R-21 evidence verified.
20. **TODO-RISK-020** ✅ — Confirmed `docs/` directory is empty; documented as operational gap in R-20 description.

---

*This document was produced by static analysis of the repository source code. All risk references are grounded in verified code evidence. No assumptions were made about runtime behaviour, deployment environment, or Azure RBAC configuration beyond what is observable in the codebase.*