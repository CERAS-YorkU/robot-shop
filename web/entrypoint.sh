#!/usr/bin/env sh

BASE_DIR=/usr/share/nginx/html

if [ -n "$1" ]
then
    exec "$@"
fi

# Configure EUM
if [ -n "$INSTANA_EUM_KEY" -a -n "$INSTANA_EUM_REPORTING_URL" ]
then
    echo "Enabling Instana EUM"
    result=$(curl -kv -s --connect-timeout 10 "$INSTANA_EUM_REPORTING_URL" 2>&1 | grep "301 Moved Permanently")
    if [ -n "$result" ];
    then
        echo '301 Moved Permanently found!'
        case "${INSTANA_EUM_REPORTING_URL}" in
            */) ;;
            *) INSTANA_EUM_REPORTING_URL="${INSTANA_EUM_REPORTING_URL}/" ;;
        esac
        sed -i "s|INSTANA_EUM_KEY|$INSTANA_EUM_KEY|" $BASE_DIR/eum-tmpl.html
        sed -i "s|INSTANA_EUM_REPORTING_URL|$INSTANA_EUM_REPORTING_URL|" $BASE_DIR/eum-tmpl.html
        cp $BASE_DIR/eum-tmpl.html $BASE_DIR/eum.html
    else
        echo "Go with the user input"
        sed -i "s|INSTANA_EUM_KEY|$INSTANA_EUM_KEY|" $BASE_DIR/eum-tmpl.html
        sed -i "s|INSTANA_EUM_REPORTING_URL|$INSTANA_EUM_REPORTING_URL|" $BASE_DIR/eum-tmpl.html
        cp $BASE_DIR/eum-tmpl.html $BASE_DIR/eum.html
    fi
else
    echo "EUM not enabled"
    cp $BASE_DIR/empty.html $BASE_DIR/eum.html
fi

# make sure nginx can access the eum file
chmod 644 $BASE_DIR/eum.html

# apply environment variables to default.conf
envsubst '${CATALOGUE_HOST} ${USER_HOST} ${CART_HOST} ${SHIPPING_HOST} ${PAYMENT_HOST} ${RATINGS_HOST}' < /etc/nginx/conf.d/default.conf.template > /etc/nginx/conf.d/default.conf

# Configure OpenTelemetry with nginx-otel module
echo "Configuring OpenTelemetry tracing with nginx-otel"
echo "  Service Name: ${OTEL_SERVICE_NAME}"
echo "  OTLP Endpoint: ${OTEL_EXPORTER_OTLP_ENDPOINT}"

# Create nginx.conf with nginx-otel module loaded
cat > /etc/nginx/nginx.conf << 'NGINXEOF'
load_module /usr/lib/nginx/modules/ngx_otel_module.so;

user  nginx;
worker_processes  auto;

error_log  /var/log/nginx/error.log notice;
pid        /var/run/nginx.pid;

events {
    worker_connections  1024;
}

http {
    include       /etc/nginx/mime.types;
    default_type  application/octet-stream;

    log_format  main  '$remote_addr - $remote_user [$time_local] "$request" '
                      '$status $body_bytes_sent "$http_referer" '
                      '"$http_user_agent" "$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile        on;
    keepalive_timeout  65;

    # OpenTelemetry configuration
    otel_exporter {
        endpoint OTEL_ENDPOINT_PLACEHOLDER;
    }

    otel_service_name OTEL_SERVICE_NAME_PLACEHOLDER;
    otel_trace on;

    include /etc/nginx/conf.d/*.conf;
}
NGINXEOF

# Replace placeholders with actual values
sed -i "s|OTEL_ENDPOINT_PLACEHOLDER|${OTEL_EXPORTER_OTLP_ENDPOINT}|g" /etc/nginx/nginx.conf
sed -i "s|OTEL_SERVICE_NAME_PLACEHOLDER|${OTEL_SERVICE_NAME}|g" /etc/nginx/nginx.conf

echo "OpenTelemetry module configured successfully"

exec nginx -g 'daemon off;'
