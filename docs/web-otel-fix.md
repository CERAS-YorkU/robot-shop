# Web Service OpenTelemetry Fix - Missing Root Spans

**Date**: 2026-01-11
**Issue**: All spans in dataset have parent_span_id pointing to non-existent spans (8,023 orphaned spans)
**Root Cause**: Nginx web service not exporting traces due to protocol mismatch

---

## Problem Discovery

### Dataset Analysis Results

Running the trace relationship analysis on `traces_labeled_20260111_135320.csv` revealed:

```
Total spans: 25,542
Unique traces: 8,023
Root spans (no parent): 0 (0.0%)
Orphaned spans: 8,023 (31.4%)

Orphaned spans by service:
  - catalogue: 3,514
  - user: 2,439
  - cart: 2,070
```

**Key Finding**: **Zero root spans** - every span has a `parent_span_id`, but 31.4% point to span_ids that don't exist in the dataset.

### What This Means

In a distributed trace, the **web service** (Nginx) receives the initial HTTP request and should create the **root span**. Backend services (catalogue, user, cart) create child spans with `parent_span_id` pointing to the web span.

**Expected trace structure:**
```
web (span_id: abc123, parent_span_id: "")        ← ROOT SPAN
  ↳ catalogue (span_id: def456, parent_span_id: abc123)
      ↳ mongodb (span_id: ghi789, parent_span_id: def456)
```

**Actual in dataset:**
```
catalogue (span_id: def456, parent_span_id: abc123)  ← ORPHANED! abc123 doesn't exist
  ↳ mongodb (span_id: ghi789, parent_span_id: def456)
```

The web service spans are **completely missing** from the dataset.

---

## Root Cause

The web service Nginx container has the `nginx-otel` module properly built and loaded, but it's **failing to export traces** due to a **protocol mismatch**.

### Error in Web Service Logs

```
2026/01/11 18:52:32 [error] OTel export failure: failed to connect to all addresses;
last error: INTERNAL: Trying to connect an http1.x server
```

### Configuration Issue

