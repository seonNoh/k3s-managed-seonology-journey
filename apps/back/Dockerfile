# syntax=docker/dockerfile:1.7
# Build context: repo root (so we can include proto/gen replaced module).
FROM golang:1.26-alpine AS builder
WORKDIR /src
COPY apps/back/go.mod apps/back/go.sum ./apps/back/
COPY proto/gen/go/go.mod proto/gen/go/go.sum ./proto/gen/go/
RUN cd apps/back && go mod download || true
COPY proto/gen ./proto/gen
COPY apps/back ./apps/back
RUN cd apps/back && CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/server ./cmd/server

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=builder /out/server /app/server
USER nonroot:nonroot
EXPOSE 9090
ENTRYPOINT ["/app/server"]
