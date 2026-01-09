# Anomaly Labeling Issue - Diagnosis and Solution

**Date**: 2026-01-09
**Namespace**: robot-shop2
**Issue**: All collected traces labeled as "normal" despite running k6 anomaly scenarios

---

## Problem Summary

You ran the k6 load test script `k6_optel_anomaly_labeled.js` which sends HTTP requests with anomaly labels in custom headers (`x-anomaly-type`, `x-anomaly-label`, etc.). However, all 651 collected traces show:
- `anomaly.label`: "normal"
- `anomaly.type`: "none"
- `anomaly.msg`: "baseline healthy traffic"

**Data Collection Period**: 85 minutes (12:25:06 - 13:50:06)
**Expected**: Mix of normal and anomalous traces
**Actual**: 100% normal traces

---

## Root Cause Analysis

### 1. ✅ k6 Script Configuration - CORRECT

The k6 script ([k6_optel_anomaly_labeled.js](../k6-scripts/k6_optel_anomaly_labeled.js)) is properly configured:

```javascript
// Sends headers correctly
'x-anomaly-type': ctx.type,
'x-anomaly-root-cause': ctx.root_cause,
'x-anomaly-label': ctx.label,
'x-anomaly-msg': ctx.msg,
```

Scenarios include:
- ✅ baseline (normal)
- ✅ latency_spike
- ✅ db_exhaustion
- ✅ cpu_saturation
- ✅ cache_miss
- ✅ dependency_bottleneck
- ✅ timeout
- ✅ error_spike

### 2. ✅ OpenTelemetry Collector Config - CORRECT

The OTel collector ([otel-collector-configmap-enhanced.yaml](../K8s/helm/templates/otel-collector-configmap-enhanced.yaml:74-86)) has a transform processor configured to extract headers:

```yaml
transform:
  trace_statements:
    - context: span
      statements:
        - set(attributes["anomaly.type"], attributes["http.request.header.x-anomaly-type"]) where ...
        - set(attributes["anomaly.root_cause"], attributes["http.request.header.x-anomaly-root-cause"]) where ...
        - set(attributes["anomaly.label"], attributes["http.request.header.x-anomaly-label"]) where ...
        - set(attributes["anomaly.msg"], attributes["http.request.header.x-anomaly-msg"]) where ...
        # Default values if headers missing:
        - set(attributes["anomaly.type"], "none") where attributes["anomaly.type"] == nil
        - set(attributes["anomaly.label"], "normal") where attributes["anomaly.label"] == nil
```

### 3. ❌ **SERVICE INSTRUMENTATION - MISSING HEADER CAPTURE**

**This is the root cause:**

The microservices (catalogue, shipping, user, cart, etc.) are **NOT configured to capture HTTP request headers** in their OpenTelemetry spans.

**Evidence from trace analysis:**
```python
# All 651 traces checked - Result:
Has x-anomaly headers: False  # <-- NO HTTP headers in ANY span
```

**What's happening:**

1. k6 sends HTTP request: `GET /products` with headers `x-anomaly-type: latency_spike`
2. Service (e.g., catalogue) receives the request
3. Service's OpenTelemetry instrumentation creates a span **BUT does not capture HTTP headers**
4. Span is sent to OTel collector without `http.request.header.x-anomaly-*` attributes
5. OTel collector's transform processor looks for these attributes, finds nothing
6. Transform processor sets default values: `anomaly.type = "none"`, `anomaly.label = "normal"`

---

## Solution Options

### Option 1: Configure Services to Capture HTTP Headers (Recommended)

Each service needs to be configured to capture custom HTTP request headers.

#### For Node.js Services (catalogue, user, cart)

Currently using Instana collector. Need to add OpenTelemetry instrumentation:

**Add to server.js (before requiring other modules):**
```javascript
const { NodeTracerProvider } = require('@opentelemetry/sdk-trace-node');
const { HttpInstrumentation } = require('@opentelemetry/instrumentation-http');
const { registerInstrumentations } = require('@opentelemetry/instrumentation');

registerInstrumentations({
  instrumentations: [
    new HttpInstrumentation({
      requestHook: (span, request) => {
        // Capture custom headers
        if (request.headers) {
          const anomalyHeaders = [
            'x-anomaly-type',
            'x-anomaly-label',
            'x-anomaly-root-cause',
            'x-anomaly-msg'
          ];

          anomalyHeaders.forEach(header => {
            const value = request.headers[header];
            if (value) {
              span.setAttribute(`http.request.header.${header}`, value);
            }
          });
        }
      }
    })
  ]
});
```

