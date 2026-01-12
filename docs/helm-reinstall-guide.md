# Helm Chart Reinstallation Guide - robot-shop2

**Date**: 2026-01-09
**Purpose**: Ensure all fixes persist after Helm chart deletion and reinstallation

---

## Summary of Required Changes

This guide ensures that all OTel collector fixes and header propagation configurations are properly applied when reinstalling the Helm chart.

### ✅ Already Fixed in Helm Chart

1. **MongoDB TLS Configuration** - Already in `otel-collector-configmap-enhanced.yaml` (lines 29-31)
2. **Shipping Service Header Capture** - Already in `shipping-deployment.yaml` (lines 25-28)
3. **Node.js Services Header Capture** - Already in `catalogue/server.js`, `user/server.js`, `cart/server.js`

### ✅ New Fixes Applied (Ready for Reinstall)

1. **MySQL OTel Permissions** - New init script created: `mysql/scripts/30-otel-permissions.sql`
2. **Nginx Header Propagation** - Updated: `web/default.conf.template`

---

## Files Modified for Persistence

### 1. MySQL OTel Permissions (NEW)

**File**: [mysql/scripts/30-otel-permissions.sql](../mysql/scripts/30-otel-permissions.sql)

**Purpose**: Automatically grant OpenTelemetry collector the required MySQL permissions on database initialization.

**Content**:
```sql
-- OpenTelemetry Collector MySQL Permissions
-- Required for metrics collection from performance_schema

-- Grant SELECT on performance_schema tables
GRANT SELECT ON performance_schema.* TO 'shipping'@'%';

-- Grant PROCESS privilege for InnoDB metrics
GRANT PROCESS ON *.* TO 'shipping'@'%';

-- Apply changes
FLUSH PRIVILEGES;
```

**How it works**: MySQL Docker image automatically executes all `.sql` files in alphabetical order from the scripts directory during initialization. This file (30-*) runs after the main dump (10-*) and ratings schema (20-*).

**Verification after reinstall**:
```bash
# Check if permissions are applied
kubectl exec -n robot-shop2 <mysql-pod> -- mysql -u root -e "SHOW GRANTS FOR 'shipping'@'%';"

# Expected output should include:
# GRANT PROCESS ON *.* TO 'shipping'@'%'
# GRANT SELECT ON `performance_schema`.* TO 'shipping'@'%'
```

---

### 2. Nginx Header Propagation (UPDATED)

**File**: [web/default.conf.template](../web/default.conf.template)

**Purpose**: Propagate anomaly label headers from k6 load tests to backend services.

**Changes**: Added to all API proxy locations:
```nginx
location /api/catalogue/ {
    # Propagate anomaly label headers for labeled dataset generation
    proxy_pass_request_headers on;
    proxy_set_header x-anomaly-type $http_x_anomaly_type;
    proxy_set_header x-anomaly-label $http_x_anomaly_label;
    proxy_set_header x-anomaly-root-cause $http_x_anomaly_root_cause;
    proxy_set_header x-anomaly-msg $http_x_anomaly_msg;
    proxy_pass http://${CATALOGUE_HOST}:8080/;
}
```

**Applied to**:
- `/api/catalogue/`
- `/api/user/`
- `/api/cart/`
- `/api/shipping/`
- `/api/payment/`
- `/api/ratings/`

**How it works**:
- `proxy_pass_request_headers on` - Ensures headers are forwarded
- `proxy_set_header x-anomaly-* $http_x_anomaly_*` - Explicitly passes custom headers to backend services
- Nginx variables like `$http_x_anomaly_type` extract the incoming header value

**Verification after reinstall**:
```bash
# Port-forward to web service
kubectl port-forward -n robot-shop2 svc/web 8080:8080

# Test header propagation
curl -H "x-anomaly-type: test" \
     -H "x-anomaly-label: anomalous" \
     http://localhost:8080/api/catalogue/products

# Check catalogue logs for received headers
kubectl logs -n robot-shop2 -l service=catalogue --tail=20 | grep anomaly
```

---

## Helm Chart Reinstallation Checklist

### Pre-Reinstallation

