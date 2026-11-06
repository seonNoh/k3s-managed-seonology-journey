# Seonology Journey

[English](README.md) | [한국어](README.ko.md) | [日本語](README.ja.md)

Seonology Journey manages travel plans and records in a monorepo with React, Android, a Go REST/WebSocket API, a Go gRPC back service, and shared Protobuf contracts.

## Architecture

![Architecture](assets/diagrams/service-architecture.svg)

Web and Android send REST requests to the API. The API forwards user identity as gRPC metadata to the back service, which stores travel data and media metadata in DynamoDB. Keycloak supplies client sign-in and JWT public keys. The back entrypoint connects media URL generation to `StubPresigner`; its default base is `https://journey-media.seonology.local`, with a 15-minute expiry.

| Interface | Behavior |
| --- | --- |
| `/api/v1` | Travel, days, schedules, meals, accommodation, expenses, notes, checklists, reservations, companions, tags, templates, favorites, shares, media and statistics. REST JSON uses Protobuf field names in camelCase. |
| `GET /api/v1/external/geocode?q=...` | Delegates to OpenStreetMap Nominatim through back. |
| `GET /api/v1/nearby`, `GET /api/v1/transit` | API calls Google Places/Directions; response cache and daily counter are process-local. |
| `GET /api/v1/external/exchange-rate` | Returns fixed rates; unmatched currency pairs return 1. |
| `GET /api/v1/external/weather` | Returns gRPC Unimplemented, mapped to HTTP 501. |
| `GET /ws/trips/{tripId}` | Server WebSocket route. Handles ping/pong and location_update/location envelopes. |
| `GET /healthz`, `GET /readyz` | API liveness; readiness calls back GetExchangeRate with a 2-second timeout. |
| `POST /internal/publish` | Requires X-Internal-Token matching API_INTERNAL_TOKEN and broadcasts to the API instance’s trip hub. The back PublishEvent RPC returns an empty response. |

## Components

![Components](assets/diagrams/component-delivery.svg)

| Path | Role | Output |
| --- | --- | --- |
| `apps/web` | React 18 / Vite 5 | `seonology-journey-web` |
| `apps/api` | REST / WebSocket gateway | `seonology-journey-api` |
| `apps/back` | gRPC / DynamoDB service | `seonology-journey-back` |
| `apps/android` | Kotlin / Jetpack Compose | Android application |
| `proto` | Protobuf contracts and generated clients | Go / TypeScript |
| `deploy` | Standalone Kustomize resources | Production Argo CD source is in central GitOps. |
| `scripts` | AWS setup, local tables and sample data | Shell / Python scripts |

## Requirements

- Node.js >=20.18.0 and pnpm 9.15.9; Gitea web CI uses Node 22 and the web Dockerfile uses Node 20.
- Go >=1.25.0; Gitea CI uses golang:1.25.14-bookworm.
- JDK 21 and Android SDK 35 for Android; minimum device API 26 and Gradle wrapper 8.10.2.
- Docker, QEMU and Buildx for multi-architecture images; Buf for Protobuf generation.

## Quick start

The web development server listens on port 5173. Set VITE_API_BASE and Keycloak build-time variables before starting Vite when using different services.

```bash
corepack enable
corepack prepare pnpm@9.15.9 --activate
pnpm install --frozen-lockfile
pnpm --filter @seonology/journey-web dev
```

Run the two Go commands in separate terminals from the repository root. For local Go processes, provide AWS credentials and DynamoDB tables (or DYNAMODB_ENDPOINT), Keycloak settings and any external API keys before starting the services. API and back listen on 8080 and 9090; their metrics ports are 8081 and 9091.

```bash
BACK_GRPC_ADDR=localhost:9090 go -C apps/api run ./cmd/server
go -C apps/back run ./cmd/server
```

The Compose file provides only DynamoDB Local (8000) and its admin UI (8001); local data is held in memory. It does not start the application services. `make proto` runs `buf generate` under `proto/`.

## Checks

```bash
python3 verify.py --skip-components
python3 verify.py
```

The first command checks documentation, generated diagrams, repository rules and workflow files. The second also runs Go vet/race tests/builds and web typecheck/tests/build. Android is handled by its own workflow.

## Delivery

Gitea is the source of truth. Its push mirror copies branches and tags to `seonNoh/k3s-managed-seonology-journey` on GitHub with `sync_on_commit: true`. Use the Gitea `origin` remote for pushes.

