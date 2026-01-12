# Anomaly Detection Dataset Generation Setup

This guide explains how to configure OpenTelemetry to capture anomaly labels from k6 load tests and generate labeled datasets for anomaly detection research.

## Overview

The setup captures custom HTTP headers (`x-anomaly-*`) from k6 load tests and propagates them through the observability pipeline as span/metric attributes. This creates a labeled dataset with both normal and anomalous traffic samples.

## Architecture

```
k6 Load Generator (with anomaly labels)
    ↓ (HTTP headers: x-anomaly-type, x-anomaly-label, etc.)
Robot Shop Services (instrumented with OTEL)
    ↓ (OTLP protocol)
OpenTelemetry Collector
    ↓ (Transform processor extracts headers as attributes)
    ├─→ Jaeger (distributed tracing visualization)
    ├─→ Prometheus (real-time metrics)
    └─→ File Exporter (JSONL files for ML dataset)
         ↓
Python Script (extract-labeled-dataset.py)
    ↓
Labeled CSV Datasets (normal + anomalous)
```

## Components

### 1. k6 Load Generator with Anomaly Labels

Location: `/Users/ji/OtherProjects/k6-scripts/k6_optel_anomaly_labeled.js`

The k6 script defines 8 scenarios:
- **Baseline** (normal): Healthy traffic
- **Latency Spike**: Slow database queries
- **DB Exhaustion**: Connection pool saturation
- **CPU Saturation**: High CPU usage
- **Cache Miss Storm**: Cache key explosion
- **Dependency Bottleneck**: External service delays
- **Timeout**: Downstream service timeouts
- **Error Spike**: High 5xx error rates

Each scenario sends custom headers:
```javascript
'x-anomaly-type': 'latency_spike',
'x-anomaly-root-cause': 'slow_database_query',
'x-anomaly-label': 'anomalous',
'x-anomaly-msg': 'high latency caused by slow DB queries'
```

### 2. Enhanced OpenTelemetry Collector

Location: `K8s/helm/templates/otel-collector-configmap-enhanced.yaml`

**Key Features:**
- **Transform Processor**: Extracts HTTP headers as span attributes
- **Resource Processor**: Adds environment metadata
- **File Exporter**: Writes traces/metrics to JSONL files with rotation
- **Prometheus Exporter**: Real-time metrics endpoint
- **Persistent Storage**: 10GB PVC for dataset accumulation

**Extracted Attributes:**
```yaml
anomaly.type: "latency_spike" | "none"
anomaly.label: "anomalous" | "normal"
anomaly.root_cause: "slow_database_query" | "none"
anomaly.msg: "high latency caused by slow DB queries"
```

### 3. Dataset Extraction Script

Location: `scripts/extract-labeled-dataset.py`

Converts JSONL traces to ML-ready CSV datasets with features:
- Service name, trace/span IDs
- Duration (ns and ms)
- HTTP method, status code, target URL
- Anomaly labels (type, label, root_cause, msg)
- Network attributes
- Span kind and status

**Output Files:**
- `traces_labeled_TIMESTAMP.csv` - Full dataset
- `traces_normal_TIMESTAMP.csv` - Normal traffic only
- `traces_anomalous_TIMESTAMP.csv` - Anomalous traffic only
- `traces_{anomaly_type}_TIMESTAMP.csv` - Per-anomaly-type datasets

## Deployment Steps

### Step 1: Backup and Replace OTEL Configuration

```bash
cd /Users/ji/OtherProjects/robot-shop

# Backup existing files
cp K8s/helm/templates/otel-collector-configmap.yaml \
   K8s/helm/templates/otel-collector-configmap.yaml.backup

cp K8s/helm/templates/otel-collector-deployment.yaml \
   K8s/helm/templates/otel-collector-deployment.yaml.backup

# Replace with enhanced versions
mv K8s/helm/templates/otel-collector-configmap-enhanced.yaml \
   K8s/helm/templates/otel-collector-configmap.yaml

mv K8s/helm/templates/otel-collector-deployment-enhanced.yaml \
   K8s/helm/templates/otel-collector-deployment.yaml
```

