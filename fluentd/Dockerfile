FROM fluentd
USER root
RUN apt update && \
    apt install -y build-essential ruby-dev

RUN fluent-gem install fluent-plugin-elasticsearch && \
    fluent-gem install fluent-plugin-kubernetes_metadata_filter  && \
    fluent-gem install fluent-plugin-multi-format-parser