- [x] Verify MySQL init script exists: `mysql/scripts/30-otel-permissions.sql`
- [x] Verify nginx config updated: `web/default.conf.template`
- [x] Verify OTel configmap has MongoDB TLS fix: `K8s/helm/templates/otel-collector-configmap-enhanced.yaml`
- [x] Verify shipping deployment has header capture: `K8s/helm/templates/shipping-deployment.yaml`
- [x] Verify Node.js services have header capture: `catalogue/server.js`, `user/server.js`, `cart/server.js`

### Docker Images to Rebuild (If Not Using Registry)

Since `mysql/scripts/` and `web/default.conf.template` changed, you need to rebuild:

1. **MySQL Image**:
   ```bash
   cd mysql
   docker build -t robotshop/rs-mysql-db:latest .
   # Optional: push to registry if using one
   ```

2. **Web Image**:
   ```bash
   cd web
   docker build -t robotshop/rs-web:latest .
   # Optional: push to registry if using one
   ```

### Reinstallation Steps

1. **Delete existing deployment**:
   ```bash
   helm uninstall robot-shop -n robot-shop2
   # Or delete namespace entirely:
   kubectl delete namespace robot-shop2
   kubectl create namespace robot-shop2
   ```

2. **Install fresh Helm chart**:
   ```bash
   helm install robot-shop --namespace robot-shop2 K8s/helm/
   ```

3. **Wait for all pods to be ready**:
   ```bash
   kubectl get pods -n robot-shop2 -w
   ```

---

## Post-Reinstallation Verification

### 1. Verify MySQL OTel Permissions

```bash
# Get MySQL pod name
MYSQL_POD=$(kubectl get pods -n robot-shop2 -l service=mysql -o jsonpath='{.items[0].metadata.name}')

# Check grants
kubectl exec -n robot-shop2 $MYSQL_POD -- mysql -u root -e "SHOW GRANTS FOR 'shipping'@'%';"
```

**Expected output**:
```
GRANT PROCESS ON *.* TO 'shipping'@'%'
GRANT ALL PRIVILEGES ON `cities`.* TO 'shipping'@'%'
GRANT SELECT ON `performance_schema`.* TO 'shipping'@'%'
```

### 2. Verify OTel Collector Logs (No Errors)

```bash
# Get OTel collector pod name
OTEL_POD=$(kubectl get pods -n robot-shop2 -l app=opentelemetry-collector -o jsonpath='{.items[0].metadata.name}')

# Check for errors (should be empty)
kubectl logs -n robot-shop2 $OTEL_POD --tail=200 | grep -i error

# Verify MySQL metrics collection
kubectl logs -n robot-shop2 $OTEL_POD --tail=100 | grep -i mysql

# Verify MongoDB metrics collection
kubectl logs -n robot-shop2 $OTEL_POD --tail=100 | grep -i mongodb
```

**Expected**: No SSL errors, no permission errors, regular metric exports

### 3. Verify Nginx Header Propagation

```bash
# Port-forward web service
kubectl port-forward -n robot-shop2 svc/web 8080:8080 &

# Send test request with headers
curl -s -H "x-anomaly-type: latency_spike" \
     -H "x-anomaly-label: anomalous" \
     -H "x-anomaly-root-cause: slow_database" \
     -H "x-anomaly-msg: test header propagation" \
     http://localhost:8080/api/catalogue/products > /dev/null

# Check catalogue service received headers
kubectl logs -n robot-shop2 -l service=catalogue --tail=10 | grep -i anomaly
```

**Expected**: Should see headers in catalogue logs

### 4. Verify Service Header Capture

```bash
# Check shipping deployment env vars
kubectl get deployment shipping -n robot-shop2 -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST")].value}'
```

**Expected output**:
```
x-anomaly-type,x-anomaly-label,x-anomaly-root-cause,x-anomaly-msg
```

### 5. End-to-End Test with k6

```bash
# Run k6 test with anomaly labels
k6 run k6-scripts/k6_optel_anomaly_labeled.js

# Wait for traces to export
sleep 60

# Copy traces from OTel collector
OTEL_POD=$(kubectl get pods -n robot-shop2 -l app=opentelemetry-collector -o jsonpath='{.items[0].metadata.name}')
kubectl cp robot-shop2/$OTEL_POD:/var/log/otel/traces.json ./data/traces_test.json

# Extract dataset
python3 python-scripts/extract-labeled-dataset.py \
    --traces ./data/traces_test.json \
    --output ./data/dataset_test

# Check for anomalous labels
cat ./data/dataset_test/traces_labeled_*.csv | cut -d',' -f17 | sort | uniq -c
```

