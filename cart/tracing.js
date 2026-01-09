const { NodeSDK } = require('@opentelemetry/sdk-node');
const { getNodeAutoInstrumentations } = require('@opentelemetry/auto-instrumentations-node');
const { OTLPTraceExporter } = require('@opentelemetry/exporter-trace-otlp-grpc');
const { Resource } = require('@opentelemetry/resources');
const { SemanticResourceAttributes } = require('@opentelemetry/semantic-conventions');
const { AsyncLocalStorageContextManager } = require('@opentelemetry/context-async-hooks');
const { W3CTraceContextPropagator } = require('@opentelemetry/core');

// Configure the OTLP exporter to send traces to the collector
const traceExporter = new OTLPTraceExporter({
  url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT || 'http://otel-collector:4317',
});

// Initialize the SDK with auto-instrumentations
const sdk = new NodeSDK({
  resource: new Resource({
    [SemanticResourceAttributes.SERVICE_NAME]: 'cart',
  }),
  traceExporter,
  // Context manager is critical for maintaining parent-child span relationships
  contextManager: new AsyncLocalStorageContextManager(),
  // W3C Trace Context propagator ensures trace context is propagated across services
  textMapPropagator: new W3CTraceContextPropagator(),
  instrumentations: [
    getNodeAutoInstrumentations({
      '@opentelemetry/instrumentation-http': {
        requestHook: (span, request) => {
          // Capture anomaly label headers for labeled dataset generation
          const headers = request.headers || {};
          if (headers['x-anomaly-type']) {
            span.setAttribute('http.request.header.x-anomaly-type', headers['x-anomaly-type']);
          }
          if (headers['x-anomaly-label']) {
            span.setAttribute('http.request.header.x-anomaly-label', headers['x-anomaly-label']);
          }
          if (headers['x-anomaly-root-cause']) {
            span.setAttribute('http.request.header.x-anomaly-root-cause', headers['x-anomaly-root-cause']);
          }
          if (headers['x-anomaly-msg']) {
            span.setAttribute('http.request.header.x-anomaly-msg', headers['x-anomaly-msg']);
          }
        },
      },
    }),
  ],
});

// Start the SDK
sdk.start();

// Gracefully shut down the SDK on process exit
process.on('SIGTERM', () => {
  sdk.shutdown()
    .then(() => console.log('Tracing terminated'))
    .catch((error) => console.log('Error terminating tracing', error))
    .finally(() => process.exit(0));
});
