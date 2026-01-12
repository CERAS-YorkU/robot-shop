# MSA Distributed Trace Analysis Guide

**Date**: 2026-01-09
**Context**: Improved trace extraction for microservices architecture

---

## Understanding Distributed Traces in MSA

### Trace Structure Hierarchy

In a microservices architecture, a single user request creates a **distributed trace** that spans multiple services:

```
User Request → Web → Catalogue → [MongoDB]
                  ↓
                  → Cart → Redis
                  ↓
                  → User → MongoDB
                  ↓
                  → Shipping → MySQL
```

### OpenTelemetry Span Hierarchy

Each service call creates **spans** with relationships:

```
Trace ID: abc123 (unique per user request)
├── Span 1: web (span_id: s1, parent_span_id: "")       [ROOT]
    ├── Span 2: catalogue (span_id: s2, parent_span_id: s1)
    │   └── Span 3: mongodb query (span_id: s3, parent_span_id: s2)
    ├── Span 4: cart (span_id: s4, parent_span_id: s1)
    │   └── Span 5: redis get (span_id: s5, parent_span_id: s4)
    └── Span 6: user (span_id: s6, parent_span_id: s1)
        └── Span 7: mongodb query (span_id: s7, parent_span_id: s6)
```

**Key Fields:**
- `trace_id`: Same for all spans in this request flow (identifies the end-to-end transaction)
- `span_id`: Unique identifier for this specific service call
- `parent_span_id`: Points to the calling service's span_id (empty for root spans)

---

## Improved Extraction Script

### What Changed

**Before** ([old version](../python-scripts/extract-labeled-dataset.py)):
- Extracted only **1 span per trace** (first span found)
- Lost all service-to-service relationships
- No parent-child information
- Result: 651 rows (1 per trace file)

**After** ([improved version](../python-scripts/extract-labeled-dataset.py)):
- Extracts **ALL spans from each trace**
- Preserves parent-child relationships via `parent_span_id`
- Captures complete service call graph
- Result: 1607 rows (multiple spans per trace)

### New Features

#### 1. Span Identification Fields

```python
features['trace_id'] = span.get('traceId', '')         # Same for all spans in request
features['span_id'] = span.get('spanId', '')           # Unique per service call
features['parent_span_id'] = span.get('parentSpanId', '')  # Parent service
```

#### 2. Enhanced Span Details

```python
features['span_name'] = span.get('name', '')           # Operation name (e.g., "GET /products")
features['span_kind'] = span.get('kind', 0)            # 1=Internal, 2=Server, 3=Client, etc.
features['start_time_ns'] = start_time                 # Absolute timestamp
features['end_time_ns'] = end_time                     # Absolute timestamp
features['datacenter'] = ...                           # Custom tags
```

#### 3. Complete Service Coverage

The script now iterates through:
- All `resourceSpans` (different services in the trace)
- All `scopeSpans` within each resource
- All `spans` within each scope

This ensures **every service call** is captured.

---

## Dataset Output Analysis

### Current Dataset Results

From `/data/traces.json` (651 trace files):

```
Extracted: 1607 spans from 651 traces
Unique trace_ids: 1069
Service distribution:
  - shipping: 511 spans
  - catalogue: 392 spans
  - user: 368 spans
  - cart: 336 spans

Span relationships:
  - Root spans (no parent): 1069
  - Child spans (has parent): 538
```

### Why 1069 Unique Traces from 651 Files?

**OpenTelemetry Export Batching**: The OTel collector batches spans by service. A single trace spanning 3 services may be exported as 3 separate JSONL entries, each with the same `trace_id` but different `resourceSpans`.

**Example**:
```
File line 1: { trace_id: "abc", resourceSpans: [catalogue_spans] }
File line 2: { trace_id: "abc", resourceSpans: [cart_spans] }
File line 3: { trace_id: "abc", resourceSpans: [user_spans] }
```

The script correctly merges these by `trace_id`.

---

## CSV Output Structure

### Columns in `traces_labeled_*.csv`

