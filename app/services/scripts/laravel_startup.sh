#!/bin/bash
set -e

echo "Starting Laravel detection and setup..."

# Setup PHP and Apache
apt-get update -qq
apt-get install -y -qq libzip-dev zip curl git unzip libpng-dev libjpeg-dev libfreetype6-dev libicu-dev > /dev/null
a2enmod rewrite
echo "ServerName ${HOSTNAME}" >> /etc/apache2/apache2.conf
docker-php-ext-install pdo_mysql zip sockets gd intl bcmath pcntl exif opcache > /dev/null
apt-get clean && rm -rf /var/lib/apt/lists/*
cd /var/www/html${WEB_SUBPATH}

BASE_DIR="/var/www/html${WEB_SUBPATH}"        # → /var/www/html/lara9
PUBLIC_DIR="${BASE_DIR}/public"

cat >/etc/apache2/sites-available/000-default.conf <<VHOST
<VirtualHost *:80>
    ServerName christian.lpachristian.com

    DocumentRoot ${PUBLIC_DIR}
    <Directory ${PUBLIC_DIR}>
        AllowOverride All
        Require all granted
    </Directory>
    ErrorLog /var/log/apache2/error.log
    CustomLog /var/log/apache2/access.log combined
</VirtualHost>
VHOST

# Install Composer
curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

composer config --no-plugins allow-plugins."*" true



cd /var/www/html${WEB_SUBPATH}

# Detect Laravel project structure
echo "Detecting Laravel project..."

# Check if this is already a Laravel project
if [ -f composer.json ] && [ -f artisan ]; then
    echo "Existing Laravel project detected"
    LARAVEL_PROJECT=true
else
    echo "Not a standard Laravel project, will check further"
    LARAVEL_PROJECT=false
fi

# Set up environment file
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo "Copying .env.example to .env"
        cp .env.example .env
    else
        echo "Creating new .env file"
        touch .env
    fi
fi

# Update environment variables
echo "Configuring environment variables..."
grep -q "^APP_URL=" .env && sed -i "s#^APP_URL=.*#APP_URL=${BASE_URL}#" .env || echo "APP_URL=${BASE_URL}" >> .env
grep -q "^ASSET_URL=" .env && sed -i "s#^ASSET_URL=.*#ASSET_URL=${BASE_URL}#" .env || echo "ASSET_URL=${BASE_URL}" >> .env
grep -q "^VITE_ASSET_URL=" .env && sed -i "s#^VITE_ASSET_URL=.*#VITE_ASSET_URL=${WEB_SUBPATH}#" .env || echo "VITE_ASSET_URL=${WEB_SUBPATH}" >> .env

# Set URL prefix for Laravel if using subdirectory
if [ -n "${WEB_SUBPATH}" ]; then
    echo "Setting Laravel URL prefix to ${WEB_SUBPATH}"
    grep -q "^APP_SUBPATH=" .env && sed -i "s#^APP_SUBPATH=.*#APP_SUBPATH=${WEB_SUBPATH}#" .env || echo "APP_SUBPATH=${WEB_SUBPATH}" >> .env
fi

# Database configuration
echo "Configuring database..."
grep -q "^DB_CONNECTION=" .env && sed -i "s#^DB_CONNECTION=.*#DB_CONNECTION=mysql#" .env || echo "DB_CONNECTION=mysql" >> .env
grep -q "^DB_HOST=" .env && sed -i "s#^DB_HOST=.*#DB_HOST=${DB_HOST}#" .env || echo "DB_HOST=${DB_HOST}" >> .env
grep -q "^DB_DATABASE=" .env && sed -i "s#^DB_DATABASE=.*#DB_DATABASE=${DB_DATABASE}#" .env || echo "DB_DATABASE=${DB_DATABASE}" >> .env
grep -q "^DB_USERNAME=" .env && sed -i "s#^DB_USERNAME=.*#DB_USERNAME=${DB_USERNAME}#" .env || echo "DB_USERNAME=${DB_USERNAME}" >> .env
grep -q "^DB_PASSWORD=" .env && sed -i "s#^DB_PASSWORD=.*#DB_PASSWORD=${DB_PASSWORD}#" .env || echo "DB_PASSWORD=${DB_PASSWORD}" >> .env

# If composer.json exists, install dependencies
if [ -f composer.json ]; then
    echo "Installing Composer dependencies..."
    composer install --prefer-dist --no-interaction --optimize-autoloader

    composer dump-autoload -o
    
fi

# If not a Laravel project or missing vendor, create new one but preserve user files
if [ "$LARAVEL_PROJECT" = false ] || [ ! -f vendor/autoload.php ]; then
    echo "Laravel project setup needed - creating or fixing project..."
    
    # Backup existing files if any
    mkdir -p /tmp/user_files
    
    # Save public directory if it exists
    if [ -d public ]; then
        mkdir -p /tmp/user_files/public
        cp -r public/* /tmp/user_files/public/ 2>/dev/null || true
    fi
    
    # Save resources directory if it exists
    if [ -d resources ]; then
        mkdir -p /tmp/user_files/resources
        cp -r resources/* /tmp/user_files/resources/ 2>/dev/null || true
    fi
    
    # Save database migrations if they exist
    if [ -d database ]; then
        mkdir -p /tmp/user_files/database
        cp -r database/* /tmp/user_files/database/ 2>/dev/null || true
    fi
    
    # Save .env file if it exists
    if [ -f .env ]; then
        cp .env /tmp/user_files/
    fi
    
    # Clear everything except public folder temporarily
    find . -mindepth 1 -not -name "public" -not -path "./public/*" -exec rm -rf {} +
    
    # Create new Laravel project
    echo "Creating new Laravel project..."
    composer create-project --prefer-dist laravel/laravel . --no-interaction
    
    # Restore user files
    echo "Restoring user files..."
    if [ -d /tmp/user_files/public ]; then
        cp -r /tmp/user_files/public/* public/ 2>/dev/null || true
    fi
    
    if [ -d /tmp/user_files/resources ]; then
        cp -r /tmp/user_files/resources/* resources/ 2>/dev/null || true
    fi
    
    if [ -d /tmp/user_files/database ]; then
        cp -r /tmp/user_files/database/* database/ 2>/dev/null || true
    fi
    
    # Restore environment variables from backed up .env
    if [ -f /tmp/user_files/.env ]; then
        # Extract important values from old .env
        APP_KEY=$(grep "^APP_KEY=" /tmp/user_files/.env | cut -d '=' -f2)
        
        # If there's an APP_KEY, use it
        if [ ! -z "$APP_KEY" ]; then
            sed -i "s/^APP_KEY=.*/APP_KEY=$APP_KEY/" .env
        fi
    fi
    
    # Update environment variables again to ensure they're set correctly
    grep -q "^APP_URL=" .env && sed -i "s#^APP_URL=.*#APP_URL=${BASE_URL}#" .env || echo "APP_URL=${BASE_URL}" >> .env
    grep -q "^ASSET_URL=" .env && sed -i "s#^ASSET_URL=.*#ASSET_URL=${BASE_URL}#" .env || echo "ASSET_URL=${BASE_URL}" >> .env
    grep -q "^VITE_ASSET_URL=" .env && sed -i "s#^VITE_ASSET_URL=.*#VITE_ASSET_URL=${WEB_SUBPATH}#" .env || echo "VITE_ASSET_URL=${WEB_SUBPATH}" >> .env
    
    # Clean up temp files
    rm -rf /tmp/user_files
