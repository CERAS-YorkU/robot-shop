#
# Build
#
FROM debian:12 AS build

RUN apt-get update && apt-get -y install maven

WORKDIR /opt/shipping

COPY pom.xml /opt/shipping/
RUN mvn dependency:resolve
COPY src /opt/shipping/src/
RUN mvn package

#
# Run
#
FROM adoptopenjdk/openjdk8:latest

EXPOSE 8080

WORKDIR /opt/shipping

ENV CART_ENDPOINT=cart:8080
ENV DB_HOST=mysql
ENV OTEL_SERVICE_NAME=shipping
ENV OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318

# Download OpenTelemetry Java agent
ADD https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases/latest/download/opentelemetry-javaagent.jar /opt/shipping/opentelemetry-javaagent.jar

COPY --from=build /opt/shipping/target/shipping-1.0.jar shipping.jar

CMD [ "java", "-javaagent:/opt/shipping/opentelemetry-javaagent.jar", "-Xmn256m", "-Xmx768m", "-jar", "shipping.jar" ]

