# Seonology Journey

[English](README.md) | [한국어](README.ko.md) | [日本語](README.ja.md)

Seonology Journey manages travel plans and records in a monorepo with React, Android, a Go REST/WebSocket API, a Go gRPC back service, and shared Protobuf contracts.

## Architecture

![Architecture](assets/diagrams/service-architecture.svg)

Web and Android send REST requests to the API. The API forwards user identity as gRPC metadata to the back service, which stores travel data and media metadata in DynamoDB. Keycloak supplies client sign-in and JWT public keys. The back entrypoint connects media URL generation to `StubPresigner`; its default base is `https://journey-media.seonology.local`, with a 15-minute expiry.

### HTTP API

The routes in the following table are relative to `/api/v1`. Send `Authorization: Bearer <token>` from a Keycloak login. The API applies the Bearer middleware to the REST group and forwards the user ID to back. Protobuf REST adapter responses use camelCase JSON. The separate nearby/transit handlers use encoding/json and retain snake_case fields such as `place_id`, `photo_ref` and `line_name`.

| Group | Methods and paths | Behavior and arguments |
| --- | --- | --- |
| Trips | `GET /trips`; `POST /trips`; `GET /trips/{tripId}`; `PATCH /trips/{tripId}`; `DELETE /trips/{tripId}` | Create with a required title; read, update or delete a trip. GET /trips accepts numeric status, cursor and limit. Dates use YYYY-MM-DD; supplying both dates generates days. |
| Days | `GET /trips/{tripId}/days`; `PATCH /days/{dayId}` | List trip days; update a day’s region, weather and dailySummary. |
| Schedules | `GET /days/{dayId}/schedules`; `POST /days/{dayId}/schedules`; `PATCH /schedules/{scheduleId}`; `DELETE /schedules/{scheduleId}` | List, create, update and delete schedule items. |
| Schedule order | `POST /days/{dayId}/schedules:reorder` | Send scheduleIdsInOrder in the request body. |
| Meals | `GET /days/{dayId}/meals`; `PUT /days/{dayId}/meals`; `DELETE /days/{dayId}/meals/{mealType}` | List or upsert a meal; mealType in the delete path is a numeric enum. |
| Accommodation | `GET /days/{dayId}/accommodation`; `PUT /days/{dayId}/accommodation`; `DELETE /days/{dayId}/accommodation` | Read, upsert or delete the accommodation for a day. |
| Expenses | `GET /trips/{tripId}/expenses`; `POST /trips/{tripId}/expenses`; `PATCH /expenses/{id}`; `DELETE /expenses/{id}`; `GET /trips/{tripId}/expense-summary` | CRUD and a per-trip expense summary. |
| Notes | `GET /trips/{tripId}/notes`; `POST /trips/{tripId}/notes`; `PATCH /notes/{id}`; `DELETE /notes/{id}` | CRUD for trip notes. |
| Checklist | `GET /trips/{tripId}/checklist`; `POST /trips/{tripId}/checklist`; `PATCH /checklist/{id}`; `DELETE /checklist/{id}` | CRUD for checklist items. |
| Reservations | `GET /trips/{tripId}/reservations`; `POST /trips/{tripId}/reservations`; `PATCH /reservations/{id}`; `DELETE /reservations/{id}` | CRUD for reservations. |
| Companions | `GET /trips/{tripId}/companions`; `POST /trips/{tripId}/companions`; `PATCH /trips/{tripId}/companions/{memberId}`; `DELETE /trips/{tripId}/companions/{memberId}` | Manage companions and their roles. |
| Tags | `GET /tags`; `POST /tags`; `DELETE /tags/{id}`; `GET /trips/{tripId}/tags`; `PUT /trips/{tripId}/tags/{tagId}`; `DELETE /trips/{tripId}/tags/{tagId}` | Manage tags and trip/tag associations. |
| Templates | `GET /templates`; `POST /trips/{tripId}:save-as-template`; `POST /templates/{id}:create-trip`; `DELETE /templates/{id}` | List templates, save a trip as a template, create a trip from one, or delete it. |
| Favorites | `GET /favorites`; `POST /favorites`; `DELETE /favorites/{id}` | List, add or remove favorite places. |
| Shares | `POST /shares`; `GET /shares/{code}`; `DELETE /shares/{code}` | Create, read or revoke a share code. These REST routes also use the Bearer middleware. |
| Media URL | `POST /trips/{tripId}/media:upload-url` | Send filename, mimeType and size; receive uploadUrl, mediaId, s3Key and expiresAt. |
| Media confirmation | `POST /trips/{tripId}/media:confirm` | Save metadata using the mediaId and s3Key from URL issuance; dayId, scheduleId and caption are optional. |
| Media | `GET /trips/{tripId}/media`; `GET /media/{id}/url`; `DELETE /media/{id}` | List accepts day_id, cursor and limit. URL lookup accepts thumbnail=true. |
| Statistics | `GET /trips/{tripId}/statistics`; `GET /statistics/yearly` | Trip statistics aggregate day/schedule/meal/region/photo counts and expenses. The yearly endpoint accepts year and only populates the year field. |

