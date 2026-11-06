# Seonology Journey

[English](README.md) | [한국어](README.ko.md) | [日本語](README.ja.md)

Seonology Journey는 여행 계획과 기록을 관리하는 모노레포입니다. React, Android, Go REST·WebSocket API, Go gRPC back 서비스와 공통 Protobuf 계약을 함께 관리합니다.

## 아키텍처

![아키텍처](assets/diagrams/service-architecture.ko.svg)

웹과 Android는 API에 REST 요청을 보냅니다. API는 사용자 식별자를 gRPC 메타데이터로 back에 전달하며, back은 여행 데이터와 미디어 메타데이터를 DynamoDB에 저장합니다. Keycloak은 클라이언트 로그인과 JWT 공개 키를 제공합니다. back의 시작 코드는 미디어 URL 생성에 `StubPresigner`를 연결합니다. 기본 주소는 `https://journey-media.seonology.local`이고 유효 기간은 15분입니다.

### HTTP API

다음 표의 경로는 `/api/v1` 기준입니다. Keycloak으로 로그인해 받은 토큰을 `Authorization: Bearer <token>`으로 보냅니다. API는 REST 그룹에 Bearer 미들웨어를 적용하고 사용자 ID를 back에 전달합니다. Protobuf REST 어댑터의 응답은 camelCase JSON을 사용합니다. 별도 nearby·transit 핸들러는 encoding/json을 사용하며 `place_id`, `photo_ref`, `line_name`처럼 snake_case 필드명을 유지합니다.

| 기능군 | 메서드와 경로 | 동작과 인수 |
| --- | --- | --- |
| 여행 | `GET /trips`; `POST /trips`; `GET /trips/{tripId}`; `PATCH /trips/{tripId}`; `DELETE /trips/{tripId}` | 필수 title로 생성하고 여행을 조회·수정·삭제합니다. GET /trips는 숫자 status, cursor, limit을 받습니다. 날짜는 YYYY-MM-DD이며 시작·종료 날짜를 모두 보내면 날짜별 항목을 생성합니다. |
| 날짜 | `GET /trips/{tripId}/days`; `PATCH /days/{dayId}` | 여행의 날짜 목록을 조회하고 region, weather, dailySummary를 수정합니다. |
| 일정 | `GET /days/{dayId}/schedules`; `POST /days/{dayId}/schedules`; `PATCH /schedules/{scheduleId}`; `DELETE /schedules/{scheduleId}` | 일정 항목을 조회·생성·수정·삭제합니다. |
| 일정 순서 | `POST /days/{dayId}/schedules:reorder` | 요청 본문에 scheduleIdsInOrder를 보냅니다. |
| 식사 | `GET /days/{dayId}/meals`; `PUT /days/{dayId}/meals`; `DELETE /days/{dayId}/meals/{mealType}` | 목록을 조회하거나 식사를 저장합니다. 삭제 경로의 mealType은 숫자 열거형입니다. |
| 숙소 | `GET /days/{dayId}/accommodation`; `PUT /days/{dayId}/accommodation`; `DELETE /days/{dayId}/accommodation` | 날짜별 숙소를 조회·저장·삭제합니다. |
| 지출 | `GET /trips/{tripId}/expenses`; `POST /trips/{tripId}/expenses`; `PATCH /expenses/{id}`; `DELETE /expenses/{id}`; `GET /trips/{tripId}/expense-summary` | 지출을 조회·생성·수정·삭제하고 여행별 지출 합계를 조회합니다. |
| 메모 | `GET /trips/{tripId}/notes`; `POST /trips/{tripId}/notes`; `PATCH /notes/{id}`; `DELETE /notes/{id}` | 여행 메모를 조회·생성·수정·삭제합니다. |
| 체크리스트 | `GET /trips/{tripId}/checklist`; `POST /trips/{tripId}/checklist`; `PATCH /checklist/{id}`; `DELETE /checklist/{id}` | 체크리스트 항목을 조회·생성·수정·삭제합니다. |
| 예약 | `GET /trips/{tripId}/reservations`; `POST /trips/{tripId}/reservations`; `PATCH /reservations/{id}`; `DELETE /reservations/{id}` | 예약을 조회·생성·수정·삭제합니다. |
| 동행자 | `GET /trips/{tripId}/companions`; `POST /trips/{tripId}/companions`; `PATCH /trips/{tripId}/companions/{memberId}`; `DELETE /trips/{tripId}/companions/{memberId}` | 동행자와 역할을 관리합니다. |
| 태그 | `GET /tags`; `POST /tags`; `DELETE /tags/{id}`; `GET /trips/{tripId}/tags`; `PUT /trips/{tripId}/tags/{tagId}`; `DELETE /trips/{tripId}/tags/{tagId}` | 태그와 여행별 연결을 관리합니다. |
| 템플릿 | `GET /templates`; `POST /trips/{tripId}:save-as-template`; `POST /templates/{id}:create-trip`; `DELETE /templates/{id}` | 목록 조회, 여행의 템플릿 저장, 템플릿에서 여행 생성과 삭제를 처리합니다. |
| 즐겨찾기 | `GET /favorites`; `POST /favorites`; `DELETE /favorites/{id}` | 장소를 조회·추가·삭제합니다. |
| 공유 | `POST /shares`; `GET /shares/{code}`; `DELETE /shares/{code}` | 공유 코드를 생성·조회·폐기합니다. 이 REST 경로에도 Bearer 미들웨어를 적용합니다. |
| 미디어 URL | `POST /trips/{tripId}/media:upload-url` | filename, mimeType, size를 보내면 uploadUrl, mediaId, s3Key, expiresAt을 발급합니다. |
| 미디어 확정 | `POST /trips/{tripId}/media:confirm` | 발급받은 mediaId와 s3Key로 메타데이터를 저장합니다. dayId, scheduleId, caption은 선택 항목입니다. |
| 미디어 | `GET /trips/{tripId}/media`; `GET /media/{id}/url`; `DELETE /media/{id}` | 목록은 day_id, cursor, limit을 받습니다. URL 조회에는 thumbnail=true를 사용할 수 있습니다. |
| 통계 | `GET /trips/{tripId}/statistics`; `GET /statistics/yearly` | 여행 통계는 날짜·일정·식사·지역·사진 수와 지출을 집계합니다. 연간 통계는 year를 받으며 연도 필드만 채웁니다. |

