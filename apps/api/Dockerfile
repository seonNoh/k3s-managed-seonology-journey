# syntax=docker/dockerfile:1.7
FROM golang:1.26-alpine AS builder
WORKDIR /src

COPY apps/api/go.mod apps/api/go.sum* ./apps/api/
COPY proto/gen/go/go.mod proto/gen/go/go.sum* ./proto/gen/go/
RUN cd apps/api && go mod download || true

COPY proto/gen ./proto/gen
COPY apps/api ./apps/api

WORKDIR /src/apps/api
RUN CGO_ENABLED=0 GOOS=linux go build -trimpath -ldflags="-s -w" -o /out/server ./cmd/server

FROM gcr.io/distroless/static-debian12:nonroot
WORKDIR /app
COPY --from=builder /out/server /app/server
USER nonroot:nonroot
EXPOSE 8080
ENTRYPOINT ["/app/server"]
