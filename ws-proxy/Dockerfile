FROM nginx:alpine

# Generate self-signed cert at build time (valid 10 years)
RUN apk add --no-cache openssl && \
    mkdir -p /etc/nginx/certs && \
    openssl req -x509 -nodes -days 3650 \
      -subj "/CN=ws.zf.nexacore.my.id" \
      -newkey rsa:2048 \
      -keyout /etc/nginx/certs/self.key \
      -out /etc/nginx/certs/self.crt && \
    apk del openssl

COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8443
