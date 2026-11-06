# Seonology Journey

[English](README.md) | [한국어](README.ko.md) | [日本語](README.ja.md)

Seonology Journey は旅行計画と記録を管理するモノレポです。React、Android、Go の REST・WebSocket API、Go の gRPC back サービス、共通の Protobuf 契約をまとめて管理します。

## アーキテクチャ

![アーキテクチャ](assets/diagrams/service-architecture.ja.svg)

Web と Android は API に REST リクエストを送ります。API はユーザー識別子を gRPC メタデータとして back に渡します。back は旅行データとメディアのメタデータを DynamoDB に保存します。Keycloak はクライアントのログインと JWT 公開鍵を提供します。back の起動コードはメディア URL の生成に `StubPresigner`を接続します。既定の URL は `https://journey-media.seonology.local`で、有効期間は 15 分です。

| インターフェース | 動作 |
| --- | --- |
| `/api/v1` | 旅行、日付、日程、食事、宿泊、支出、メモ、チェックリスト、予約、同行者、タグ、テンプレート、お気に入り、共有、メディア、統計を扱います。REST JSON は Protobuf のフィールド名を camelCase で使用します。 |
| `GET /api/v1/external/geocode?q=...` | back 経由で OpenStreetMap Nominatim を呼び出します。 |
| `GET /api/v1/nearby`, `GET /api/v1/transit` | API が Google Places・Directions を呼び出します。レスポンスキャッシュと日次カウンターはプロセスごとのメモリにあります。 |
| `GET /api/v1/external/exchange-rate` | 固定レートを返します。未定義の通貨ペアは 1 を返します。 |
| `GET /api/v1/external/weather` | gRPC Unimplemented を返し、HTTP 501 に変換します。 |
| `GET /ws/trips/{tripId}` | サーバー側の WebSocket パスです。ping/pong と location_update/location のメッセージ形式を処理します。 |
| `GET /healthz`, `GET /readyz` | API の生存状態を返します。準備状態の確認では、2 秒の制限で back の GetExchangeRate を呼び出します。 |
| `POST /internal/publish` | X-Internal-Token と API_INTERNAL_TOKEN の一致が必要です。その API インスタンスの旅行ハブに配信します。back の PublishEvent RPC は空のレスポンスを返します。 |

## コンポーネント

![コンポーネント](assets/diagrams/component-delivery.ja.svg)

| パス | 役割 | 成果物 |
| --- | --- | --- |
| `apps/web` | React 18 / Vite 5 | `seonology-journey-web` |
| `apps/api` | REST / WebSocket API | `seonology-journey-api` |
| `apps/back` | gRPC / DynamoDB サービス | `seonology-journey-back` |
| `apps/android` | Kotlin / Jetpack Compose | Android アプリケーション |
| `proto` | Protobuf 契約と生成クライアント | Go / TypeScript |
| `deploy` | 独立した Kustomize リソース | 本番 Argo CD のソースは中央 GitOps にあります。 |
| `scripts` | AWS 設定、ローカルテーブル、サンプルデータ | シェル / Python スクリプト |

## 必要環境

- Node.js 20.18.0 以上と pnpm 9.15.9 を使用します。Gitea の Web CI は Node 22、Web Dockerfile は Node 20 を使用します。
- Go 1.25.0 以上を使用します。Gitea CI は golang:1.25.14-bookworm を使用します。
- Android には JDK 21 と Android SDK 35 が必要です。端末の最小 API は 26、Gradle wrapper は 8.10.2 です。
- マルチアーキテクチャイメージには Docker、QEMU、Buildx を使用します。Protobuf の生成には Buf を使用します。

## クイックスタート

Web 開発サーバーのポートは 5173 です。接続先を変える場合は、Vite の起動前に VITE_API_BASE と Keycloak のビルド変数を設定します。

```bash
corepack enable
corepack prepare pnpm@9.15.9 --activate
pnpm install --frozen-lockfile
pnpm --filter @seonology/journey-web dev
```

