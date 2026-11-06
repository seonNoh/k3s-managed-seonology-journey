#!/usr/bin/env python3
"""Generate the twelve multilingual Journey Relief diagrams deterministically."""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "assets" / "diagrams"
LANG_SUFFIX = {"en": "", "ko": ".ko", "ja": ".ja"}
TOPICS = ("service-architecture", "component-delivery", "runtime-cutover", "repository-roles")

RELIEF = '<style>\n  svg{\n    --bg:#0d1117; --surface-a:#1b222c; --surface-b:#151b23;\n    --lead-a:#222b38; --lead-b:#19202a;\n    --inner:#1e2530; --inner-lead:#232c39;\n    --line:#252d38; --line-lead:#33404f;\n    --text:#f0f6fc; --body:#c3ccd6; --dim:#a2abb5; --faint:#8d959f;\n    --accent:#7c9fff; --accent-bg:rgba(124,159,255,.16);\n    --ok:#4ac97e; --warn:#e0a740; --bad:#f2705e; --off:#8b939d;\n    --quiet:#78818c;\n    --sh:#000; --sh-op:.50; --shl-op:.58; --shs-op:.40;\n    --glow-op:.40; --glow-cast:.45; --hl:rgba(255,255,255,.05);\n  }\n  @media (prefers-color-scheme: light){\n    svg{\n      --bg:#f6f8fa; --surface-a:#ffffff; --surface-b:#fafbfc;\n      --lead-a:#ffffff; --lead-b:#f5f8ff;\n      --inner:#eef1f4; --inner-lead:#e9f0fe;\n      --line:#d8dee4; --line-lead:#b8c9ee;\n      --text:#1f2328; --body:#3d444d; --dim:#59636e; --faint:#656d7a;\n      --accent:#2f62d4; --accent-bg:rgba(47,98,212,.10);\n      --ok:#187734; --warn:#8e5f00; --bad:#cf222e; --off:#5f6773;\n      --quiet:#6e7781;\n      --sh:#1f2328; --sh-op:.13; --shl-op:.18; --shs-op:.12;\n      --glow-op:.35; --glow-cast:.14; --hl:transparent;\n    }\n  }\n  .P-flow{fill:none;stroke:var(--accent);stroke-width:1.6;\n          stroke-linecap:round;stroke-linejoin:round;\n          stroke-dasharray:5 6;animation:P-move 2s linear infinite}\n  .P-quiet{fill:none;stroke:var(--quiet);stroke-width:1.4;\n           stroke-linecap:round;stroke-linejoin:round}\n  @keyframes P-move{to{stroke-dashoffset:-22}}\n  @media (prefers-reduced-motion:reduce){.P-flow{animation:none}}\n</style>\n<defs>\n  <filter id="P-sh" x="-30%" y="-30%" width="160%" height="170%">\n    <feDropShadow dx="-3" dy="10" stdDeviation="9" flood-color="var(--sh)" flood-opacity="var(--sh-op)"/>\n  </filter>\n  <filter id="P-shl" x="-30%" y="-30%" width="160%" height="180%">\n    <feDropShadow dx="-4" dy="13" stdDeviation="11" flood-color="var(--sh)" flood-opacity="var(--shl-op)"/>\n  </filter>\n  <filter id="P-shs" x="-30%" y="-30%" width="160%" height="170%">\n    <feDropShadow dx="-2" dy="4" stdDeviation="4" flood-color="var(--sh)" flood-opacity="var(--shs-op)"/>\n  </filter>\n  <filter id="P-gl" x="-60%" y="-90%" width="220%" height="280%">\n    <feDropShadow dx="0" dy="0" stdDeviation="8" flood-color="var(--accent)" flood-opacity="var(--glow-op)"/>\n    <feDropShadow dx="0" dy="4" stdDeviation="5" flood-color="var(--sh)" flood-opacity="var(--glow-cast)"/>\n  </filter>\n  <linearGradient id="P-s" x1="0" y1="0" x2=".3" y2="1">\n    <stop offset="0" stop-color="var(--surface-a)"/><stop offset="1" stop-color="var(--surface-b)"/>\n  </linearGradient>\n  <linearGradient id="P-sl" x1="0" y1="0" x2=".3" y2="1">\n    <stop offset="0" stop-color="var(--lead-a)"/><stop offset="1" stop-color="var(--lead-b)"/>\n  </linearGradient>\n  <marker id="P-t" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">\n    <path d="M0,0 L8,4 L0,8 z" fill="var(--accent)"/>\n  </marker>\n  <marker id="P-tq" viewBox="0 0 8 8" refX="7" refY="4" markerWidth="6" markerHeight="6" orient="auto-start-reverse">\n    <path d="M0,0 L8,4 L0,8 z" fill="var(--quiet)"/>\n  </marker>\n</defs>'

