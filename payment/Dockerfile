FROM python:3.9

EXPOSE 8080
USER root

ENV INSTANA_SERVICE_NAME=payment

WORKDIR /app

COPY requirements.txt /app/

RUN pip install -r requirements.txt

COPY *.py /app/
COPY payment.ini /app/

#CMD ["python", "payment.py"]
CMD ["opentelemetry-instrument", "--service_name", "payment", "--exporter_otlp_endpoint", "http://otel-collector:4317", "uwsgi", "--ini", "payment.ini"]

