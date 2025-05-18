import os
import pathlib
import subprocess
import shutil
from typing import Dict, List, Optional, Tuple

class LaravelService:
    """
    Service to manage Laravel project detection and setup.
    This class provides utilities to scan a Laravel project directory,
    detect its configuration, and generate appropriate setup scripts.
    """
    
    def __init__(self, base_path: pathlib.Path):
        """Initialize the Laravel service with the base path to user projects."""
        self.base_path = base_path
    
    def detect_laravel_version(self, project_path: pathlib.Path) -> Optional[str]:
        """
        Detect the Laravel version by examining the composer.json file.
        
        Args:
            project_path: Path to the Laravel project directory
            
        Returns:
            Optional[str]: Laravel version or None if not detected
        """
        composer_json = project_path / "composer.json"
        if not composer_json.exists():
            return None
            
        # Use grep to extract laravel/framework version
        try:
            output = subprocess.check_output(
                ["grep", "-o", '"laravel/framework"\\s*:\\s*"\\^\\?[0-9]\\+\\.[0-9]\\+"', str(composer_json)],
                universal_newlines=True
            ).strip()
            
            # Extract version number
            if output:
                import re
                version_match = re.search(r'"(\^)?(\d+\.\d+)"', output)
                if version_match:
                    return version_match.group(2)
            return None
        except subprocess.CalledProcessError:
            return None
    
    def detect_nodejs_requirements(self, project_path: pathlib.Path) -> Dict[str, bool]:
        """
        Detect if the project requires Node.js by checking for package.json.
        
        Args:
            project_path: Path to the Laravel project directory
            
        Returns:
            Dict[str, bool]: Dictionary indicating if npm and build steps are needed
        """
        package_json = project_path / "package.json"
        result = {
            "needs_npm": package_json.exists(),
            "needs_build": False
        }
        
        if result["needs_npm"]:
            # Check if build script exists
            try:
                output = subprocess.check_output(
                    ["grep", "-o", '"build"\\s*:', str(package_json)],
                    universal_newlines=True
                ).strip()
                result["needs_build"] = bool(output)
            except subprocess.CalledProcessError:
                pass
                
        return result
    
    def detect_database_config(self, project_path: pathlib.Path) -> Dict[str, str]:
        """
        Detect database configuration from .env or .env.example file.
        
        Args:
            project_path: Path to the Laravel project directory
            
        Returns:
            Dict[str, str]: Database configuration
        """
        env_file = project_path / ".env"
        if not env_file.exists():
            env_file = project_path / ".env.example"
            if not env_file.exists():
                return {
                    "connection": "mysql",
                    "database": "laravel",
                    "username": "laravel_user",
                    "password": "laravel_password"
                }
        
        config = {
            "connection": "mysql",
            "database": "laravel",
            "username": "laravel_user",
            "password": "laravel_password"
        }
        
        # Parse .env file
        if env_file.exists():
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    if '=' in line:
                        key, value = line.split('=', 1)
                        if key == "DB_CONNECTION":
                            config["connection"] = value
                        elif key == "DB_DATABASE":
                            config["database"] = value
                        elif key == "DB_USERNAME":
                            config["username"] = value
                        elif key == "DB_PASSWORD":
                            config["password"] = value
        
        return config
    
    def generate_startup_script(self, 
                               username: str, 
                               webname: str, 
                               project_path: pathlib.Path) -> Tuple[str, Dict[str, str]]:
        """
        Generate a startup script based on the detected configuration.
        
        Args:
            username: Username
            webname: Web project name
            project_path: Path to the Laravel project directory
            
        Returns:
            Tuple[str, Dict[str, str]]: Startup script content and environment variables
        """
        laravel_version = self.detect_laravel_version(project_path)
        nodejs_reqs = self.detect_nodejs_requirements(project_path)
        db_config = self.detect_database_config(project_path)
        
        # Environment variables
        env_vars = {
            "DB_CONNECTION": db_config["connection"],
            "DB_DATABASE": db_config["database"],
            "DB_USERNAME": db_config["username"],
            "DB_PASSWORD": db_config["password"],
            "DB_HOST": f"{username}-{webname}-db",
            "APP_URL": f"https://{username}.lpachristian.com/{webname}",
            "ASSET_URL": f"https://{username}.lpachristian.com/{webname}",
            "VITE_ASSET_URL": f"/{webname}"
        }
        
        # Generate the script
        script = """#!/bin/bash
set -e

# Setup PHP and Apache
apt-get update -qq
apt-get install -y -qq libzip-dev zip curl git unzip > /dev/null
a2enmod rewrite
echo "ServerName ${HOSTNAME}" >> /etc/apache2/apache2.conf
docker-php-ext-install pdo_mysql zip > /dev/null
apt-get clean && rm -rf /var/lib/apt/lists/*

# Configure Apache virtual host
cat >/etc/apache2/sites-available/000-default.conf <<VHOST
<VirtualHost *:80>
  DocumentRoot /var/www/html/public

  <Directory /var/www/html/public>
      AllowOverride All
      Require all granted
      RewriteEngine On
      RewriteCond %{REQUEST_FILENAME} !-d
      RewriteCond %{REQUEST_FILENAME} !-f
      RewriteRule ^ index.php [L]
  </Directory>

  ErrorLog /var/log/apache2/error.log
  CustomLog /var/log/apache2/access.log combined
</VirtualHost>
VHOST

# Install Composer
curl -sS https://getcomposer.org/installer | php -- --install-dir=/usr/local/bin --filename=composer

cd /var/www/html

# Set up environment
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        cp .env.example .env
    else
        touch .env
    fi
fi

# Update environment variables
grep -q "^APP_URL=" .env && sed -i "s#^APP_URL=.*#APP_URL=${APP_URL}#" .env || echo "APP_URL=${APP_URL}" >> .env
grep -q "^ASSET_URL=" .env && sed -i "s#^ASSET_URL=.*#ASSET_URL=${ASSET_URL}#" .env || echo "ASSET_URL=${ASSET_URL}" >> .env
grep -q "^VITE_ASSET_URL=" .env && sed -i "s#^VITE_ASSET_URL=.*#VITE_ASSET_URL=${VITE_ASSET_URL}#" .env || echo "VITE_ASSET_URL=${VITE_ASSET_URL}" >> .env

# Database configuration
grep -q "^DB_CONNECTION=" .env && sed -i "s#^DB_CONNECTION=.*#DB_CONNECTION=${DB_CONNECTION}#" .env || echo "DB_CONNECTION=${DB_CONNECTION}" >> .env
grep -q "^DB_HOST=" .env && sed -i "s#^DB_HOST=.*#DB_HOST=${DB_HOST}#" .env || echo "DB_HOST=${DB_HOST}" >> .env
grep -q "^DB_DATABASE=" .env && sed -i "s#^DB_DATABASE=.*#DB_DATABASE=${DB_DATABASE}#" .env || echo "DB_DATABASE=${DB_DATABASE}" >> .env
grep -q "^DB_USERNAME=" .env && sed -i "s#^DB_USERNAME=.*#DB_USERNAME=${DB_USERNAME}#" .env || echo "DB_USERNAME=${DB_USERNAME}" >> .env
grep -q "^DB_PASSWORD=" .env && sed -i "s#^DB_PASSWORD=.*#DB_PASSWORD=${DB_PASSWORD}#" .env || echo "DB_PASSWORD=${DB_PASSWORD}" >> .env
"""

        # Add Composer and Laravel setup
        script += """
# Install dependencies with Composer if composer.json exists
if [ -f composer.json ]; then
    composer install --prefer-dist --no-interaction --optimize-autoloader
fi

# Check if vendor/autoload.php exists
if [ ! -f vendor/autoload.php ]; then
    echo "vendor/autoload.php missing, composer install failed or project is not properly configured"
    echo "Creating a new Laravel project if needed..."
    
    # Move existing files to backup directory
    mkdir -p /tmp/project_backup
    find . -maxdepth 1 -not -name "." -not -name "public" | xargs -I{} mv {} /tmp/project_backup/
    
    # Create new Laravel project
    composer create-project laravel/laravel . --prefer-dist
    
    # Copy back important user files
    if [ -d /tmp/project_backup/resources ]; then
        cp -r /tmp/project_backup/resources/* resources/ 2>/dev/null || true
    fi
    if [ -d /tmp/project_backup/public ]; then
        cp -r /tmp/project_backup/public/* public/ 2>/dev/null || true
    fi
    if [ -d /tmp/project_backup/database ]; then
        cp -r /tmp/project_backup/database/* database/ 2>/dev/null || true
    fi
fi

# Generate application key
php artisan key:generate --force

# Run migrations
php artisan migrate --force

# Clear and cache configuration
php artisan config:clear
php artisan config:cache
"""

        # Add Node.js setup if needed
        if nodejs_reqs["needs_npm"]:
            script += """
# Install Node.js if needed
if [ -f package.json ]; then
    apt-get update -qq
    apt-get install -y -qq nodejs npm > /dev/null
    npm install --loglevel error
"""
            if nodejs_reqs["needs_build"]:
                script += """
    # Run build process if it exists
    if grep -q "\\\"build\\\":" package.json; then
        npm run build --silent
    fi
"""
            script += "fi\n"

        # Add final permission setup and Apache start
        script += """
# Set proper permissions
chown -R www-data:www-data storage bootstrap/cache
chmod -R 775 storage bootstrap/cache

# Start Apache
exec apache2-foreground
"""
        
        return script, env_vars
    
    def create_startup_script(self, username: str, webname: str, target_dir: pathlib.Path) -> Dict[str, str]:
        """
        Create the startup script file for a Laravel project.
        
        Args:
            username: Username
            webname: Web project name
            target_dir: Target directory for the project
            
        Returns:
            Dict[str, str]: Environment variables for docker-compose
        """
        project_path = target_dir / "data"
        scripts_dir = target_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        # Generate the script
        script_content, env_vars = self.generate_startup_script(username, webname, project_path)
        
        # Write the script to file
        script_path = scripts_dir / "laravel_startup.sh"
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make the script executable
        script_path.chmod(0o755)
        
        return env_vars 