以下の Go コマンドはリポジトリのルートから別々のターミナルで実行します。Go プロセスをローカルで起動する前に、AWS 認証情報、DynamoDB テーブルまたは DYNAMODB_ENDPOINT、Keycloak 設定、必要な外部 API キーを用意します。API と back のポートは 8080 と 9090、メトリクスポートは 8081 と 9091 です。

```bash
BACK_GRPC_ADDR=localhost:9090 go -C apps/api run ./cmd/server
go -C apps/back run ./cmd/server
```

Compose は DynamoDB Local（8000）と管理 UI（8001）だけを提供します。データはメモリに保持し、アプリケーションサービスは起動しません。`make proto`は `proto/`で `buf generate`を実行します。

## 確認手順

```bash
python3 verify.py --skip-components
python3 verify.py
```

最初のコマンドは文書、生成図、リポジトリ規則、ワークフローファイルを確認します。2 番目は Go vet・race テスト・ビルドと Web の型チェック・テスト・ビルドも実行します。Android は専用のワークフローで扱います。

## 配布

Gitea が基準リポジトリです。push mirror は `sync_on_commit: true`で、ブランチとタグを GitHub の `seonNoh/k3s-managed-seonology-journey`にコピーします。push には Gitea の `origin`を使用します。

| ワークフロー / ジョブ | 起動条件 | ステップと条件 |
| --- | --- | --- |
| `ci.yml / verify` | main push、main PR、手動実行 | Checkout → Repository contract → Go services → Web test and build の順です。 |
| `images.yml / publish` | main push、api-v*・back-v*・web-v* タグ、手動実行 | Checkout → QEMU → Buildx → Registry ログイン → 直列ビルド・公開・index 確認の順です。ci.yml への依存はありません。 |
| `gitea-android-ci.yml / android` | apps/android/** または当該ワークフローを変更する main PR、手動実行 | Checkout → Test and assemble debug application の順です。linux/amd64 の android-sdk:35 を使用します。 |
| `gitea-release.yml / create-release` | api-v*・back-v*・web-v*・android-v* タグ push | Create Gitea release を実行します。component-vX.Y.Z 形式が必要です。既存のリリースは変更しません。 |

images ジョブは API → back → web の順で処理します。コンポーネントタグでは対応するコンポーネントだけを選びます。main・手動実行では、バージョン順で最も高い既存タグを使うため、対象の各コンポーネントにタグが必要です。`git.seonology.com/seonology/seonology-journey-{api,back,web}`の各イメージに `X.Y.Z`、`sha-<7>`、`latest`を付けます。各 index は `linux/amd64`と `linux/arm64`を含みます。Registry ログインには PACKAGE_USER・PACKAGE_TOKEN、リリース公開には GITEA_TOKEN を使用します。

`apps/*/.releaserc.json`は `api-vX.Y.Z`、`back-vX.Y.Z`、`web-vX.Y.Z`、`android-vX.Y.Z`を定義します。各コンポーネントの scope と `all`の明示ルールでは、feat は minor、fix・perf・refactor は patch、破壊的変更は major に対応します。Gitea ワークフローは既存タグを公開し、semantic-release を呼び出すステップはありません。

```bash
git push origin main
git push origin api-vX.Y.Z
```

## 運用

![運用](assets/diagrams/runtime-cutover.ja.svg)

Argo CD Application `seonology-journey-monorepo`は、`seonology/seonology-k3s`の `workloads/seonology-journey/overlays/production`を読み、`seonology-journey`名前空間に適用します。Image Updater は Gitea の各 `latest`の digest を追跡し、`main`の Kustomization に書き戻します。Argo CD は自動 prune・self-heal を使用します。オーバーレイでイメージの digest を固定します。web、API、back のレプリカ設定はそれぞれ 2 です。

| リソース | 設定 |
| --- | --- |
| 公開パス | Traefik TLS は journey.seonology.com を web:8080 に、journey-api.seonology.com を API:8080 に接続します。API は api-cors、WebSocket は追加で ws-timeout（inFlightReq 200）を使用します。残りの UI パスは console-embed を使用します。 |
| 認証 | クライアントは Keycloak でログインします。API は中央 Deployment から KEYCLOAK_JWKS_URL、KEYCLOAK_ISSUER、KEYCLOAK_AUDIENCE を受け取ります。 |
| シークレット | External Secrets は Vault の AWS・Google Maps・Keycloak 項目を毎時同期します。shared/gitea-packages の認証情報は、3 つの Deployment が使用する gitea-registry-secret に保存します。 |
| ネットワークと観測 | 既定の拒否ポリシーに DNS、受信、API→back:9090、監視、外部 HTTPS の許可を追加します。ServiceMonitor は API:8081 と back:9091 を収集し、トレースは monitoring の OTel Collector に送ります。 |
| 状態確認 | 中央の web・API 準備状態 probe は /healthz を使用します。back の起動・生存・準備状態 probe は gRPC:9090 を使用します。API は /readyz も提供します。 |
| バックアップ | 中央 Velero daily-cluster の cron は 0 4 * * *、保持期間は 336 時間です。Journey は除外リストに含まれません。AWS テーブル作成スクリプトは、新規テーブルごとに DynamoDB PITR を有効にします。 |

### 実行時設定

| コンポーネント / 変数 | 既定値または設定値 | 用途 |
| --- | --- | --- |
| API: HTTP_LISTEN_ADDR / METRICS_LISTEN_ADDR | `:8080` / `:8081` | HTTP / Prometheus |
| API: BACK_GRPC_ADDR | `seonology-journey-back:9090` | gRPC 接続先 |
| API: CORS_ALLOW_ORIGIN | 中央設定: `https://journey.seonology.com` | ブラウザのオリジン |
| API: GOOGLE_MAPS_API_KEY / EXTERNAL_API_DAILY_LIMIT | キー / `1000` | Places・Directions 用です。UTC の日付変更でカウンターを初期化し、キャッシュ取得前に加算します。 |
| back: GRPC_LISTEN_ADDR / OBS_LISTEN_ADDR | `:9090` / `:9091` | gRPC / 状態とメトリクス |
| back: AWS_REGION / DYNAMODB_ENDPOINT | `ap-northeast-1` / 任意の URL | AWS リージョン / ローカル接続先 |
| back: MEDIA_PRESIGN_BASE_URL | `https://journey-media.seonology.local` | Stub URL の基準 |
| back: LOG_FORMAT / LOG_LEVEL | テキスト / info | json で JSON を出力します。debug、warn、error も指定できます。 |
| web: VITE_API_BASE | `https://journey-api.seonology.com` | クライアントが /api/v1 を付けます。 |
| web: VITE_KEYCLOAK_URL / VITE_KEYCLOAK_REALM / VITE_KEYCLOAK_CLIENT_ID | `https://auth.seonology.com` / `seonology-journey` / `journey-web` | ビルド時のログイン設定 |
| web: VITE_MAPBOX_TOKEN | 任意のトークン | Mapbox 地図コンポーネント |
| Android: ANDROID_VERSION_NAME / ANDROID_VERSION_CODE | `0.1.0` / `1` | ビルドバージョンです。API と Keycloak の URL は BuildConfig 定数です。 |

DynamoDB テーブルの接頭辞は定数 `seonology-journey-`です。back の起動コードは Deployment の METRICS_LISTEN_ADDR ではなく OBS_LISTEN_ADDR を読みます。中央マニフェストには DDB_TABLE_PREFIX、S3_MEDIA_BUCKET、AUTH_BACK_GRPC_ADDR、MEMBER_BACK_GRPC_ADDR がありますが、この起動コードは読み取りません。

## リポジトリ方針

![リポジトリ方針](assets/diagrams/repository-roles.ja.svg)

- `.commitlintrc.json`に定義された scope を明記し、Conventional Commits を使用します。
- Protobuf 定義と生成クライアントを一致させます。
- 認証情報は Gitea secrets、Vault、Kubernetes Secrets に保存します。

## ライセンス

[MIT ライセンス](LICENSE)を使用します。