TEXT = {
    "service-architecture": {
        "en": ("Service architecture", "Client requests, JWT keys and durable metadata",
               ["Web", "Android", "Journey API", "Journey back", "Keycloak", "DynamoDB",
                "REST · :8080", "gRPC · :9090", "JWKS", "Metadata",
                "Media URLs: StubPresigner. Geocoding: back → Nominatim. Nearby/transit: API → Google Maps."]),
        "ko": ("서비스 아키텍처", "클라이언트 요청, JWT 공개 키와 영속 메타데이터",
               ["웹", "Android", "Journey API", "Journey back", "Keycloak", "DynamoDB",
                "REST · :8080", "gRPC · :9090", "JWKS", "메타데이터",
                "미디어 URL: StubPresigner · 지리 검색: back → Nominatim · 주변·교통: API → Google Maps"]),
        "ja": ("サービス構成", "クライアントのリクエスト、JWT 公開鍵、永続メタデータ",
               ["Web", "Android", "Journey API", "Journey back", "Keycloak", "DynamoDB",
                "REST · :8080", "gRPC · :9090", "JWKS", "メタデータ",
                "メディア URL: StubPresigner · 地理検索: back → Nominatim · 周辺・交通: API → Google Maps"]),
    },
    "component-delivery": {
        "en": ("Component delivery", "images.yml / publish: API, back and web run serially",
               ["Trigger", "main / manual", "Component tag", "Gitea Registry", "1 · API", "2 · back", "3 · web",
                "linux/amd64 + linux/arm64", "Tags: X.Y.Z · sha-<7> · latest",
                "A component tag selects only its matching image. Main/manual resolves each latest component version tag."]),
        "ko": ("컴포넌트 게시", "images.yml의 publish 잡은 API, back, web을 순서대로 처리합니다",
               ["시작 조건", "main / 수동 실행", "컴포넌트 태그", "Gitea Registry", "1 · API", "2 · back", "3 · web",
                "linux/amd64 + linux/arm64", "태그: X.Y.Z · sha-<7> · latest",
                "컴포넌트 태그는 해당 이미지만 선택합니다. main·수동 실행은 각 컴포넌트의 최신 버전 태그를 찾습니다."]),
        "ja": ("コンポーネントの公開", "images.yml の publish ジョブは API、back、web を順番に処理します",
               ["起動条件", "main / 手動実行", "コンポーネントタグ", "Gitea Registry", "1 · API", "2 · back", "3 · web",
                "linux/amd64 + linux/arm64", "タグ: X.Y.Z · sha-<7> · latest",
                "コンポーネントタグでは対応するイメージだけを公開します。main・手動実行では各最新バージョンタグを使います。"]),
    },
    "runtime-cutover": {
        "en": ("GitOps delivery", "Digest tracking → Git write-back → automated sync",
               ["Gitea Registry", "Image Updater", "seonology-k3s", "Argo CD",
                "Read latest digest", "Write kustomization", "Read overlay",
                "Target: seonology-journey · web / API / back: 2 replicas each",
                "workloads/seonology-journey/overlays/production", "k3s namespace", "Apply Deployments"]),
        "ko": ("GitOps 배포", "digest 추적 → Git 기록 → 자동 동기화",
               ["Gitea Registry", "Image Updater", "seonology-k3s", "Argo CD",
                "latest digest 조회", "kustomization 기록", "오버레이 조회",
                "대상: seonology-journey · web / API / back: 각각 복제본 2개",
                "workloads/seonology-journey/overlays/production", "k3s 네임스페이스", "Deployment 적용"]),
        "ja": ("GitOps デプロイ", "digest の追跡 → Git への書き戻し → 自動同期",
               ["Gitea Registry", "Image Updater", "seonology-k3s", "Argo CD",
                "latest digest の取得", "kustomization の更新", "オーバーレイ取得",
                "対象: seonology-journey · web / API / back: 各 2 レプリカ",
                "workloads/seonology-journey/overlays/production", "k3s 名前空間", "Deployment を適用"]),
    },
    "repository-roles": {
        "en": ("Repository map", "Directory ownership within one monorepo",
               ["Applications", "React client", "REST / WebSocket", "gRPC / DynamoDB", "Android client",
                "Shared contracts", "Protobuf → Go / TypeScript", "Standalone manifests",
                "Cluster source: seonology-k3s / workloads/seonology-journey",
                "Gitea is the source of truth; its push mirror copies branches and tags to GitHub."]),
        "ko": ("저장소 구성", "하나의 모노레포에서 디렉터리별 역할을 구분합니다",
               ["애플리케이션", "React 클라이언트", "REST / WebSocket", "gRPC / DynamoDB", "Android 클라이언트",
                "공통 계약", "Protobuf → Go / TypeScript", "독립 매니페스트",
                "클러스터 소스: seonology-k3s / workloads/seonology-journey",
                "Gitea가 기준 저장소이며, push mirror가 브랜치와 태그를 GitHub에 복사합니다."]),
        "ja": ("リポジトリ構成", "単一モノレポ内のディレクトリと役割",
               ["アプリケーション", "React クライアント", "REST / WebSocket", "gRPC / DynamoDB", "Android クライアント",
                "共通の契約", "Protobuf → Go / TypeScript", "独立マニフェスト",
                "クラスタのソース: seonology-k3s / workloads/seonology-journey",
                "Gitea が基準リポジトリです。push mirror がブランチとタグを GitHub にコピーします。"]),
    },
}


