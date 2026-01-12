# OpenTelemetry Collector Fixes - robot-shop2

**Date**: 2026-01-09
**Namespace**: robot-shop2

## Problems Identified

The otel-collector pod was generating massive amounts of error logs (running continuously every 30 seconds) due to two critical issues:

### 1. MongoDB SSL/TLS Configuration Mismatch
**Error**: `SSLHandshakeFailed: SSL handshake received but server is started without SSL support`

**Root Cause**: The MongoDB receiver in otel-collector was attempting SSL/TLS connections, but the MongoDB instance was running without SSL support.

**Symptoms**:
- Connection failures every 30s (collection_interval)
- EOF errors on connection attempts
- Server selection timeouts

### 2. MySQL Insufficient Privileges
**Error**: `SELECT command denied to user 'shipping'@'10.42.14.64' for table ...`

**Root Cause**: The `shipping` MySQL user lacked necessary privileges to query performance_schema tables required by the MySQL receiver.

**Missing Privileges**:
- `SELECT` on `performance_schema.*`
- `PROCESS` global privilege for InnoDB stats

## Solutions Implemented

### Fix 1: MongoDB Configuration Update

**File Modified**: `K8s/helm/templates/otel-collector-configmap-enhanced.yaml`

**Changes** (lines 24-31):
```yaml
# MongoDB metrics receiver
mongodb:
  hosts:
    - endpoint: mongodb:27017
  collection_interval: 30s
  tls:
    insecure: true
    insecure_skip_verify: true
```

**Rationale**: Disabled TLS verification to match MongoDB server configuration. This is acceptable for internal cluster communication in a demo environment.

### Fix 2: MySQL User Privilege Grants

**Commands Executed**:
```bash
# Grant SELECT on performance_schema tables
kubectl exec -n robot-shop2 mysql-566ccd4dc6-xmmn4 -- \
  mysql -u root -e "GRANT SELECT ON performance_schema.* TO 'shipping'@'%'; FLUSH PRIVILEGES;"

# Grant PROCESS privilege for InnoDB metrics
kubectl exec -n robot-shop2 mysql-566ccd4dc6-xmmn4 -- \
  mysql -u root -e "GRANT PROCESS ON *.* TO 'shipping'@'%'; FLUSH PRIVILEGES;"
```

**Final Grants**:
```sql
GRANT PROCESS ON *.* TO 'shipping'@'%'
GRANT ALL PRIVILEGES ON `cities`.* TO 'shipping'@'%'
GRANT SELECT ON `performance_schema`.* TO 'shipping'@'%'
```

## Deployment Steps

1. **Applied ConfigMap Update**:
   ```bash
   kubectl apply -f K8s/helm/templates/otel-collector-configmap-enhanced.yaml -n robot-shop2
   ```

2. **Restarted Deployment**:
   ```bash
   kubectl rollout restart deployment otel-collector -n robot-shop2
   ```

3. **Verified Rollout**:
   ```bash
   kubectl rollout status deployment otel-collector -n robot-shop2
   ```

## Verification

### Before Fixes
- Logs showed continuous errors every 30 seconds
- MongoDB: SSL handshake failures
- MySQL: Permission denied errors on 4+ tables
- Log volume: Extremely high (thousands of error lines)

### After Fixes
```bash
# No errors in logs
kubectl logs -n robot-shop2 otel-collector-5b95d7759f-xkt6m --tail=100 | grep -i error
# (no output - clean!)

# Metrics being exported successfully
kubectl logs -n robot-shop2 otel-collector-5b95d7759f-xkt6m --since=2m | grep 'MetricsExporter'
# Shows regular metric exports:
# - 12 resource metrics with 80 metrics and 170 data points (includes MySQL & MongoDB)
# - No error messages
```

### Current Status: ✅ RESOLVED

- MongoDB receiver: Successfully collecting metrics
- MySQL receiver: Successfully collecting performance_schema metrics
- Log volume: Normal (only info-level messages)
- Error rate: 0

## Important Notes

### MySQL Privilege Persistence
⚠️ **Note**: The MySQL privilege grants are applied to the running MySQL pod. If the MySQL pod is deleted or the database is reset, these grants will be lost and need to be reapplied.

**Solution for Persistence**: Add grants to MySQL initialization script:
- File: `mysql/scripts/30-otel-permissions.sql` (create new)
- Content:
  ```sql
  GRANT SELECT ON performance_schema.* TO 'shipping'@'%';
  GRANT PROCESS ON *.* TO 'shipping'@'%';
  FLUSH PRIVILEGES;
  ```
- This will auto-apply on MySQL container initialization

### MongoDB TLS in Production
⚠️ **Security Note**: In production environments, you should either:
1. Enable TLS on MongoDB and provide proper certificates to otel-collector, OR
2. Use network policies to ensure MongoDB is only accessible within the cluster

The current `insecure: true` configuration is acceptable for development/research but not recommended for production.

## Monitoring

To monitor collector health ongoing:

```bash
# Check for errors (should return empty)
kubectl logs -n robot-shop2 -l app=opentelemetry-collector --tail=100 | grep -i error

# Verify metric collection
kubectl logs -n robot-shop2 -l app=opentelemetry-collector --tail=50 | grep MetricsExporter

# Check resource metrics count
# Should see: "resource metrics": 12 (includes MongoDB + MySQL + other sources)
```

## References

- Configuration file: [K8s/helm/templates/otel-collector-configmap-enhanced.yaml](../K8s/helm/templates/otel-collector-configmap-enhanced.yaml)
- MySQL image: `robotshop/rs-mysql-db:latest`
- MongoDB image: (check deployment)
- OTel Collector version: 0.95.0

---

**Fixed by**: Claude Code Agent
**Context**: Anomaly detection research project in robot-shop2 namespace
