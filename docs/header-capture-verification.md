# Header Capture Implementation - Verification Report

**Date**: 2026-01-09
**Namespace**: robot-shop2

## Implementation Summary

### Changes Made

#### 1. Java Shipping Service
**File**: [K8s/helm/templates/shipping-deployment.yaml](../K8s/helm/templates/shipping-deployment.yaml:24-28)

Added environment variables to enable HTTP header capture:
```yaml
env:
- name: OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST
  value: "x-anomaly-type,x-anomaly-label,x-anomaly-root-cause,x-anomaly-msg"
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: "http://otel-collector:4317"
```

#### 2. Node.js Services (Catalogue, User, Cart)

**Files Modified**:
- [catalogue/server.js](../catalogue/server.js:52-59)
- [user/server.js](../user/server.js:55-62)
- [cart/server.js](../cart/server.js:62-69)

Added middleware to capture anomaly headers using Instana spans:
```javascript
// Capture anomaly headers for labeled dataset generation
const anomalyHeaders = ['x-anomaly-type', 'x-anomaly-label', 'x-anomaly-root-cause', 'x-anomaly-msg'];
anomalyHeaders.forEach(header => {
    const value = req.headers[header];
    if (value) {
        span.annotate(`http.request.header.${header}`, value);
    }
});
```

#### 3. Docker Images Rebuilt

```bash
✅ catalogue:latest - Built successfully
✅ user:latest - Built successfully
✅ cart:latest - Built successfully
```

#### 4. Deployments Restarted

```bash
✅ catalogue - Restarted and ready
✅ user - Restarted and ready
✅ cart - Restarted and ready
✅ shipping - Restarted (Java - long startup time)
```

---

## Verification Tests

### Test 1: HTTP Request with Anomaly Headers

**Command**:
```bash
curl -H "x-anomaly-type: test_anomaly" \
     -H "x-anomaly-label: anomalous" \
     -H "x-anomaly-root-cause: test_failure" \
     -H "x-anomaly-msg: testing header capture" \
     http://localhost:8080/api/catalogue/products
```

**Result**: ✅ **SUCCESS**
- Request completed successfully
- Response returned 200 OK with product data

### Test 2: Service Logs Verification

**Checked**: Catalogue service logs

**Result**: ✅ **HEADERS RECEIVED**

Log entry shows headers were successfully received by the service:
```json
{
  "level": "info",
  "req": {
    "method": "GET",
    "url": "/products",
    "headers": {
      "x-anomaly-type": "test_anomaly",
      "x-anomaly-label": "anomalous",
      "x-anomaly-root-cause": "test_failure",
      "x-anomaly-msg": "testing header capture"
    }
  },
  "msg": "request completed"
}
```

###Test 3: Multiple Requests Sent

**Test**: Sent 5 consecutive requests with anomaly headers

**Command**:
```bash
for i in {1..5}; do
  curl -H "x-anomaly-type: latency_spike" \
       -H "x-anomaly-label: anomalous" \
       -H "x-anomaly-root-cause: slow_database" \
       -H "x-anomaly-msg: simulated latency spike" \
       http://localhost:8080/api/catalogue/products
done
```

**Result**: ✅ **ALL REQUESTS SUCCESSFUL**

### Test 4: OpenTelemetry Collector Activity

**Checked**: OTel collector logs

**Result**: ✅ **TRACES BEING EXPORTED**
```
TracesExporter: resource spans: 1, spans: 1
TracesExporter: resource spans: 2, spans: 8
```

Collector is actively receiving and exporting traces.

---

## Current Status

### ✅ Completed
1. Source code modifications for header capture
2. Docker image rebuilds
3. Service deployments updated
4. HTTP headers successfully sent to services
5. Services receiving and logging headers

### ⚠️ Pending Verification

**Next Step**: Verify that the headers are being propagated through to OpenTelemetry traces

**Key Question**: Are the `span.annotate()` calls in Node.js services properly adding the headers as span attributes that OpenTelemetry can see?

**Potential Issue**: Instana collector may not be forwarding custom annotations to OpenTelemetry format

---

## Recommended Next Steps

### Option A: Verify with Jaeger UI

1. Port-forward to Jaeger:
   ```bash
   kubectl port-forward -n robot-shop2 svc/jaeger-query 16686:16686
   ```

2. Open Jaeger UI: http://localhost:16686

3. Search for traces from "catalogue" service

4. Inspect trace attributes for:
   - `http.request.header.x-anomaly-type`
   - `http.request.header.x-anomaly-label`
   - `http.request.header.x-anomaly-root-cause`
   - `http.request.header.x-anomaly-msg`

### Option B: Export and Analyze Traces

1. Collect traces from collector:
   ```bash
   kubectl cp robot-shop2/<otel-collector-pod>:/var/log/otel/traces.json ./new_traces.json
   ```

2. Run extraction script:
   ```bash
   python3 python-scripts/extract-labeled-dataset.py \
       --traces ./new_traces.json \
       --output ./data/dataset_test
   ```

3. Check for anomalous labels:
   ```bash
   # Should show mix of normal and anomalous
   cat ./data/dataset_test/traces_labeled_*.csv | cut -d',' -f9-10 | sort | uniq -c
   ```

### Option C: Switch to Native OpenTelemetry (If Instana Bridge Fails)

If Instana annotations aren't being forwarded, we need to:

1. Replace Instana collector with native OpenTelemetry SDK in Node.js services
2. Use OpenTelemetry HTTP instrumentation with `requestHook` to capture headers
3. Rebuild and redeploy

**Code Example**:
```javascript
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');

new HttpInstrumentation({
  requestHook: (span, request) => {
    const headers = ['x-anomaly-type', 'x-anomaly-label', 'x-anomaly-root-cause', 'x-anomaly-msg'];
    headers.forEach(header => {
      const value = request.headers[header];
      if (value) {
        span.setAttribute(`http.request.header.${header}`, value);
      }
    });
  }
});
```

---

## Summary

**Implementation**: ✅ Complete
**HTTP Headers**: ✅ Reaching services
**Service Logs**: ✅ Showing headers
**Trace Propagation**: ⚠️ **Needs Verification**

The critical unknown is whether Instana's `span.annotate()` properly forwards custom attributes to OpenTelemetry exporters. This requires checking actual trace data in Jaeger or exported trace files.

**Recommendation**: Proceed with **Option A (Jaeger UI)** or **Option B (Export traces)** to confirm end-to-end header propagation.

---

## Files Modified

1. `/Users/ji/OtherProjects/robot-shop/K8s/helm/templates/shipping-deployment.yaml`
2. `/Users/ji/OtherProjects/robot-shop/catalogue/server.js`
3. `/Users/ji/OtherProjects/robot-shop/user/server.js`
4. `/Users/ji/OtherProjects/robot-shop/cart/server.js`

---

**Next Action**: Verify header propagation in actual OpenTelemetry trace data.