### Step 2: Deploy Updated OTEL Collector

```bash
# Apply updated configuration to robot-shop2 namespace
kubectl apply -f K8s/helm/templates/otel-collector-configmap.yaml -n robot-shop2
kubectl apply -f K8s/helm/templates/otel-collector-deployment.yaml -n robot-shop2

# Wait for rollout
kubectl rollout status deployment/otel-collector -n robot-shop2

# Verify the new configuration
kubectl get pods -n robot-shop2 | grep otel-collector
kubectl logs -n robot-shop2 deployment/otel-collector --tail=50
```

### Step 3: Verify Persistent Volume

```bash
# Check PVC status
kubectl get pvc -n robot-shop2 | grep otel-logs

# Expected output:
# otel-logs-pvc   Bound    pvc-xxxxx   10Gi       RWO            local-path     1m
```

### Step 4: Update Web Service for Header Propagation

The Robot Shop web service (Nginx) needs to be configured to forward the anomaly headers to backend services. Check if headers are being forwarded:

```bash
# Get the web service pod
WEB_POD=$(kubectl get pods -n robot-shop2 -l service=web -o jsonpath='{.items[0].metadata.name}')

# Check Nginx configuration
kubectl exec -n robot-shop2 $WEB_POD -- cat /etc/nginx/nginx.conf | grep -A 5 proxy_set_header
```

**Note:** If headers aren't being forwarded, you may need to update the Nginx configuration to include:
```nginx
proxy_set_header x-anomaly-type $http_x_anomaly_type;
proxy_set_header x-anomaly-root-cause $http_x_anomaly_root_cause;
proxy_set_header x-anomaly-label $http_x_anomaly_label;
proxy_set_header x-anomaly-msg $http_x_anomaly_msg;
```

### Step 5: Run k6 Load Tests

```bash
cd /Users/ji/OtherProjects

# Get the web service endpoint
WEB_SERVICE=$(kubectl get svc web -n robot-shop2 -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# If LoadBalancer is pending, use NodePort
if [ -z "$WEB_SERVICE" ]; then
  NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')
  NODE_PORT=$(kubectl get svc web -n robot-shop2 -o jsonpath='{.spec.ports[0].nodePort}')
  WEB_SERVICE="$NODE_IP:$NODE_PORT"
fi

echo "Web Service: http://$WEB_SERVICE"

# Update k6 script BASE_URL
sed -i.backup "s|http://localhost:8080|http://$WEB_SERVICE|" k6-scripts/k6_optel_anomaly_labeled.js

# Run k6 load test (15 minutes total)
k6 run k6-scripts/k6_optel_anomaly_labeled.js

# Restore original
mv k6-scripts/k6_optel_anomaly_labeled.js.backup k6-scripts/k6_optel_anomaly_labeled.js
```

**k6 Timeline:**
- 0-2m: Baseline (normal)
- 2-4m: Latency spike
- 4-6m: DB exhaustion
- 6-8m: CPU saturation
- 8-10m: Cache miss storm
- 10-12m: Dependency bottleneck
- 12-14m: Timeout scenario
- 14-15m: Error spike

### Step 6: Extract Dataset from OTEL Collector

```bash
# Get the OTEL collector pod name
OTEL_POD=$(kubectl get pods -n robot-shop2 -l app=opentelemetry-collector -o jsonpath='{.items[0].metadata.name}')

# Check if trace files are being written
kubectl exec -n robot-shop2 $OTEL_POD -- ls -lh /var/log/otel/

# Copy trace files to local machine
kubectl cp robot-shop2/$OTEL_POD:/var/log/otel/traces.jsonl ./traces.jsonl
kubectl cp robot-shop2/$OTEL_POD:/var/log/otel/metrics.jsonl ./metrics.jsonl
```

