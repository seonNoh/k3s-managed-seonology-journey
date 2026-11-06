# Seonology Journey

[English](README.md) | [한국어](README.ko.md) | [日本語](README.ja.md)

Seonology Journey는 여행 계획과 기록을 관리하는 모노레포입니다. React, Android, Go REST·WebSocket API, Go gRPC back 서비스와 공통 Protobuf 계약을 함께 관리합니다.

## 아키텍처

![아키텍처](assets/diagrams/service-architecture.ko.svg)

웹과 Android는 API에 REST 요청을 보냅니다. API는 사용자 식별자를 gRPC 메타데이터로 back에 전달하며, back은 여행 데이터와 미디어 메타데이터를 DynamoDB에 저장합니다. Keycloak은 클라이언트 로그인과 JWT 공개 키를 제공합니다. back의 시작 코드는 미디어 URL 생성에 `StubPresigner`를 연결합니다. 기본 주소는 `https://journey-media.seonology.local`이고 유효 기간은 15분입니다.

| 인터페이스 | 동작 |
| --- | --- |
| `/api/v1` | 여행, 날짜, 일정, 식사, 숙소, 지출, 메모, 체크리스트, 예약, 동행자, 태그, 템플릿, 즐겨찾기, 공유, 미디어와 통계를 처리합니다. REST JSON은 Protobuf 필드명을 camelCase로 사용합니다. |
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
| `apps/android` | Kotlin / Jetpack Compose | Android 애플리케이션 |
| `proto` | Protobuf 계약과 생성 클라이언트 | Go / TypeScript |
| `deploy` | 독립 Kustomize 리소스 | 운영 Argo CD 소스는 중앙 GitOps에 있습니다. |
| `scripts` | AWS 설정, 로컬 테이블과 예제 데이터 | 셸 / Python 스크립트 |

## 사전 요구 사항

- Node.js 20.18.0 이상과 pnpm 9.15.9를 사용합니다. Gitea 웹 CI는 Node 22, 웹 Dockerfile은 Node 20을 사용합니다.
- Go 1.25.0 이상을 사용합니다. Gitea CI는 golang:1.25.14-bookworm을 사용합니다.
- Android에는 JDK 21과 Android SDK 35가 필요합니다. 최소 기기 API는 26이고 Gradle wrapper는 8.10.2입니다.
- 다중 아키텍처 이미지에는 Docker, QEMU와 Buildx를 사용합니다. Protobuf 생성에는 Buf를 사용합니다.

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

## 라이선스

[MIT 라이선스](LICENSE)를 사용합니다.
