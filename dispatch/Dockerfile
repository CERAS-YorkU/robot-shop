FROM golang:1.20

WORKDIR /go/src/app

COPY *.go .

# Initialize go module and add OpenTelemetry dependencies
RUN go mod init dispatch && \
    go get go.opentelemetry.io/otel@v1.21.0 && \
    go get go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracegrpc@v1.21.0 && \
    go get go.opentelemetry.io/otel/sdk@v1.21.0 && \
    go get go.opentelemetry.io/otel/bridge/opentracing@v1.21.0 && \
    go get github.com/opentracing/opentracing-go@v1.2.0 && \
    go get github.com/streadway/amqp@v1.0.0 && \
    go get github.com/instana/go-sensor@v1.49.0

RUN go install

CMD ["dispatch"]