fi

# Generate application key if needed
if ! grep -q "^APP_KEY=...." .env; then
    echo "Generating application key..."
    php artisan key:generate --force
fi

# Run migrations
echo "Running database migrations..."
php artisan migrate --force || echo "Migration failed, but continuing..."

# Clear and cache configuration
echo "Optimizing Laravel configuration..."
php artisan config:clear
php artisan config:cache

# Configure URL handling for subdirectory
if [ -n "${WEB_SUBPATH}" ] && [ -d "app/Providers" ]; then
    echo "Configuring Laravel URL handling for subdirectory ${WEB_SUBPATH}..."
    cat > app/Providers/AppServiceProvider.php <<EOF
<?php

namespace App\Providers;

use Illuminate\Support\ServiceProvider;
use Illuminate\Support\Facades\URL; // Asegúrate que esto esté importado

class AppServiceProvider extends ServiceProvider
{
    /**
     * Register any application services.
     */
    public function register(): void
    {
        //
    }

    /**
     * Bootstrap any application services.
     */
    public function boot(): void
    {
        // Si APP_URL está configurado correctamente en .env para incluir el subdirectorio
        // (ej. http://dominio.com/lara13), el generador de URLs de Laravel debería funcionar bien.
        // Forzarlo aquí puede ser útil para comandos de consola o workers.
        // La variable 'APP_SUBPATH' es una costumbre tuya, puedes basarte en ella o
        // directamente en si la URL configurada tiene un path.
        if (env('APP_SUBPATH') || !empty(parse_url(config('app.url'), PHP_URL_PATH))) {
            URL::forceRootUrl(config('app.url'));
        }

        // NO USAR: URL::defaults(['prefix' => env('APP_SUBPATH')]);
        // Esto causaría que las rutas definidas como Route::get('login',...)
        // se esperen en /lara13/lara13/login si APP_URL ya es http://.../lara13
    }
}
EOF
    echo "AppServiceProvider updated for subdirectory handling"
fi

# Check for Node.js requirements
if [ -f package.json ]; then
    echo "Node.js package.json detected, installing Node dependencies..."
    apt-get update -qq
    apt-get install -y -qq nodejs npm > /dev/null
    npm install --loglevel error
    
    # Check if build script exists
    if grep -q "\"build\":" package.json; then
        echo "Running npm build process..."
        npm run build --silent
    fi
fi

# Set proper permissions
echo "Setting file permissions..."
chown -R www-data:www-data storage bootstrap/cache
chmod -R 775 storage bootstrap/cache


# ─────────────────────────────────────────────────────────────────
# Crear .htaccess para que cualquier petición a /laravel30/ redirija a public/
# ─────────────────────────────────────────────────────────────────
echo "Configurando .htaccess para RewriteBase / (ya que DocumentRoot apunta a public/ del subproyecto)..."
cat > "${PUBLIC_DIR}/.htaccess" <<HTACCESS
<IfModule mod_rewrite.c>
    <IfModule mod_negotiation.c>
        Options -MultiViews -Indexes
    </IfModule>

    RewriteEngine On

    # Establecer RewriteBase a / porque DocumentRoot ya apunta a este directorio (o a su padre si es alias)
    # En tu caso, DocumentRoot es /var/www/html/lara13/public, así que RewriteBase es /
    RewriteBase /

    # Manejar solicitudes de activos de Vite directamente si existen
    RewriteCond %{REQUEST_URI} ^/build/
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteRule ^(.*)$ index.php [L]

    # Si no es un archivo ni un directorio, pásalo a index.php
    RewriteCond %{REQUEST_FILENAME} !-d
    RewriteCond %{REQUEST_FILENAME} !-f
    RewriteRule ^ index.php [L]
</IfModule>
HTACCESS
chown www-data:www-data "${PUBLIC_DIR}/.htaccess"
chmod 644 "${PUBLIC_DIR}/.htaccess"
echo "Laravel setup complete! Starting Apache..."
# Start Apache
exec apache2-foreground 