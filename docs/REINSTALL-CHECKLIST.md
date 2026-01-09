# Quick Reinstall Checklist

**Before you delete the Helm chart, verify these fixes are in place:**

## ✅ Pre-Flight Checklist

### 1. OTel Collector MongoDB Fix
- [x] File: `K8s/helm/templates/otel-collector-configmap-enhanced.yaml`
- [x] Check lines 29-31 for TLS configuration:
  ```yaml
  tls:
    insecure: true
    insecure_skip_verify: true
  ```

### 2. MySQL OTel Permissions (NEW!)
- [x] File: `mysql/scripts/30-otel-permissions.sql` ← **NEWLY CREATED**
- [x] Content grants SELECT on performance_schema and PROCESS privilege
- [x] **MUST rebuild MySQL Docker image** for this to take effect

### 3. Nginx Header Propagation (UPDATED!)
- [x] File: `web/default.conf.template` ← **NEWLY UPDATED**
- [x] All `/api/*` locations have `proxy_set_header x-anomaly-*` directives
- [x] **MUST rebuild Web Docker image** for this to take effect

### 4. Shipping Service Header Capture
- [x] File: `K8s/helm/templates/shipping-deployment.yaml`
- [x] Check lines 25-28 for env vars

### 5. Node.js Services Header Capture
- [x] Files: `catalogue/server.js`, `user/server.js`, `cart/server.js`
- [x] All have `span.annotate()` code for anomaly headers

---

## 🔨 Rebuild Docker Images

**These must be rebuilt because source files changed:**

```bash
# 1. Rebuild MySQL (new init script)
cd mysql
docker build -t robotshop/rs-mysql-db:latest .

# 2. Rebuild Web (updated nginx config)
cd ../web
docker build -t robotshop/rs-web:latest .

# Optional: If using a registry, push them
# docker push robotshop/rs-mysql-db:latest
# docker push robotshop/rs-web:latest
```

---

## 🚀 Reinstall Steps

```bash
# 1. Delete existing deployment
helm uninstall robot-shop -n robot-shop2

# 2. Install fresh
helm install robot-shop --namespace robot-shop2 K8s/helm/

# 3. Wait for ready
kubectl get pods -n robot-shop2 -w
```

---

## ✅ Post-Install Verification

### Quick Test: OTel Collector Logs
```bash
# Should be clean (no errors)
kubectl logs -n robot-shop2 -l app=opentelemetry-collector --tail=100 | grep -i error
```

### Quick Test: MySQL Permissions
```bash
MYSQL_POD=$(kubectl get pods -n robot-shop2 -l service=mysql -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n robot-shop2 $MYSQL_POD -- mysql -u root -e "SHOW GRANTS FOR 'shipping'@'%';" | grep performance_schema
```

### Quick Test: Header Propagation
```bash
kubectl port-forward -n robot-shop2 svc/web 8080:8080 &
curl -H "x-anomaly-type: test" http://localhost:8080/api/catalogue/products
kubectl logs -n robot-shop2 -l service=catalogue --tail=5 | grep anomaly
```

---

## 📚 Full Guide

See [helm-reinstall-guide.md](helm-reinstall-guide.md) for detailed verification steps and troubleshooting.

---

## Summary

**2 NEW changes that require Docker rebuilds:**
1. ✨ `mysql/scripts/30-otel-permissions.sql` - Persists MySQL grants
2. ✨ `web/default.conf.template` - Propagates headers through Nginx

**3 EXISTING changes already in Helm chart:**
1. ✅ OTel collector MongoDB TLS fix
2. ✅ Shipping service header capture env vars
3. ✅ Node.js services header capture code

**After reinstall, you should have:**
- 🟢 Clean OTel collector logs (no MongoDB SSL or MySQL permission errors)
- 🟢 Headers propagating from k6 → Nginx → Services → OTel → Dataset
- 🟢 Both "normal" and "anomalous" labels in extracted datasets
