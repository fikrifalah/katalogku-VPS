# PocketBase image for ARM64 STB
FROM alpine:3.22

ARG PB_VERSION=0.40.5
ARG PB_URL=https://github.com/pocketbase/pocketbase/releases/download

RUN apk add --no-cache ca-certificates wget unzip \
 && wget -4 -S --timeout=30 --tries=1 -O /tmp/pb.zip \
    "${PB_URL}/v${PB_VERSION}/pocketbase_${PB_VERSION}_linux_arm64.zip" \
 && unzip /tmp/pb.zip pocketbase -d /usr/local/bin \
 && rm /tmp/pb.zip

EXPOSE 8090

CMD ["pocketbase", "serve", "--http=0.0.0.0:8090", "--dir=/pb_data"]