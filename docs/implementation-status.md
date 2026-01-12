# Implementation Status - Anomaly Detection Dataset

**Last Updated**: 2026-01-09 15:08

---

## ✅ Completed Tasks

### 1. OpenTelemetry Collector Fixes
- **MongoDB SSL Issue**: Fixed TLS configuration in [otel-collector-configmap-enhanced.yaml](../K8s/helm/templates/otel-collector-configmap-enhanced.yaml)
- **MySQL Permissions**: Granted SELECT and PROCESS privileges for metrics collection
- **Status**: Logs are clean, no error flooding
- **Documentation**: [otel-collector-fixes.md](otel-collector-fixes.md)

### 2. Python Extraction Script Fixes
- **Grammar Error**: Fixed `exit()` → `sys.exit()` with proper import
- **JSON Parsing**: Rewrote to handle OpenTelemetry trace structure correctly
- **Timestamp Conversion**: Fixed string→int conversion for duration calculations
- **File**: [extract-labeled-dataset.py](../python-scripts/extract-labeled-dataset.py)

### 3. MSA Trace Extraction (CRITICAL FIX)
**Problem**: Script was only extracting 1 span per trace, missing all service relationships

**Solution**: Complete rewrite of `extract_trace_features()` to:
- Iterate through ALL resourceSpans (different services)
- Iterate through ALL scopeSpans within each resource
- Extract ALL spans with parent-child relationships

**Results**:
- **Before**: 651 rows (1 per trace)
- **After**: 1607 spans from 651 traces
- **Trace relationships**: 1069 root spans, 538 child spans
- **Documentation**: [msa-trace-analysis.md](msa-trace-analysis.md)

### 4. Timestamp Column Addition
**Feature**: Added human-readable timestamp as first column in CSV output

**Implementation**:
```python
# Convert nanoseconds to ISO 8601 timestamp
features['timestamp'] = datetime.fromtimestamp(start_time / 1_000_000_000).isoformat()
```

**Output Format**:
```csv
timestamp,start_time_ns,end_time_ns,duration_ns,duration_ms,service_name,trace_id,span_id,parent_span_id,...
2026-01-09T12:25:06.721000,1767979506721000000,1767979506725416048,4416048,4.416048,shipping,d2e25fe1...,4805715c...,,...
```

**Benefits**:
- Easy filtering by time windows
- Human-readable for analysis
- Preserves nanosecond precision in `start_time_ns`/`end_time_ns`

**Documentation**: [dataset-columns.md](dataset-columns.md)

### 5. Header Capture Implementation
**Purpose**: Capture anomaly labels from k6 HTTP headers

**Changes Made**:

#### Java Shipping Service
[shipping-deployment.yaml](../K8s/helm/templates/shipping-deployment.yaml:24-28)
```yaml
env:
- name: OTEL_INSTRUMENTATION_HTTP_CAPTURE_HEADERS_SERVER_REQUEST
  value: "x-anomaly-type,x-anomaly-label,x-anomaly-root-cause,x-anomaly-msg"
```

#### Node.js Services (Catalogue, User, Cart)
Added middleware to capture headers using Instana spans:
```javascript
const anomalyHeaders = ['x-anomaly-type', 'x-anomaly-label', 'x-anomaly-root-cause', 'x-anomaly-msg'];
anomalyHeaders.forEach(header => {
    const value = req.headers[header];
    if (value) {
        span.annotate(`http.request.header.${header}`, value);
    }
});
```

**Verification**:
- ✅ Headers reaching services (confirmed in logs)
- ✅ Services annotating spans
- ⚠️ **Pending**: Verify Instana forwards annotations to OpenTelemetry format

**Documentation**: [header-capture-verification.md](header-capture-verification.md)

---

## ⚠️ Pending Verification

### Header Propagation to OpenTelemetry Traces

**Current Status**: Implementation complete, awaiting verification

**Unknown**: Whether Instana's `span.annotate()` properly forwards custom attributes to OpenTelemetry exporters

**Verification Options**:

#### Option A: Jaeger UI (Recommended)
```bash
kubectl port-forward -n robot-shop2 svc/jaeger-query 16686:16686
# Open http://localhost:16686
# Search for traces from "catalogue" service
# Check for attributes: http.request.header.x-anomaly-type, etc.
```

#### Option B: Export and Analyze Traces
```bash
# Collect traces from collector
kubectl cp robot-shop2/<otel-collector-pod>:/var/log/otel/traces.json ./new_traces.json

# Run extraction script
python3 python-scripts/extract-labeled-dataset.py \
    --traces ./new_traces.json \
    --output ./data/dataset_test

# Check for anomalous labels
cat ./data/dataset_test/traces_labeled_*.csv | cut -d',' -f16-17 | sort | uniq -c
```

**Expected Result**:
```
Label distribution:
  normal: 1500
  anomalous: 107  <-- Should see this!
```

---

## 📊 Current Dataset Statistics

**File**: `data/dataset/traces_labeled_20260109_150835.csv`

```
Total spans: 1607
Unique traces: 1069

Service distribution:
  - shipping: 511 spans
  - catalogue: 392 spans
  - user: 368 spans
  - cart: 336 spans

Label distribution:
  - normal: 1607 (100%)
  - anomalous: 0 (0%)  ⚠️ Awaiting header capture verification

Span relationships:
  - Root spans (no parent): 1069
  - Child spans (has parent): 538
```

---

## 🎯 Next Steps

### 1. Verify Header Propagation
Choose one of the verification options above to confirm that anomaly labels are appearing in OpenTelemetry traces.

### 2. Run Full k6 Scenarios (After Verification)
```bash
k6 run k6-scripts/k6_optel_anomaly_labeled.js

# Wait for traces to be exported
sleep 60

# Extract dataset
python3 python-scripts/extract-labeled-dataset.py \
    --traces ./data/traces_full.json \
    --output ./data/dataset_full
```

### 3. Build ML Models
With properly labeled, multi-span traces:
- **Supervised Learning**: Train classifiers on `anomaly_label`
- **Sequence Models**: LSTMs on service call sequences
- **Graph Neural Networks**: On service dependency graphs
- **Anomaly Detection**: Autoencoders on normal traces

---

## 📁 Documentation Index

1. [otel-collector-fixes.md](otel-collector-fixes.md) - MongoDB/MySQL error fixes
2. [anomaly-labeling-issue.md](anomaly-labeling-issue.md) - Root cause analysis of missing labels
3. [header-capture-verification.md](header-capture-verification.md) - Header capture implementation
4. [msa-trace-analysis.md](msa-trace-analysis.md) - MSA distributed trace guide
5. [dataset-columns.md](dataset-columns.md) - CSV column reference
6. [implementation-status.md](implementation-status.md) - This file

---

## 🔧 Modified Files

### Python Scripts
- [python-scripts/extract-labeled-dataset.py](../python-scripts/extract-labeled-dataset.py)

### Kubernetes Deployments
- [K8s/helm/templates/otel-collector-configmap-enhanced.yaml](../K8s/helm/templates/otel-collector-configmap-enhanced.yaml)
- [K8s/helm/templates/shipping-deployment.yaml](../K8s/helm/templates/shipping-deployment.yaml)

### Node.js Services
- [catalogue/server.js](../catalogue/server.js:52-59)
- [user/server.js](../user/server.js:55-62)
- [cart/server.js](../cart/server.js:62-69)

---

**Summary**: All implementation tasks are complete. The dataset extraction script now properly captures all MSA spans with trace relationships and timestamps. The critical remaining task is to verify that anomaly headers are propagating through to OpenTelemetry traces via the Instana collector.