### Step 7: Generate Labeled Datasets

```bash
# Install dependencies
pip install pandas

# Extract traces dataset
python3 scripts/extract-labeled-dataset.py \
  --traces ./traces.jsonl \
  --metrics ./metrics.jsonl \
  --output ./dataset

# View results
ls -lh dataset/
```

**Expected Output:**
```
dataset/
├── traces_labeled_20260109_120000.csv        # Full dataset
├── traces_normal_20260109_120000.csv         # Normal only
├── traces_anomalous_20260109_120000.csv      # Anomalous only
├── traces_latency_spike_20260109_120000.csv
├── traces_db_exhaustion_20260109_120000.csv
├── traces_cpu_saturation_20260109_120000.csv
├── traces_cache_miss_20260109_120000.csv
├── traces_dependency_bottleneck_20260109_120000.csv
├── traces_timeout_20260109_120000.csv
├── traces_error_spike_20260109_120000.csv
└── metrics_labeled_20260109_120000.csv
```

## Verification and Monitoring

### Check OTEL Collector Logs

```bash
# View collector logs for header extraction
kubectl logs -n robot-shop2 deployment/otel-collector --tail=100 -f | grep anomaly

# Check for transform processor activity
kubectl logs -n robot-shop2 deployment/otel-collector | grep "transform"
```

### Query Prometheus Metrics

```bash
# Port-forward Prometheus endpoint
kubectl port-forward -n robot-shop2 svc/otel-collector-prometheus 8889:8889

# In another terminal, query metrics
curl http://localhost:8889/metrics | grep robotshop
```

### View Traces in Jaeger

```bash
# Port-forward Jaeger UI
kubectl port-forward -n robot-shop2 svc/jaeger-query 16686:16686

# Open browser
open http://localhost:16686
```

Search for traces and look for tags:
- `anomaly.type`
- `anomaly.label`
- `anomaly.root_cause`
- `anomaly.msg`

## Dataset Features

### Trace Features
| Feature | Type | Description | Example |
|---------|------|-------------|---------|
| `trace_id` | string | Unique trace identifier | `a1b2c3d4...` |
| `span_id` | string | Unique span identifier | `e5f6g7h8...` |
| `service_name` | string | Service name | `web`, `cart`, `payment` |
| `duration_ns` | int | Span duration in nanoseconds | `1250000000` |
| `duration_ms` | float | Span duration in milliseconds | `1250.0` |
| `http_method` | string | HTTP method | `GET`, `POST` |
| `http_status_code` | int | HTTP status code | `200`, `500` |
| `http_target` | string | Request path | `/products`, `/checkout` |
| `anomaly_type` | string | Anomaly type | `latency_spike`, `none` |
| `anomaly_label` | string | Binary label | `normal`, `anomalous` |
| `anomaly_root_cause` | string | Root cause | `slow_database_query` |
| `anomaly_msg` | string | Description | `high latency caused by...` |
| `span_kind` | int | Span kind (0-5) | `1` (SERVER) |
| `span_status` | int | Status code | `0` (OK), `2` (ERROR) |

### Metric Features
- Service-level metrics (CPU, memory, request rate)
- Database metrics (MySQL, MongoDB connection pools, query times)
- Anomaly labels attached to each metric datapoint

## Continuous Collection

For ongoing dataset collection:

### Option 1: Scheduled k6 Runs (Cron)

```bash
# Create k6 job script
cat > run-k6-job.sh <<'EOF'
#!/bin/bash
WEB_SERVICE=$(kubectl get svc web -n robot-shop2 -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
k6 run -e BASE_URL=http://$WEB_SERVICE k6-scripts/k6_optel_anomaly_labeled.js
EOF

chmod +x run-k6-job.sh

# Add to crontab (run every 4 hours)
crontab -e
# 0 */4 * * * /path/to/run-k6-job.sh >> /var/log/k6-anomaly.log 2>&1
```

### Option 2: Kubernetes CronJob

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: k6-anomaly-generator
  namespace: robot-shop2