미디어는 `media:upload-url`을 호출한 뒤 `media:confirm`을 호출하며, 발급받은 `mediaId`와 `s3Key`를 확정 요청에 넣습니다. 현재 시작 코드는 앞서 설명한 StubPresigner를 사용합니다. 여행·미디어 목록은 `cursor`와 `limit`(1~100)을 받습니다.

Keycloak에서 받은 액세스 토큰을 JOURNEY_TOKEN에 설정합니다. 첫 번째 요청은 필수 title만으로 여행을 만들고 두 번째 요청은 목록을 조회합니다.

```bash
JOURNEY_API_BASE=https://journey-api.seonology.com
curl --fail-with-body -sS -X POST "$JOURNEY_API_BASE/api/v1/trips" \
  -H "Authorization: Bearer $JOURNEY_TOKEN" \
  -H 'Content-Type: application/json' \
  --data '{"title":"Sample trip"}'
curl --fail-with-body -sS "$JOURNEY_API_BASE/api/v1/trips?limit=20" \
  -H "Authorization: Bearer $JOURNEY_TOKEN"
```

### 외부·서비스 인터페이스

| 인터페이스 | 동작 |
| --- | --- |
| `GET /api/v1/external/geocode?q=...` | back을 통해 OpenStreetMap Nominatim을 호출합니다. |
| `GET /api/v1/nearby`, `GET /api/v1/transit` | API가 Google Places·Directions를 호출합니다. 응답 캐시와 일일 카운터는 프로세스별 메모리에 있습니다. |
| `GET /api/v1/external/exchange-rate` | 고정 환율을 반환하며, 지정되지 않은 통화 쌍은 1을 반환합니다. |
| `GET /api/v1/external/weather` | gRPC Unimplemented를 반환하며, HTTP 501로 변환합니다. |
| `GET /ws/trips/{tripId}` | 서버 WebSocket 경로입니다. ping/pong과 location_update/location 메시지 형식을 처리합니다. |
| `GET /healthz`, `GET /readyz` | API 생존 상태를 반환합니다. 준비 상태 확인은 2초 제한으로 back의 GetExchangeRate를 호출합니다. |
| `POST /internal/publish` | X-Internal-Token이 API_INTERNAL_TOKEN과 일치해야 합니다. 해당 API 인스턴스의 여행 허브에 방송합니다. back의 PublishEvent RPC는 빈 응답을 반환합니다. |

