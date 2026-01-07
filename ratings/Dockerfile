#
# Build the app
#
FROM php:8.1-apache

RUN apt-get update && apt-get install -yqq unzip libzip-dev git \
    && docker-php-ext-install pdo_mysql opcache zip

# Install OpenTelemetry PHP extension
RUN pecl install opentelemetry-1.0.0 \
    && docker-php-ext-enable opentelemetry

# Enable AutoProfile for PHP which is currently opt-in beta
RUN echo "instana.enable_auto_profile=1" > "/usr/local/etc/php/conf.d/zzz-instana-extras.ini"

# Configure OpenTelemetry
RUN echo "extension=opentelemetry.so" > "/usr/local/etc/php/conf.d/opentelemetry.ini" && \
    echo "otel.service.name=ratings" >> "/usr/local/etc/php/conf.d/opentelemetry.ini" && \
    echo "otel.traces.exporter=otlp" >> "/usr/local/etc/php/conf.d/opentelemetry.ini" && \
    echo "otel.exporter.otlp.endpoint=http://otel-collector:4318" >> "/usr/local/etc/php/conf.d/opentelemetry.ini"

# relax permissions on status
COPY status.conf /etc/apache2/mods-available/status.conf
# Enable Apache mod_rewrite and status
RUN a2enmod rewrite && a2enmod status

WORKDIR /var/www/html

COPY html/ /var/www/html

COPY --from=composer /usr/bin/composer /usr/bin/composer
RUN composer install

# This is important. Symfony needs write permissions and we
# dont know the context in which the container will run, i.e.
# which user will be forced from the outside so better play
# safe for this simple demo.
RUN rm -Rf /var/www/var/*
RUN chown -R www-data /var/www
RUN chmod -R 777 /var/www