class Drawing:
    def __init__(self, prefix: str):
        self.p = prefix
        self.parts: list[str] = []

    def text(self, x, y, value, size=13, box=None, mono=False, color="body"):
        attrs = f' data-box="{self.p}-{box}"' if box else ""
        family = "ui-monospace, SFMono-Regular, Menlo, monospace" if mono else "Pretendard, system-ui, -apple-system, sans-serif"
        weight = 600 if size == 20 else 500 if size == 15 else 400
        self.parts.append(f'<text x="{x}" y="{y}" font-size="{size}" font-family="{family}" font-weight="{weight}" fill="var(--{color})"{attrs}>{html.escape(value)}</text>')

    def rect(self, key, x, y, w, h, kind="card", lead=False):
        surface = "sl" if lead else "s"
        shadow = "shl" if lead else "sh"
        fill = f"url(#{self.p}-{surface})" if kind in ("card", "region") else "var(--inner)"
        radius = 12 if kind in ("card", "region") else 8
        self.parts.append(f'<rect id="{self.p}-{key}" data-kind="{kind}" x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="var(--{"line-lead" if lead else "line"})" filter="url(#{self.p}-{shadow})"/>')
        if kind == "card":
            self.parts.append(f'<path d="M{x+12},{y+1} H{x+w-12}" stroke="var(--hl)" fill="none"/>')

    def arrow(self, src, dst, pts, flow=False):
        # Straight segments and quadratic corner arcs follow the declared vertices.
        d = f"M{pts[0][0]},{pts[0][1]}"
        for i, (x, y) in enumerate(pts[1:], 1):
            if i < len(pts)-1:
                px, py = pts[i-1]
                nx, ny = pts[i+1]
                radius = min(8, (abs(x-px)+abs(y-py))/2, (abs(nx-x)+abs(ny-y))/2)
                ux, uy = (x-px)/(abs(x-px)+abs(y-py)), (y-py)/(abs(x-px)+abs(y-py))
                vx, vy = (nx-x)/(abs(nx-x)+abs(ny-y)), (ny-y)/(abs(nx-x)+abs(ny-y))
                d += f" L{x-ux*radius:g},{y-uy*radius:g} Q{x},{y} {x+vx*radius:g},{y+vy*radius:g}"
            else:
                d += f" L{x},{y}"
        data = ";".join(f"{x},{y}" for x,y in pts)
        self.parts.append(f'<path data-from="{self.p}-{src}" data-to="{self.p}-{dst}" data-pts="{data}" d="{d}" class="{self.p}-{"flow" if flow else "quiet"}" marker-end="url(#{self.p}-{"t" if flow else "tq"})"/>')

    def line(self, d, dashed=False):
        dash = ' stroke-dasharray="2 6"' if dashed else ""
        self.parts.append(f'<path d="{d}" fill="none" stroke="var(--quiet)" stroke-width="1"{dash}/>')