## 컴포넌트

![컴포넌트](assets/diagrams/component-delivery.ko.svg)

| 경로 | 역할 | 산출물 |
| --- | --- | --- |
| `apps/web` | React 18 / Vite 5 | `seonology-journey-web` |
| `apps/api` | REST / WebSocket API | `seonology-journey-api` |
| `apps/back` | gRPC / DynamoDB 서비스 | `seonology-journey-back` |
| `apps/android` | Kotlin / Jetpack Compose | APK(debug/release), AAB(release) |
| `proto` | Protobuf 계약과 생성 클라이언트 | Go / TypeScript |
| `deploy` | 독립 Kustomize 리소스 | 운영 Argo CD 소스는 중앙 GitOps에 있습니다. |
| `scripts` | AWS 설정, 로컬 테이블과 예제 데이터 | 셸 / Python 스크립트 |

Gitea Android CI는 `test assembleDebug`를 실행해 debug APK를 만듭니다. 별도 release 빌드에서 `assembleRelease`는 release APK를, `bundleRelease`는 AAB를 만듭니다.

### 저장소 지도

| 소스 링크 | 역할 |
| --- | --- |
| [apps/web/src/main.tsx](apps/web/src/main.tsx) · [apps/web/src/App.tsx](apps/web/src/App.tsx) · [apps/web/src/pages/](apps/web/src/pages/) | 웹 진입점·라우팅·페이지 |
| [apps/api/cmd/server/main.go](apps/api/cmd/server/main.go) | API 라우트·미들웨어·서비스 연결 |
| [apps/api/internal/handler/handlers.go](apps/api/internal/handler/handlers.go) | REST → Protobuf/gRPC 어댑터 |
| [apps/api/internal/external/handler.go](apps/api/internal/external/handler.go) · [apps/api/internal/external/service.go](apps/api/internal/external/service.go) · [apps/api/internal/ws/hub.go](apps/api/internal/ws/hub.go) | 외부 JSON 핸들러와 WebSocket 허브 |
| [apps/back/cmd/server/main.go](apps/back/cmd/server/main.go) · [apps/back/internal/server/](apps/back/internal/server/) | back 진입점과 JourneyService RPC |
| [apps/back/internal/repository/ddb/client.go](apps/back/internal/repository/ddb/client.go) · [apps/back/internal/media/service.go](apps/back/internal/media/service.go) | DynamoDB 클라이언트와 미디어 메타데이터·URL 서비스 |
| [apps/android/app/src/main/java/com/seonology/journey/MainActivity.kt](apps/android/app/src/main/java/com/seonology/journey/MainActivity.kt) · [apps/android/app/src/main/java/com/seonology/journey/data/JourneyApi.kt](apps/android/app/src/main/java/com/seonology/journey/data/JourneyApi.kt) | Android 진입점과 REST 인터페이스 |
| [proto/journey/v1/](proto/journey/v1/) · [proto/buf.gen.yaml](proto/buf.gen.yaml) · [proto/gen/](proto/gen/) | 계약·생성 설정·생성 클라이언트 |
| [deploy/overlays/production/kustomization.yaml](deploy/overlays/production/kustomization.yaml) · [Makefile](Makefile) | make deploy-render를 통한 독립 매니페스트 렌더 |
| [.gitea/workflows/ci.yml](.gitea/workflows/ci.yml) · [.gitea/workflows/images.yml](.gitea/workflows/images.yml) · [.gitea/workflows/gitea-android-ci.yml](.gitea/workflows/gitea-android-ci.yml) · [.gitea/workflows/gitea-release.yml](.gitea/workflows/gitea-release.yml) | 저장소 CI·이미지 게시·Android CI·릴리스 |
| [apps/api/.releaserc.json](apps/api/.releaserc.json) · [apps/back/.releaserc.json](apps/back/.releaserc.json) · [apps/web/.releaserc.json](apps/web/.releaserc.json) · [apps/android/.releaserc.json](apps/android/.releaserc.json) | 컴포넌트 태그 형식과 릴리스 규칙 |
| [tools/generate_phase_b_svgs.py](tools/generate_phase_b_svgs.py) | README SVG 생성기 |
| [tests/test_repository_contract.py](tests/test_repository_contract.py) · [verify.py](verify.py) · [README_STRUCTURE.md](README_STRUCTURE.md) | 저장소 검사·컴포넌트 검사·README 구조 계약 |