For media, request `media:upload-url` before `media:confirm` and carry the returned `mediaId` and `s3Key` into confirmation. The current entrypoint uses the StubPresigner described above. Trip and media lists accept `cursor` and `limit` (1–100).

Set JOURNEY_TOKEN to an access token obtained through Keycloak. The first request creates a trip with the minimum required title; the second lists trips.

```bash
JOURNEY_API_BASE=https://journey-api.seonology.com
curl --fail-with-body -sS -X POST "$JOURNEY_API_BASE/api/v1/trips" \
  -H "Authorization: Bearer $JOURNEY_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"title":"Sample trip"}'
curl --fail-with-body -sS "$JOURNEY_API_BASE/api/v1/trips?limit=20" \
  -H "Authorization: Bearer $JOURNEY_TOKEN"
```

### External and service interfaces

| Interface | Behavior |
| --- | --- |
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
| `apps/android` | Kotlin / Jetpack Compose | APK (debug/release), AAB (release) |
| `proto` | Protobuf contracts and generated clients | Go / TypeScript |
| `deploy` | Standalone Kustomize resources | Production Argo CD source is in central GitOps. |
| `scripts` | AWS setup, local tables and sample data | Shell / Python scripts |

Gitea Android CI runs `test assembleDebug` and produces a debug APK. Separate release builds use `assembleRelease` for a release APK and `bundleRelease` for an AAB.

### Repository map

| Source link | Role |
| --- | --- |
| [apps/web/src/main.tsx](apps/web/src/main.tsx) · [apps/web/src/App.tsx](apps/web/src/App.tsx) · [apps/web/src/pages/](apps/web/src/pages/) | Web entrypoint, routing and pages |
| [apps/api/cmd/server/main.go](apps/api/cmd/server/main.go) | API routes, middleware and service wiring |
| [apps/api/internal/handler/handlers.go](apps/api/internal/handler/handlers.go) | REST → Protobuf/gRPC adapter |
| [apps/api/internal/external/handler.go](apps/api/internal/external/handler.go) · [apps/api/internal/external/service.go](apps/api/internal/external/service.go) · [apps/api/internal/ws/hub.go](apps/api/internal/ws/hub.go) | External JSON handlers and WebSocket hub |
| [apps/back/cmd/server/main.go](apps/back/cmd/server/main.go) · [apps/back/internal/server/](apps/back/internal/server/) | Back entrypoint and JourneyService RPCs |
| [apps/back/internal/repository/ddb/client.go](apps/back/internal/repository/ddb/client.go) · [apps/back/internal/media/service.go](apps/back/internal/media/service.go) | DynamoDB client and media metadata/URL service |
| [apps/android/app/src/main/java/com/seonology/journey/MainActivity.kt](apps/android/app/src/main/java/com/seonology/journey/MainActivity.kt) · [apps/android/app/src/main/java/com/seonology/journey/data/JourneyApi.kt](apps/android/app/src/main/java/com/seonology/journey/data/JourneyApi.kt) | Android entrypoint and REST interface |
| [proto/journey/v1/](proto/journey/v1/) · [proto/buf.gen.yaml](proto/buf.gen.yaml) · [proto/gen/](proto/gen/) | Contracts, generator configuration and generated clients |
| [deploy/overlays/production/kustomization.yaml](deploy/overlays/production/kustomization.yaml) · [Makefile](Makefile) | Standalone manifest rendering via make deploy-render |
| [.gitea/workflows/ci.yml](.gitea/workflows/ci.yml) · [.gitea/workflows/images.yml](.gitea/workflows/images.yml) · [.gitea/workflows/gitea-android-ci.yml](.gitea/workflows/gitea-android-ci.yml) · [.gitea/workflows/gitea-release.yml](.gitea/workflows/gitea-release.yml) | Repository CI, image publication, Android CI and releases |
| [apps/api/.releaserc.json](apps/api/.releaserc.json) · [apps/back/.releaserc.json](apps/back/.releaserc.json) · [apps/web/.releaserc.json](apps/web/.releaserc.json) · [apps/android/.releaserc.json](apps/android/.releaserc.json) | Component tag formats and release rules |
| [tools/generate_phase_b_svgs.py](tools/generate_phase_b_svgs.py) | Deterministic README SVG generator |
| [tests/test_repository_contract.py](tests/test_repository_contract.py) · [verify.py](verify.py) · [README_STRUCTURE.md](README_STRUCTURE.md) | Repository checks, component checks and README layout contract |

