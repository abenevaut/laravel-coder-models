#
# docker build -t laravel-coder-models . --no-cache
# docker run -it --rm -v $(pwd)/laravel-docs:/app/laravel-docs -v $(pwd)/laravel-docs-data:/app/laravel-docs-data laravel-coder-models
#
# docker run --rm --entrypoint php laravel-coder-models -v
# docker run --rm --entrypoint composer laravel-coder-models --version
# docker run --rm --entrypoint phpstan laravel-coder-models --version
#
FROM debian:bookworm-slim

# Ajoute le dépôt Sury pour PHP 8.3
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    gnupg2 \
    && curl -fsSL https://packages.sury.org/php/apt.gpg | gpg --dearmor -o /usr/share/keyrings/sury-php-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/sury-php-archive-keyring.gpg] https://packages.sury.org/php/ bookworm main" > /etc/apt/sources.list.d/sury-php.list \
    && rm -rf /var/lib/apt/lists/*

# Installe PHP 8.3 et ses extensions + Python 3.11
RUN apt-get update && apt-get install -y --no-install-recommends \
    php8.3-cli \
    php8.3-common \
    php8.3-mbstring \
    php8.3-xml \
    php8.3-zip \
    php8.3-curl \
    php8.3-gd \
    php8.3-opcache \
    php8.3-readline \
    php8.3-simplexml \
    php8.3-sqlite3 \
    python3.11 \
    python3-pip \
    python3.11-dev \
    git \
    unzip \
    wget \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Installe Composer
RUN php -r "copy('https://getcomposer.org/installer', 'composer-setup.php');" \
    && php composer-setup.php --install-dir=/usr/local/bin --filename=composer \
    && php -r "unlink('composer-setup.php');"

# Installe PHPStan
RUN mkdir -p /root/.composer \
    && composer global require --with-all-dependencies phpstan/phpstan:^1.10 \
    && cp -r /root/.composer/vendor/phpstan /usr/local/lib/ \
    && ln -s /usr/local/lib/phpstan/phpstan/phpstan /usr/local/bin/phpstan

# Installe les dépendances Python
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

# Copie le code source
COPY . .

# Utilisateur non-root
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# Volumes
VOLUME ["/app/laravel-docs", "/app/laravel-docs-data"]

# Point d'entrée
ENTRYPOINT ["python3", "laravel-docs-process/main.py"]