| Workflow / job | Trigger | Steps and conditions |
| --- | --- | --- |
| `ci.yml / verify` | main push, main PR, manual | Checkout → Repository contract → Go services → Web test and build. |
| `images.yml / publish` | main push; api-v*, back-v*, web-v* tag; manual | Checkout → QEMU → Buildx → Registry login → serial build/publish/index checks. No dependency on ci.yml. |
| `gitea-android-ci.yml / android` | main PR touching apps/android/** or this workflow; manual | Checkout → Test and assemble debug application, using linux/amd64 android-sdk:35. |
| `gitea-release.yml / create-release` | api-v*, back-v*, web-v*, android-v* tag push | Create Gitea release. Requires component-vX.Y.Z; an existing release is left unchanged. |

The images job loops API → back → web. A component tag selects only that component. Main/manual builds use the highest version-sorted existing component tag, so every selected component needs one. Each image under `git.seonology.com/seonology/seonology-journey-{api,back,web}` receives `X.Y.Z`, `sha-<7>` and `latest`; each index contains `linux/amd64` and `linux/arm64`. Registry login uses PACKAGE_USER/PACKAGE_TOKEN; release publication uses GITEA_TOKEN.

The `apps/*/.releaserc.json` files define `api-vX.Y.Z`, `back-vX.Y.Z`, `web-vX.Y.Z` and `android-vX.Y.Z`. Explicit rules for each component scope and `all` map feat to minor, fix/perf/refactor to patch, and breaking changes to major. Gitea workflows publish existing tags; they contain no semantic-release invocation.

```bash
git push origin main
git push origin api-vX.Y.Z
```

## Operations

![Operations](assets/diagrams/runtime-cutover.svg)

Argo CD Application `seonology-journey-monorepo` reads `workloads/seonology-journey/overlays/production` from `seonology/seonology-k3s` into namespace `seonology-journey`. Image Updater tracks each Gitea `latest` digest, writes the Kustomization on `main`, and Argo CD uses automated prune/self-heal. The overlay pins image digests. Each of web, API and back declares 2 replicas; these are desired counts.

| Resource | Configuration |
| --- | --- |
| Public routes | Traefik TLS: journey.seonology.com → web:8080; journey-api.seonology.com → API:8080. API uses api-cors; WebSocket also uses ws-timeout (inFlightReq 200); fallback UI route uses console-embed. |
| Identity | Client Keycloak sign-in; API receives KEYCLOAK_JWKS_URL, KEYCLOAK_ISSUER and KEYCLOAK_AUDIENCE from the central Deployment. |
| Secrets | External Secrets refreshes Vault AWS/Google Maps/Keycloak entries hourly. Registry credentials from shared/gitea-packages populate gitea-registry-secret used by all three Deployments. |
| Network and telemetry | Default-deny plus DNS, ingress, API→back:9090, monitoring and external HTTPS policies. ServiceMonitor scrapes API:8081 and back:9091; tracing targets the monitoring OTel Collector. |
| Health | Central web/API readiness probes use /healthz; back startup/liveness/readiness use gRPC:9090. API also exposes /readyz. |
| Backups | Central Velero daily-cluster: cron 0 4 * * *, retention 336h; Journey is not excluded. The AWS table creation script enables DynamoDB PITR after creating each table. |

### Runtime configuration

| Component / variable | Default or value | Purpose |
| --- | --- | --- |
| API: HTTP_LISTEN_ADDR / METRICS_LISTEN_ADDR | `:8080` / `:8081` | HTTP / Prometheus |
| API: BACK_GRPC_ADDR | `seonology-journey-back:9090` | gRPC destination |
| API: CORS_ALLOW_ORIGIN | Central value: `https://journey.seonology.com` | Browser origin |
| API: GOOGLE_MAPS_API_KEY / EXTERNAL_API_DAILY_LIMIT | Key / `1000` | Places/Directions; counter resets on UTC date change before cache lookup. |
| back: GRPC_LISTEN_ADDR / OBS_LISTEN_ADDR | `:9090` / `:9091` | gRPC / health and metrics |
| back: AWS_REGION / DYNAMODB_ENDPOINT | `ap-northeast-1` / optional URL | AWS client region / local endpoint |
| back: MEDIA_PRESIGN_BASE_URL | `https://journey-media.seonology.local` | Stub URL base |
| back: LOG_FORMAT / LOG_LEVEL | Text / info | json selects structured JSON; debug, warn and error levels supported. |
| web: VITE_API_BASE | `https://journey-api.seonology.com` | REST base; client adds /api/v1 |
| web: VITE_KEYCLOAK_URL / VITE_KEYCLOAK_REALM / VITE_KEYCLOAK_CLIENT_ID | `https://auth.seonology.com` / `seonology-journey` / `journey-web` | Build-time sign-in settings |
| web: VITE_MAPBOX_TOKEN | Optional token | Mapbox map components |
| Android: ANDROID_VERSION_NAME / ANDROID_VERSION_CODE | `0.1.0` / `1` | Build version; API and Keycloak endpoints are BuildConfig constants. |

DynamoDB table names use the constant `seonology-journey-` prefix. The back entrypoint reads OBS_LISTEN_ADDR rather than the Deployment’s METRICS_LISTEN_ADDR. DDB_TABLE_PREFIX, S3_MEDIA_BUCKET, AUTH_BACK_GRPC_ADDR and MEMBER_BACK_GRPC_ADDR are present in central manifests but are not read by this entrypoint.

## Repository policy

![Repository policy](assets/diagrams/repository-roles.svg)

- Use Conventional Commits with an explicit scope from `.commitlintrc.json`.
- Keep Protobuf source and generated clients aligned.
- Store credentials in Gitea secrets, Vault or Kubernetes Secrets.

## License

The project uses the [MIT license](LICENSE).
