# BrowserSessionManager + Async Jobs Design

Status: design target after repair `v0.0.278.1`  
Scope: Promptbranch browser-backed ChatGPT operations

## Problem

The current browser-backed service can create multiple `ChatGPTAutomationService` instances for different project URLs. Those instances may still use the same persistent Chromium profile directory.

A persistent browser profile is writable shared state. It contains cookies, local storage, IndexedDB, service-worker state, browser preferences, session state, and Chromium singleton ownership artifacts.

The safe invariant is:

```text
one writable browser profile -> one active Promptbranch browser owner
```

`v0.0.278.1` adds a coarse profile-scoped repair lock. That is intentionally conservative. It prevents the observed overlap class, but it is not the final orchestration model.

## Repair invariant in v0.0.278.1

All browser-backed operations sharing the same resolved profile directory are serialized by a profile-scoped lock.

This covers operations such as:

```text
ask_question_result
list_projects
list_project_chats
get_chat
list_project_sources
add_project_source
remove_project_source
download_chat_artifact
project debug flows
```

The container service also no longer clears Chromium `Singleton*` profile artifacts by default.

## Target architecture

```text
Promptbranch service
  └── BrowserSessionManager
        ├── owns one persistent Chromium profile
        ├── owns lifecycle for browser/context/page resources
        ├── accepts typed browser jobs
        ├── serializes browser mutations
        ├── exposes job status/result records
        ├── allows backend-only reads outside browser queue
        └── records evidence and recovery hints
```

## Typed operation classes

```text
backend_read
  no browser profile ownership required
  may run concurrently

browser_read
  uses browser state but does not mutate project/source state
  initially serialized; later may be multiplexed through one owner

browser_mutation
  changes ChatGPT project/source/chat state
  serialized strictly

ask_wait
  submits prompt and waits for assistant completion
  represented as a long-running job

source_mutation
  source add/remove/sync
  transactional mutation queue
```

## Async job model

Long-running browser operations should not hold one blocking HTTP request until completion.

Target API shape:

```text
POST /v1/jobs/ask
  -> returns job_id quickly

GET /v1/jobs/{job_id}
  -> queued | running | stabilizing | completed | failed | timed_out

GET /v1/jobs/{job_id}/result
  -> final structured result, if completed
```

A CLI call such as `pb ask` can still behave synchronously by polling the job endpoint, but the result must remain recoverable if the CLI times out or disconnects.

## Backend-first reads

Where possible, read operations should avoid browser ownership entirely.

Preferred read order:

```text
1. backend/network payload
2. persisted Promptbranch state or job records
3. browser DOM fallback
4. visual/OCR fallback only as last resort
```

Examples:

```text
project list      -> backend first
chat/task list    -> backend/state first
latest answer     -> persisted job/task records first
source list       -> backend first where available, browser fallback otherwise
```

## Transactional mutation queue

Source and project mutations must be modeled as transactions:

```text
trigger
  -> wait for settled/backend-confirmed state
  -> re-read/verify persistence
  -> update Promptbranch state only after verification
```

Never:

```text
click and assume success
refresh immediately after save
clear Chromium singleton files while another operation may be active
update local state before persistence is verified
```

## Migration path

### Step 1: repair lock

Implemented by `v0.0.278.1`.

### Step 2: BrowserSessionManager skeleton

Introduce a service-owned manager with a typed operation queue. Keep existing automation methods as execution backends.

### Step 3: job records

Persist job metadata and final results under `.pb_profile/jobs/` or the service runtime equivalent.

### Step 4: async ask

Move `pb ask` to submit/poll/result while preserving the existing operator-facing command behavior.

### Step 5: transactional source queue

Move source add/remove/sync into explicit transaction records with before/after evidence.

## Non-goals for the repair

`v0.0.278.1` does not implement the full manager, job store, backend extraction, or queue taxonomy. It only restores the critical safety invariant that one profile is not driven concurrently by multiple service instances.