**Expected output**:
```
   1500 normal
    107 anomalous  <-- Should see anomalous labels!
```

---

## Troubleshooting

### Issue: MySQL permissions not applied

**Symptom**: OTel collector logs show permission errors

**Solution**:
```bash
# Check if init script is in the image
MYSQL_POD=$(kubectl get pods -n robot-shop2 -l service=mysql -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n robot-shop2 $MYSQL_POD -- ls -la /docker-entrypoint-initdb.d/

# If missing, rebuild MySQL image with latest scripts
cd mysql
docker build -t robotshop/rs-mysql-db:latest .
docker push robotshop/rs-mysql-db:latest  # if using registry

# Delete MySQL pod to force recreation
kubectl delete pod -n robot-shop2 -l service=mysql
```

### Issue: Headers not reaching services

**Symptom**: Only "normal" labels in dataset

**Possible causes**:
1. **Nginx not propagating headers** - Rebuild web image with updated `default.conf.template`
2. **Services not capturing headers** - Verify Node.js services have header capture code
3. **Instana not forwarding to OTel** - Check Jaeger UI for header attributes

**Debug**:
```bash
# Check nginx config in running pod
WEB_POD=$(kubectl get pods -n robot-shop2 -l service=web -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n robot-shop2 $WEB_POD -- cat /etc/nginx/conf.d/default.conf | grep -A 5 "x-anomaly"

# Should see proxy_set_header directives
```

### Issue: OTel collector MongoDB SSL errors

**Symptom**: Logs show "SSL handshake received but server is started without SSL support"

**Solution**: Verify `otel-collector-configmap-enhanced.yaml` has TLS configuration:
```yaml
mongodb:
  hosts:
    - endpoint: mongodb:27017
  collection_interval: 30s
  tls:
    insecure: true
    insecure_skip_verify: true
```

---

## Summary: What's Persistent vs. What's Not

### ✅ Persistent (Survives Helm Reinstall)

| Component | File | Why Persistent |
|-----------|------|----------------|
| MongoDB TLS config | `otel-collector-configmap-enhanced.yaml` | Part of Helm chart |
| Shipping header env | `shipping-deployment.yaml` | Part of Helm chart |
| Node.js header capture | `catalogue/server.js`, `user/server.js`, `cart/server.js` | Baked into Docker images |
| MySQL OTel permissions | `mysql/scripts/30-otel-permissions.sql` | Auto-applied at DB init |
| Nginx header propagation | `web/default.conf.template` | Baked into Docker image |

### ❌ Not Persistent (Lost on Reinstall)

| Component | Fix |
|-----------|-----|
| Manual `kubectl exec` MySQL grants | Use init script instead |
| Manual ConfigMap patches | Update Helm templates |
| Runtime service restarts | Rebuild images |

---

## Files Reference

### Modified Files (Helm Chart)
- [K8s/helm/templates/otel-collector-configmap-enhanced.yaml](../K8s/helm/templates/otel-collector-configmap-enhanced.yaml) - MongoDB TLS fix (lines 29-31)
- [K8s/helm/templates/shipping-deployment.yaml](../K8s/helm/templates/shipping-deployment.yaml) - Header capture env vars (lines 25-28)

### Modified Files (Docker Images)
- [mysql/scripts/30-otel-permissions.sql](../mysql/scripts/30-otel-permissions.sql) - **NEW** - OTel permissions
- [web/default.conf.template](../web/default.conf.template) - **UPDATED** - Header propagation
- [catalogue/server.js](../catalogue/server.js) - Header capture middleware
- [user/server.js](../user/server.js) - Header capture middleware
- [cart/server.js](../cart/server.js) - Header capture middleware

### Documentation
- [otel-collector-fixes.md](otel-collector-fixes.md) - Original fix documentation
- [header-capture-verification.md](header-capture-verification.md) - Header capture implementation
- [helm-reinstall-guide.md](helm-reinstall-guide.md) - This file

---

**Result**: After following this guide, all OTel collector fixes will persist through Helm chart reinstallation, and anomaly labels will properly propagate from k6 → Nginx → Services → OpenTelemetry → Dataset.