def render(topic: str, language: str) -> str:
    title, subtitle, t = TEXT[topic][language]
    prefix = f"j60-{topic}-{language}"
    g = Drawing(prefix)
    g.text(32, 38, title, 20, color="text")
    g.text(32, 64, subtitle, 13.5, color="dim")
    if topic == "service-architecture":
        for key,x,y,w,h,lead in [
            ("web",32,144,192,88,False),("android",32,288,192,88,False),
            ("api",336,208,240,144,True),("back",688,208,240,104,False),
            ("keys",336,80,240,88,False),("ddb",688,400,240,80,False)]:
            g.rect(key,x,y,w,h,lead=lead)
        for key,x,y,label in [("web",56,180,t[0]),("android",56,324,t[1]),
                              ("api",360,244,t[2]),("back",712,244,t[3]),
                              ("keys",360,120,t[4]),("ddb",712,432,t[5])]:
            g.text(x,y,label,15,key,color="text")
        for x,y,label,box in [(56,208,"apps/web","web"),(56,352,"apps/android","android"),
                             (360,280,":8080 · :8081","api"),(360,312,"/api/v1 · /ws/trips","api"),
                             (712,280,":9090 · :9091","back"),(712,456,t[9],"ddb"),
                             (360,144,"seonology-journey","keys")]:
            g.text(x,y,label,13,box,mono=label.startswith(("apps",":","/")))
        g.arrow("web","api",[(224,188),(280,188),(280,256),(336,256)],True)
        g.arrow("android","api",[(224,332),(336,332)])
        g.arrow("api","back",[(576,260),(688,260)],True)
        g.arrow("api","keys",[(456,208),(456,168)])
        g.arrow("back","ddb",[(808,312),(808,400)])
        g.text(240,172,"REST",13,color="dim")
        g.text(240,316,"REST",13,color="dim")
        g.text(608,244,"gRPC",13,color="dim")
        g.text(472,188,"JWKS",13,color="dim")
        g.text(824,364,"AWS SDK",13,color="dim")
        g.text(32,516,t[10],13,color="faint")
    elif topic == "component-delivery":
        g.rect("trigger",32,112,192,192)
        for y,txt,size in [(144,t[0],15),(184,t[1],13),(224,t[2],13),(256,"*-vX.Y.Z",13),(280,"workflow_dispatch",13)]:
            g.text(52,y,txt,size,"trigger",mono=txt in ("*-vX.Y.Z","workflow_dispatch"))
        for i,key in enumerate(("api","back","web")):
            y=112+i*120
            g.rect(key,280,y,344,80,lead=i==0)
            g.text(304,y+32,t[4+i],15,key,color="text")
            g.text(304,y+56,f"apps/{key}/Dockerfile",13,key,mono=True)
        g.rect("registry",688,112,240,320,kind="region")
        g.text(712,144,t[3],15,"registry",color="text")
        for i,key in enumerate(("api","back","web")):
            y=168+i*120
            g.text(712,y,f"seonology-journey-{key}",13,"registry",mono=True)
            g.arrow(key,"registry",[(624,152+i*120),(688,152+i*120)])
        g.arrow("trigger","api",[(224,152),(280,152)])
        g.arrow("api","back",[(452,192),(452,232)],True)
        g.arrow("back","web",[(452,312),(452,352)],True)
        g.text(32,464,t[7],13,color="dim")
        g.text(456,464,t[8],13,mono=True,color="dim")
        # The longest translated note is split by meaning, not by clipping.
        notes={
            "en": ["Component tags select only their matching image.", "Main/manual resolves the latest component version tags; CI runs independently."],
            "ko": ["컴포넌트 태그는 해당 이미지만 선택합니다.", "main·수동 실행은 각 최신 버전 태그를 찾습니다. CI는 별도 트리거로 실행됩니다."],
            "ja": ["コンポーネントタグでは対応するイメージだけを公開します。", "main・手動実行では各最新バージョンタグを使います。CI は別のトリガーで動きます。"]
        }
        g.text(32,496,notes[language][0],13,color="faint")
        g.text(32,520,notes[language][1],13,color="faint")
    elif topic == "runtime-cutover":
        for key,x,label in [("registry",24,t[0]),("updater",208,t[1]),
                            ("git",392,t[2]),("argo",576,t[3])]:
            g.rect(key,x,104,176,88,lead=key=="updater")
            g.text(x+20,148,label,15,key,color="text")
        g.rect("namespace",760,104,176,88)
        g.text(776,136,t[9],15,"namespace",color="text")
        g.text(776,168,"seonology-journey",13,"namespace",mono=True)
        for x in (112,296,480,664,848):
            g.line(f"M{x},192 V472",True)
        for key,x,y,h in [("reg-act",104,224,32),("upd-act",288,224,112),
                           ("git-act",472,296,104),("argo-act",656,368,104),
                           ("namespace-act",840,440,32)]:
            g.rect(key,x,y,16,h,kind="block")
        messages = [
            ("upd-act","reg-act",[(288,240),(120,240)],136,t[4],False),
            ("upd-act","git-act",[(304,312),(472,312)],320,t[5],True),
            ("argo-act","git-act",[(656,384),(488,384)],504,t[6],False),
            ("argo-act","namespace-act",[(672,456),(840,456)],688,t[10],True),
        ]
        for src,dst,pts,label_x,label,flow in messages:
            g.arrow(src,dst,pts,flow)
            g.text(label_x,pts[0][1]-7,label,13,color="dim")
        g.text(32,496,t[7],13,color="body")
        g.text(32,520,t[8],13,mono=True,color="faint")
    elif topic == "repository-roles":
        g.rect("repo",32,104,896,344,kind="region",lead=True)
        g.text(56,136,"k3s-managed-seonology-journey/",15,"repo",mono=True,color="text")
        g.rect("apps",56,160,416,256)
        g.text(80,192,"apps/",15,"apps",mono=True,color="text")
        for i,(name,role) in enumerate(zip(("web/","api/","back/","android/"),t[1:5])):
            y=232+i*48
            g.line(f"M88,{y-5} H104")
            g.text(112,y,name,13,"apps",mono=True)
            g.text(224,y,role,13,"apps")
        g.line("M88,216 V371")
        g.rect("proto",504,160,400,104)
        g.text(528,192,"proto/",15,"proto",mono=True,color="text")
        g.text(528,224,t[5],13,"proto")
        g.text(528,240,t[6],13,"proto")
        g.rect("deploy",504,288,400,128)
        g.text(528,320,"deploy/",15,"deploy",mono=True,color="text")
        g.text(528,352,t[7],13,"deploy")
        g.text(528,384,"Kustomize",13,"deploy",mono=True)
        g.text(32,480,t[8],13,color="body")
        g.text(32,516,t[9],13,color="faint")

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="960" height="540" viewBox="0 0 960 540" lang="{language}" role="img" aria-labelledby="{prefix}-title {prefix}-desc">\n'
        f'<title id="{prefix}-title">{html.escape(title)}</title>\n'
        f'<desc id="{prefix}-desc">{html.escape(subtitle)}</desc>\n'
        + RELIEF.replace("P-", prefix+"-")
        + '\n<rect x="0" y="0" width="960" height="540" fill="var(--bg)"/>\n'
        + "\n".join(g.parts) + "\n</svg>\n"
    )


def outputs() -> dict[Path, str]:
    result = {}
    entries = []
    for topic in TOPICS:
        for language, suffix in LANG_SUFFIX.items():
            filename = f"{topic}{suffix}.svg"
            result[OUT / filename] = render(topic, language)
            entries.append({"file": filename, "pedia_id": f"svg-svg-gtm-live-65-journey-{topic}-{language}"})
    result[OUT / "pedia-manifest.json"] = json.dumps({"contract_version": 1, "entries": entries}, ensure_ascii=False, indent=2) + "\n"
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    mismatches = []
    for path, expected in outputs().items():
        if args.check:
            if not path.is_file() or path.read_text(encoding="utf-8") != expected:
                mismatches.append(str(path.relative_to(ROOT)))
        else:
            path.write_text(expected, encoding="utf-8")
    if mismatches:
        print("Generated files differ:", ", ".join(mismatches))
        return 1
    print("Phase B SVG set is deterministic" if args.check else "Generated Phase B SVG set")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
