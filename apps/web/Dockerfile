# syntax=docker/dockerfile:1.7
FROM node:20-alpine AS builder
WORKDIR /workspace
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
RUN pnpm install --frozen-lockfile --filter @seonology/journey-web...
COPY apps/web ./apps/web
RUN pnpm --filter @seonology/journey-web build

FROM nginxinc/nginx-unprivileged:1.31-alpine
USER root
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /workspace/apps/web/dist /usr/share/nginx/html
USER nginx
EXPOSE 8080