## 사전 요구 사항

- Node.js 20.18.0 이상과 pnpm 9.15.9를 사용합니다. Gitea 웹 CI는 Node 22, 웹 Dockerfile은 Node 20을 사용합니다.
- Go 1.25.0 이상을 사용합니다. Gitea CI는 golang:1.25.14-bookworm을 사용합니다.
- Android에는 JDK 21과 Android SDK 35가 필요합니다. 최소 기기 API는 26이고 Gradle wrapper는 8.10.2입니다.
- 다중 아키텍처 이미지에는 Docker, QEMU와 Buildx를 사용합니다. Protobuf 생성에는 Buf를 사용합니다.
- 로컬 매니페스트 렌더에는 Kustomize 기능이 내장된 kubectl을 사용합니다.

## 빠른 시작

웹 개발 서버는 5173 포트를 사용합니다. 다른 서비스에 연결하려면 Vite 시작 전에 VITE_API_BASE와 Keycloak 빌드 변수를 설정합니다.

```bash
corepack enable
corepack prepare pnpm@9.15.9 --activate
pnpm install --frozen-lockfile
pnpm --filter @seonology/journey-web dev
```

아래 Go 명령은 저장소 루트에서 각각 별도 터미널로 실행합니다. Go 프로세스를 로컬에서 실행하려면 AWS 자격증명과 DynamoDB 테이블 또는 DYNAMODB_ENDPOINT, Keycloak 설정, 필요한 외부 API 키를 준비합니다. API와 back의 포트는 각각 8080과 9090이며, 지표 포트는 8081과 9091입니다.

```bash
BACK_GRPC_ADDR=localhost:9090 go -C apps/api run ./cmd/server
go -C apps/back run ./cmd/server
```

Compose는 DynamoDB Local(8000)과 관리 UI(8001)만 제공합니다. 로컬 데이터는 메모리에 저장하며 애플리케이션 서비스는 실행하지 않습니다. `make proto`는 `proto/`에서 `buf generate`를 실행합니다.

`make deploy-render`는 `kubectl kustomize deploy/overlays/production`으로 독립 매니페스트를 로컬에서 렌더합니다. 운영 Argo CD는 운영 절에 적힌 중앙 GitOps 경로를 읽습니다.

## 확인 절차

```bash
python3 verify.py --skip-components
python3 verify.py
```

첫 번째 명령은 문서, 생성 그림, 저장소 규칙과 워크플로 파일을 확인합니다. 두 번째 명령은 Go vet·경쟁 상태 테스트·빌드와 웹 타입 검사·테스트·빌드도 실행합니다. Android는 별도 워크플로에서 처리합니다.

## 배포

Gitea가 기준 저장소입니다. push mirror는 `sync_on_commit: true`로 브랜치와 태그를 GitHub의 `seonNoh/k3s-managed-seonology-journey`에 복사합니다. push에는 Gitea의 `origin` 원격을 사용합니다.