**File**: [web/Dockerfile:70](../web/Dockerfile#L70)

**Before (INCORRECT)**:
```dockerfile
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
```

**Problem**: The nginx-otel module is built with **gRPC support** (see Dockerfile line 40: `-DWITH_OTLP_GRPC=ON`), which means it exports traces using the **OTLP gRPC protocol**.

However, it was configured to connect to port **4318**, which is the **OTLP HTTP/JSON** endpoint. This causes the gRPC client to fail with "Trying to connect an http1.x server".

### OpenTelemetry Collector Port Reference

| Port | Protocol | Use Case |
|------|----------|----------|
| **4317** | **OTLP gRPC** | Binary protocol, high performance |
| **4318** | **OTLP HTTP** | JSON/Protobuf over HTTP |

---

## Solution

### Fix Applied

**File**: [web/Dockerfile:70](../web/Dockerfile#L70)

**After (CORRECT)**:
```dockerfile
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
```

Changed port from `4318` (HTTP) to `4317` (gRPC) to match the nginx-otel module's protocol.

### Deployment Steps

```bash
# 1. Rebuild web service image
docker build -t robotshop/rs-web:latest ./web/

# 2. Push to registry (if using remote cluster)
docker push robotshop/rs-web:latest

# 3. Restart web deployment in Kubernetes
kubectl rollout restart deployment/web -n robot-shop2

# 4. Verify the fix
kubectl logs -n robot-shop2 deployment/web --tail=50 | grep -i otel

# Expected: No "OTel export failure" errors
# Expected: Successful "Configuring OpenTelemetry tracing with nginx-otel" message
```

### Verification

After redeployment, check that:

1. **No gRPC errors in web logs**:
   ```bash
   kubectl logs -n robot-shop2 deployment/web | grep "OTel export failure"
   # Should return nothing
   ```

2. **Traces exported to OTEL collector**:
   ```bash
   kubectl logs -n robot-shop2 deployment/otel-collector | grep "web"
   # Should see traces from web service
   ```

3. **Re-extract dataset and analyze**:
   ```bash
   # Get new traces
   kubectl cp robot-shop2/<otel-pod>:/var/log/otel/traces.json ./data/traces_new.json

   # Extract dataset
   python3 python-scripts/extract-labeled-dataset.py \
       --traces ./data/traces_new.json \
       --output ./data/dataset_new

   # Analyze relationships
   python3 python-scripts/analyze_trace_relationships.py \
       ./data/dataset_new/traces_labeled_*.csv
   ```

4. **Expected results after fix**:
   ```
   Total spans: ~30,000+ (includes web spans now)
   Root spans: ~8,000 (web service spans with no parent)
   Orphaned spans: 0 (or very few)

   Service distribution:
     - web: ~8,000 spans      ← NEW! These were missing before
     - catalogue: ~3,500 spans
     - user: ~2,500 spans
     - cart: ~2,000 spans
     - ...
   ```

---

## Technical Details

### Nginx-otel Module Configuration

The nginx-otel module is configured in [web/entrypoint.sh:48-84](../web/entrypoint.sh#L48-L84):

```nginx
load_module /usr/lib/nginx/modules/ngx_otel_module.so;

http {
    # OpenTelemetry configuration
    otel_exporter {
        endpoint http://otel-collector:4317;  # Now correct (gRPC)
    }

    otel_service_name web;
    otel_trace on;
}
```

### How nginx-otel Works

1. **Request arrives**: k6 sends HTTP request with anomaly headers to Nginx
2. **nginx-otel creates root span**:
   - Creates a new span with unique `span_id`
   - Sets `parent_span_id` to empty (root span)
   - Captures HTTP method, URL, headers (including x-anomaly-*)
3. **W3C Trace Context propagation**:
   - Adds `traceparent` header: `00-<trace_id>-<span_id>-01`
   - Forwards to backend service (catalogue, user, cart)
4. **Backend receives request**:
   - Reads `traceparent` header
   - Creates child span with `parent_span_id` = Nginx's `span_id`
   - Context manager maintains the relationship
5. **Export to collector**:
   - All services export to otel-collector:4317 via gRPC
   - Collector writes to `traces.json`

### Why This Was Missed Initially

The implementation history shows:

1. **Initial focus**: Capture anomaly labels from HTTP headers (docs show this was the primary goal)
2. **Nginx configuration**: Headers were properly propagated via `proxy_set_header` directives
3. **Backend instrumentation**: Node.js services were fixed to capture headers and propagate trace context
4. **Nginx OpenTelemetry**: The nginx-otel module was built and loaded, but export endpoint was misconfigured

The error logs showed gRPC connection failures, but they were buried in access logs and not immediately visible during initial testing.

---

## Impact on Anomaly Detection Research

### Before Fix

- **Incomplete traces**: Missing the entry point spans from web service
- **No true root spans**: All spans appear orphaned or disconnected
- **Limited analysis**: Cannot analyze full request flow from entry to backends
- **Parent-child relationships**: Only partial relationships between backend services

### After Fix

- **Complete distributed traces**: Full request flow from web → catalogue/user/cart → databases
- **Proper trace hierarchy**: Root spans from web service, child spans from backends
- **Enhanced features for ML**:
  - Full request latency (end-to-end from web entry)
  - Complete service dependency graphs
  - Accurate parent-child span relationships
  - Trace depth and breadth metrics
- **Better anomaly detection**:
  - Can identify if latency is at entry point vs downstream
  - Service-to-service call pattern analysis
  - Cascading failure detection

---

## Related Files

- [web/Dockerfile](../web/Dockerfile) - Nginx container with nginx-otel module
- [web/entrypoint.sh](../web/entrypoint.sh) - Configures nginx-otel at startup
- [web/default.conf.template](../web/default.conf.template) - Nginx proxy configuration
- [python-scripts/analyze_trace_relationships.py](../python-scripts/analyze_trace_relationships.py) - Analysis script that detected the issue
- [K8s/helm/templates/otel-collector-configmap.yaml](../K8s/helm/templates/otel-collector-configmap.yaml) - Collector configuration

---

## References

- **nginx-otel GitHub**: https://github.com/nginxinc/nginx-otel
- **OpenTelemetry OTLP Specification**: https://opentelemetry.io/docs/specs/otlp/
- **OTLP gRPC vs HTTP**: https://opentelemetry.io/docs/specs/otel/protocol/exporter/
- **W3C Trace Context**: https://www.w3.org/TR/trace-context/

---

**Status**: Fix applied to web/Dockerfile. Awaiting Docker rebuild and redeployment to verify complete trace collection.