#### For Java Service (shipping)

Uses OpenTelemetry Java agent. Need to configure header capture via environment variables:

**Add to deployment YAML:**
```yaml
env:
  - name: OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST
    value: "x-anomaly-type,x-anomaly-label,x-anomaly-root-cause,x-anomaly-msg"
```

Or add to Java agent configuration file.

#### For Python Service (payment)

**Add custom span hook in your Flask app:**
```python
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from flask import request

def request_hook(span, environ):
    # Capture anomaly headers
    for header in ['x-anomaly-type', 'x-anomaly-label', 'x-anomaly-root-cause', 'x-anomaly-msg']:
        value = request.headers.get(header.replace('x-', 'X-'))
        if value:
            span.set_attribute(f'http.request.header.{header}', value)

FlaskInstrumentor().instrument_app(app, request_hook=request_hook)
```

#### For Go Service (dispatch)

**Add custom span attributes in HTTP middleware:**
```go
import (
    "go.opentelemetry.io/otel"
    "go.opentelemetry.io/otel/attribute"
)

func captureAnomalyHeaders(r *http.Request, span trace.Span) {
    headers := []string{
        "x-anomaly-type",
        "x-anomaly-label",
        "x-anomaly-root-cause",
        "x-anomaly-msg",
    }

    for _, header := range headers {
        if value := r.Header.Get(header); value != "" {
            span.SetAttributes(attribute.String("http.request.header."+header, value))
        }
    }
}
```

---

### Option 2: Use Baggage for Header Propagation (Alternative)

Instead of relying on HTTP header capture, use OpenTelemetry Baggage to propagate anomaly labels through the trace context.

**Pros**: Works automatically across service boundaries
**Cons**: Requires code changes in k6 or adding a proxy

---

### Option 3: Add Instrumentation at Nginx/Web Layer

Add header extraction logic at the web/nginx entry point to inject anomaly labels into trace context before reaching backend services.

**Pros**: Centralized, no changes to individual services
**Cons**: Requires Nginx OpenTelemetry module configuration

---

## Verification Steps

After implementing fixes:

1. **Restart services** to pick up new instrumentation:
   ```bash
   kubectl rollout restart deployment catalogue user cart shipping payment dispatch -n robot-shop2
   ```

2. **Send test request with header**:
   ```bash
   curl -H "x-anomaly-type: test" \
        -H "x-anomaly-label: anomalous" \
        http://<web-service>:8080/products
   ```

3. **Check traces for headers**:
   ```bash
   # Query Jaeger or check collector logs
   # Should see: http.request.header.x-anomaly-type = "test"
   ```

4. **Re-run k6 script**:
   ```bash
   k6 run k6-scripts/k6_optel_anomaly_labeled.js
   ```

5. **Verify dataset**:
   ```bash
   python3 python-scripts/extract-labeled-dataset.py \
       --traces ./data/traces.json \
       --output ./data/dataset

   # Should now show anomalous traces:
   # Label distribution:
   #   normal: 500
   #   anomalous: 150
   ```

---

## Current Data Status

**File**: `data/traces.json`
- Total traces: 651
- Time span: 85 minutes
- Services: shipping (485), catalogue (84), user (49), cart (33)
- **All labeled as "normal"** ⚠️

**This dataset is NOT usable for anomaly detection research** until the header capture issue is fixed.

---

## Next Steps

1. Choose solution approach (recommend Option 1 for Java shipping service as a POC)
2. Implement header capture for one service first
3. Test and verify headers appear in traces
4. Roll out to all services
5. Re-run k6 with full 15-minute scenario
6. Validate labeled dataset contains anomalous samples

---

## References

- OpenTelemetry HTTP semantic conventions: https://opentelemetry.io/docs/specs/semconv/http/
- Java agent header capture: https://opentelemetry.io/docs/instrumentation/java/automatic/agent-config/
- Node.js instrumentation hooks: https://opentelemetry.io/docs/instrumentation/js/instrumentation/

---

**Status**: Issue identified, awaiting implementation of header capture in service instrumentation.