| Column | Description | Example |
|--------|-------------|---------|
| `service_name` | Service that generated this span | "catalogue" |
| `trace_id` | End-to-end request ID | "d2e25fe1..." |
| `span_id` | This service call's ID | "4805715c..." |
| `parent_span_id` | Calling service's span_id | "be37d6b3..." or "" |
| `span_name` | Operation name | "GET /products" |
| `span_kind` | Type: 1=Internal, 2=Server, 3=Client | 2 |
| `start_time_ns` | Start timestamp (nanoseconds) | 1767979506721000000 |
| `end_time_ns` | End timestamp (nanoseconds) | 1767979506725416048 |
| `duration_ns` | Execution time (nanoseconds) | 4416048 |
| `duration_ms` | Execution time (milliseconds) | 4.416048 |
| `http_method` | HTTP method if applicable | "GET" |
| `http_status_code` | HTTP response code | 200 |
| `http_target` | Request path | "/products" |
| `anomaly_type` | Injected anomaly type | "latency_spike" |
| `anomaly_label` | Binary label | "anomalous" |
| `anomaly_root_cause` | Root cause label | "slow_database" |
| `anomaly_msg` | Description | "simulated latency spike" |
| `span_status` | OpenTelemetry status code | 0 (OK) |
| `datacenter` | Custom tag | "us-east-1" |

---

## Analyzing MSA Traces

### Example 1: Find Service Call Chains

```python
import pandas as pd

df = pd.read_csv('traces_labeled_20260109_150342.csv')

# Get a specific trace
trace_id = df['trace_id'].iloc[0]
trace_df = df[df['trace_id'] == trace_id]

# Build call tree
for _, row in trace_df.iterrows():
    indent = "  " if row['parent_span_id'] else ""
    print(f"{indent}{row['service_name']}: {row['span_name']} ({row['duration_ms']:.2f}ms)")
```

**Output:**
```
catalogue: GET /products (56.42ms)
  cart: tcp.connect (67.25ms)
  cart: GET (67.88ms)
```

### Example 2: Identify Bottlenecks

```python
# Find slowest spans by service
slow_spans = df.groupby('service_name')['duration_ms'].agg(['mean', 'max', 'std'])
print(slow_spans.sort_values('max', ascending=False))
```

### Example 3: Trace Critical Paths

```python
# Find traces that touched all 4 services
def get_trace_services(trace_id):
    return set(df[df['trace_id'] == trace_id]['service_name'])

full_traces = [tid for tid in df['trace_id'].unique()
               if len(get_trace_services(tid)) == 4]

print(f"Traces spanning all services: {len(full_traces)}")
```

### Example 4: Anomaly Propagation Analysis

When we have anomalous traces (after header capture fix):

```python
# Check if anomaly labels propagate through service calls
anomalous_traces = df[df['anomaly_label'] == 'anomalous']['trace_id'].unique()

for tid in anomalous_traces[:5]:
    trace = df[df['trace_id'] == tid]
    print(f"\nTrace {tid}:")
    print(trace[['service_name', 'anomaly_label', 'anomaly_type']].to_string(index=False))
```

---

## Machine Learning Features

### Feature Engineering for Anomaly Detection

#### Per-Span Features
- `duration_ms`: Response time
- `span_kind`: Service role
- `http_status_code`: Success/failure
- `datacenter`: Geographic distribution

#### Per-Trace Aggregations
```python
# Calculate trace-level features
trace_features = df.groupby('trace_id').agg({
    'duration_ms': ['sum', 'mean', 'max', 'std'],  # Latency stats
    'service_name': 'count',                        # Span count
    'span_status': lambda x: (x != 0).sum(),       # Error count
})
```

#### Graph Features
```python
# Build service dependency graph
edges = df[df['parent_span_id'] != ''].apply(
    lambda row: (row['parent_span_id'], row['span_id']), axis=1
)

# Count service transitions
transitions = df.groupby(['service_name', 'parent_span_id']).size()
```

---

## Next Steps for Labeled Dataset

### 1. Verify Header Capture

Once the header capture implementation is fully working:

```bash
# Send test request with anomaly headers
curl -H "x-anomaly-type: latency_spike" \
     -H "x-anomaly-label: anomalous" \
     http://localhost:8080/api/catalogue/products

# Wait for trace export
sleep 10

# Extract and check
python3 python-scripts/extract-labeled-dataset.py \
    --traces ./new_traces.json \
    --output ./test_dataset
```

**Expected**:
```
Label distribution:
  normal: 500
  anomalous: 50  <-- Should see this!
```

### 2. Run Full k6 Scenarios

```bash
k6 run k6-scripts/k6_optel_anomaly_labeled.js

# Collect traces after 15-minute run
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

## References

- **OpenTelemetry Trace Spec**: https://opentelemetry.io/docs/specs/otel/trace/api/
- **Span Context**: https://opentelemetry.io/docs/concepts/signals/traces/#span-context
- **MSA Observability Patterns**: Distributed tracing in microservices

---

**Key Takeaway**: The improved extraction script now captures the **complete service interaction graph**, enabling proper MSA anomaly detection research with trace-level and span-level features.