spec:
  schedule: "0 */4 * * *"  # Every 4 hours
  jobTemplate:
    spec:
      template:
        spec:
          containers:
          - name: k6
            image: grafana/k6:latest
            command: ["k6", "run", "/scripts/k6_optel_anomaly_labeled.js"]
            volumeMounts:
            - name: scripts
              mountPath: /scripts
          restartPolicy: OnFailure
          volumes:
          - name: scripts
            configMap:
              name: k6-scripts
```

### Option 3: Automated Dataset Extraction

```bash
# Create extraction script that runs in cluster
cat > extract-datasets.sh <<'EOF'
#!/bin/bash
OTEL_POD=$(kubectl get pods -n robot-shop2 -l app=opentelemetry-collector -o jsonpath='{.items[0].metadata.name}')
DATE=$(date +%Y%m%d)

# Copy files
kubectl cp robot-shop2/$OTEL_POD:/var/log/otel/traces.jsonl ./traces_$DATE.jsonl

# Extract dataset
python3 scripts/extract-labeled-dataset.py \
  --traces ./traces_$DATE.jsonl \
  --output ./dataset/$DATE

# Cleanup
rm ./traces_$DATE.jsonl
EOF

chmod +x extract-datasets.sh

# Run daily at midnight
crontab -e
# 0 0 * * * /path/to/extract-datasets.sh >> /var/log/dataset-extraction.log 2>&1
```

## Troubleshooting

### No Anomaly Labels in Traces

**Check 1: Headers reaching services**
```bash
WEB_POD=$(kubectl get pods -n robot-shop2 -l service=web -o jsonpath='{.items[0].metadata.name}')
kubectl logs -n robot-shop2 $WEB_POD --tail=100 | grep anomaly
```

**Check 2: OTEL transform processor**
```bash
kubectl logs -n robot-shop2 deployment/otel-collector | grep "transform"
```

**Check 3: Service instrumentation**
```bash
# Check if services are capturing HTTP headers
kubectl exec -n robot-shop2 deployment/cart -- env | grep OTEL
```

### File Exporter Not Writing

**Check PVC mount:**
```bash
OTEL_POD=$(kubectl get pods -n robot-shop2 -l app=opentelemetry-collector -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n robot-shop2 $OTEL_POD -- df -h /var/log/otel
kubectl exec -n robot-shop2 $OTEL_POD -- touch /var/log/otel/test.txt
```

**Check file permissions:**
```bash
kubectl exec -n robot-shop2 $OTEL_POD -- ls -la /var/log/otel/
```

### Empty or Malformed JSONL

**Validate JSONL syntax:**
```bash
kubectl exec -n robot-shop2 $OTEL_POD -- cat /var/log/otel/traces.jsonl | head -1 | jq .
```

**Check collector errors:**
```bash
kubectl logs -n robot-shop2 deployment/otel-collector | grep -i error
```

## Next Steps

1. **Train Anomaly Detection Models**: Use the labeled datasets with ML frameworks (scikit-learn, PyTorch, TensorFlow)

2. **Feature Engineering**: Extract additional features from traces:
   - Service dependency graphs
   - Request rate patterns
   - Error rate trends
   - P95/P99 latency percentiles

3. **Real-time Detection**: Deploy trained models as OTEL processors for live anomaly detection

4. **Expand Anomaly Types**: Add more scenarios to k6 script:
   - Memory leaks
   - Network partition
   - Resource exhaustion
   - Cascading failures

5. **Visualization**: Create dashboards showing:
   - Normal vs anomalous distribution
   - Anomaly type breakdown
   - Model prediction accuracy

## References

- [OpenTelemetry Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)
- [OTLP Transform Processor](https://github.com/open-telemetry/opentelemetry-collector-contrib/tree/main/processor/transformprocessor)
- [k6 Load Testing](https://k6.io/docs/)
- [Robot Shop Architecture](../CLAUDE.md)
