# K8s Game MVP Contract

## Project identity

```text
project_id: k8s-game-mvp
purpose: controlled test vehicle for JSON orchestration state
```

The game is not the product. The orchestration model is the product.

## Game concept

```text
Click the pod before it disappears.
```

Minimal future behavior:

```text
- player sees a pod object
- player clicks the pod to score points
- countdown timer runs
- final score is displayed
- browser page is served from a container
- Kubernetes manifests deploy the app
```

## First implementation target

The first implementation release is intentionally static-first:

```text
Browser
  ↓
Static HTML/CSS/JS game
  ↓
Nginx container
  ↓
Kubernetes Deployment
  ↓
Service
  ↓
Ingress or port-forward fallback
```

## v0.1.0 role

v0.1.0 does not implement the game.

v0.1.0 defines the orchestration contract and state surfaces needed before game implementation starts.

## Allowed first implementation scope, later release

```text
- static browser game
- score counter
- countdown timer
- pod click behavior
- Dockerfile
- nginx static container
- Kubernetes Deployment
- Service
- Ingress or documented port-forward fallback
- README
- basic smoke test
- orchestration stage trace
```

## Explicitly out of scope for first implementation

```text
- FastAPI backend
- database
- authentication
- leaderboard
- multiplayer
- WebSockets
- Helm chart
- full CI/CD
- production-grade observability
```

## Default deployment assumptions

```text
namespace: k8s-game-mvp unless operator overrides later
runtime: browser-only static app for first implementation
exposure: ingress or port-forward fallback
production_allowed: false
smoke_test_required: true
```