## Requirements

- Node.js >=20.18.0 and pnpm 9.15.9; Gitea web CI uses Node 22 and the web Dockerfile uses Node 20.
- Go >=1.25.0; Gitea CI uses golang:1.25.14-bookworm.
- JDK 21 and Android SDK 35 for Android; minimum device API 26 and Gradle wrapper 8.10.2.
- Docker, QEMU and Buildx for multi-architecture images; Buf for Protobuf generation.
- kubectl with its built-in Kustomize support for local manifest rendering.

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

`make deploy-render` runs `kubectl kustomize deploy/overlays/production` to render the standalone manifests locally. Production Argo CD reads the central GitOps path described under Operations.

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

On main/manual runs, the existing component tag supplies only the version string. Checkout keeps the run ref’s source; the workflow does not check out that version tag. It builds and pushes on every selected iteration without skipping an existing image, so an existing `X.Y.Z` image tag can be published again from different source, alongside `sha-<7>` and `latest`.

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

### Deployment checks

Check for Application `Synced` and `Healthy`, completed rollouts and the declared two ready replicas per Deployment. Compare Deployment image references with the central overlay and running Pod imageIDs with the corresponding platform digest in each OCI index. Review component logs for failures.

```bash
kubectl -n argocd get application seonology-journey-monorepo
kubectl -n argocd get application seonology-journey-monorepo \
  -o jsonpath='{.status.sync.status}{" "}{.status.health.status}{"\n"}'
kubectl -n seonology-journey get deployments,pods,services
for component in web api back; do
  kubectl -n seonology-journey rollout status "deployment/seonology-journey-$component" --timeout=180s
  kubectl -n seonology-journey logs "deployment/seonology-journey-$component" -c "$component" --tail=50
done
kubectl -n seonology-journey get deployments \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .spec.template.spec.containers[*]}{.image}{"\n"}{end}{end}'
kubectl -n seonology-journey get pods \
  -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{range .status.containerStatuses[*]}{.name}{"\t"}{.imageID}{"\n"}{end}{end}'
```

Run each port-forward below in a separate terminal. Run the following curl commands in another terminal to check internal service paths and public routes. Expect HTTP 200; API `/readyz` also depends on the back RPC. Back’s HTTP health endpoint on 9091 complements its declared gRPC probes on 9090.

```bash
kubectl -n seonology-journey port-forward service/seonology-journey-api 18080:8080
kubectl -n seonology-journey port-forward service/seonology-journey-web 18081:8080
kubectl -n seonology-journey port-forward service/seonology-journey-back 19091:9091
```

```bash
curl --fail-with-body -sS http://127.0.0.1:18080/healthz
curl --fail-with-body -sS http://127.0.0.1:18080/readyz
curl --fail-with-body -sS http://127.0.0.1:18081/healthz
curl --fail-with-body -sS http://127.0.0.1:19091/healthz
curl --fail-with-body -sS https://journey.seonology.com/healthz
curl --fail-with-body -sS https://journey-api.seonology.com/healthz
curl --fail-with-body -sS https://journey-api.seonology.com/readyz
```

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
- Do not add automated-author signatures or emoji to project artifacts. See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

The project uses the [MIT license](LICENSE).