| 워크플로 / 잡 | 시작 조건 | 단계와 조건 |
| --- | --- | --- |
| `ci.yml / verify` | main push, main PR, 수동 실행 | Checkout → Repository contract → Go services → Web test and build 순서입니다. |
| `images.yml / publish` | main push, api-v*·back-v*·web-v* 태그, 수동 실행 | Checkout → QEMU → Buildx → Registry 로그인 → 직렬 빌드·게시·index 확인 순서입니다. ci.yml과 의존 관계가 없습니다. |
| `gitea-android-ci.yml / android` | apps/android/** 또는 해당 워크플로를 바꾸는 main PR, 수동 실행 | Checkout → Test and assemble debug application 순서입니다. linux/amd64의 android-sdk:35를 사용합니다. |
| `gitea-release.yml / create-release` | api-v*·back-v*·web-v*·android-v* 태그 push | Create Gitea release를 실행합니다. component-vX.Y.Z 형식을 요구하며, 기존 릴리스는 그대로 둡니다. |

images 잡은 API → back → web 순서로 처리합니다. 컴포넌트 태그에서는 해당 컴포넌트만 선택합니다. main·수동 실행에서는 버전순으로 가장 높은 기존 컴포넌트 태그를 사용하므로 선택된 각 컴포넌트에 태그가 필요합니다. `git.seonology.com/seonology/seonology-journey-{api,back,web}`의 각 이미지는 `X.Y.Z`, `sha-<7>`, `latest` 태그를 받습니다. 각 index에는 `linux/amd64`와 `linux/arm64`가 포함됩니다. Registry 로그인에는 PACKAGE_USER·PACKAGE_TOKEN을, 릴리스 게시에는 GITEA_TOKEN을 사용합니다.

main·수동 실행에서 기존 컴포넌트 태그는 버전 문자열만 정합니다. Checkout은 실행 ref의 소스를 사용하며 해당 버전 태그를 체크아웃하지 않습니다. 기존 이미지가 있어도 생략하지 않고 선택된 각 이미지를 빌드·게시하므로, 같은 `X.Y.Z` 이미지 태그가 다른 소스로 다시 게시될 수 있습니다. `sha-<7>`과 `latest`도 함께 게시합니다.

`apps/*/.releaserc.json`은 `api-vX.Y.Z`, `back-vX.Y.Z`, `web-vX.Y.Z`, `android-vX.Y.Z`를 정의합니다. 각 컴포넌트 scope와 `all`의 명시 규칙은 feat를 minor, fix·perf·refactor를 patch, breaking change를 major에 대응시킵니다. Gitea 워크플로는 기존 태그를 게시하며 semantic-release를 호출하는 단계가 없습니다.

```bash
git push origin main
git push origin api-vX.Y.Z
```

## 운영

![운영](assets/diagrams/runtime-cutover.ko.svg)

Argo CD Application `seonology-journey-monorepo`는 `seonology/seonology-k3s`의 `workloads/seonology-journey/overlays/production`을 읽어 `seonology-journey` 네임스페이스에 적용합니다. Image Updater는 Gitea의 각 `latest` digest를 추적하고 `main`의 Kustomization에 기록합니다. Argo CD는 자동 prune·self-heal을 사용합니다. 오버레이는 이미지 digest를 고정합니다. web, API, back의 선언된 복제본 수는 각각 2개입니다.

| 리소스 | 설정 |
| --- | --- |
| 공개 경로 | Traefik TLS는 journey.seonology.com을 web:8080에, journey-api.seonology.com을 API:8080에 연결합니다. API는 api-cors를, WebSocket은 ws-timeout(inFlightReq 200)도 사용합니다. 나머지 UI 경로는 console-embed를 사용합니다. |
| 인증 | 클라이언트는 Keycloak으로 로그인합니다. API는 중앙 Deployment에서 KEYCLOAK_JWKS_URL, KEYCLOAK_ISSUER, KEYCLOAK_AUDIENCE를 받습니다. |
| 시크릿 | External Secrets는 Vault의 AWS·Google Maps·Keycloak 항목을 매시간 동기화합니다. shared/gitea-packages의 인증 정보는 세 Deployment가 사용하는 gitea-registry-secret에 저장됩니다. |
| 네트워크와 관측 | 기본 거부 정책에 DNS, 인입, API→back:9090, 모니터링과 외부 HTTPS 허용 정책을 더합니다. ServiceMonitor는 API:8081과 back:9091을 수집하며, 추적은 monitoring의 OTel Collector로 전송합니다. |
| 상태 확인 | 중앙 web·API 준비 상태 probe는 /healthz를 사용합니다. back의 시작·생존·준비 probe는 gRPC:9090을 사용합니다. API는 /readyz도 제공합니다. |
| 백업 | 중앙 Velero daily-cluster의 cron은 0 4 * * *이며 보존 기간은 336시간입니다. Journey는 제외 목록에 없습니다. AWS 테이블 생성 스크립트는 새 테이블마다 DynamoDB PITR을 활성화합니다. |

### 배포 점검

Application의 `Synced`·`Healthy` 상태, rollout 완료와 Deployment별 선언된 준비 복제본 2개를 확인합니다. Deployment 이미지 참조를 중앙 오버레이와 대조하고 Pod의 imageID는 각 OCI index에서 해당 플랫폼의 digest와 대조합니다. 컴포넌트 로그에서 오류를 확인합니다.

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

아래 port-forward 명령은 각각 별도 터미널에서 실행합니다. 다음 curl 명령은 다른 터미널에서 실행해 내부 서비스 경로와 공개 경로를 확인합니다. 기대 응답은 HTTP 200이며 API의 `/readyz`는 back RPC에도 의존합니다. back의 9091 HTTP 상태 경로는 매니페스트의 9090 gRPC probe와 별개로 제공합니다.

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

### 런타임 설정

| 컴포넌트 / 변수 | 기본값 또는 설정값 | 용도 |
| --- | --- | --- |
| API: HTTP_LISTEN_ADDR / METRICS_LISTEN_ADDR | `:8080` / `:8081` | HTTP / Prometheus |
| API: BACK_GRPC_ADDR | `seonology-journey-back:9090` | gRPC 연결 대상 |
| API: CORS_ALLOW_ORIGIN | 중앙 설정: `https://journey.seonology.com` | 브라우저 출처 |
| API: GOOGLE_MAPS_API_KEY / EXTERNAL_API_DAILY_LIMIT | 키 / `1000` | Places·Directions용입니다. UTC 날짜 변경 시 카운터를 초기화하며 캐시 조회 전에 계산합니다. |
| back: GRPC_LISTEN_ADDR / OBS_LISTEN_ADDR | `:9090` / `:9091` | gRPC / 상태와 지표 |
| back: AWS_REGION / DYNAMODB_ENDPOINT | `ap-northeast-1` / 선택 URL | AWS 리전 / 로컬 연결 주소 |
| back: MEDIA_PRESIGN_BASE_URL | `https://journey-media.seonology.local` | Stub URL 기준 주소 |
| back: LOG_FORMAT / LOG_LEVEL | 텍스트 / info | json이면 JSON을 출력하며 debug, warn, error 수준도 지원합니다. |
| web: VITE_API_BASE | `https://journey-api.seonology.com` | 클라이언트가 /api/v1을 덧붙입니다. |
| web: VITE_KEYCLOAK_URL / VITE_KEYCLOAK_REALM / VITE_KEYCLOAK_CLIENT_ID | `https://auth.seonology.com` / `seonology-journey` / `journey-web` | 빌드 시 로그인 설정 |
| web: VITE_MAPBOX_TOKEN | 선택 토큰 | Mapbox 지도 컴포넌트 |
| Android: ANDROID_VERSION_NAME / ANDROID_VERSION_CODE | `0.1.0` / `1` | 빌드 버전입니다. API와 Keycloak 주소는 BuildConfig 상수입니다. |

DynamoDB 테이블 접두사는 상수 `seonology-journey-`입니다. back의 시작 코드는 Deployment의 METRICS_LISTEN_ADDR 대신 OBS_LISTEN_ADDR를 읽습니다. 중앙 매니페스트에는 DDB_TABLE_PREFIX, S3_MEDIA_BUCKET, AUTH_BACK_GRPC_ADDR, MEMBER_BACK_GRPC_ADDR가 있지만 이 시작 코드는 해당 변수를 읽지 않습니다.

## 저장소 정책

![저장소 정책](assets/diagrams/repository-roles.ko.svg)

- `.commitlintrc.json`에 있는 명시적인 scope로 Conventional Commits를 작성합니다.
- Protobuf 정의와 생성 클라이언트를 일치시킵니다.
- 자격증명은 Gitea secrets, Vault 또는 Kubernetes Secrets에 저장합니다.
- 프로젝트 산출물에 자동 작성자 서명이나 이모지를 추가하지 않습니다. [CONTRIBUTING.md](CONTRIBUTING.md)의 기여 규칙을 따릅니다.

## 라이선스

[MIT 라이선스](LICENSE)를 사용합니다.
