#!/bin/bash
set -e

echo "🚀 React project startup script"
cd /app

# Default Vite config content generator function
generate_vite_config() {
  local base_path_val="${WEB_SUBPATH:-/}" # Use WEB_SUBPATH, default to root if not set
  # Ensure base_path_val ends with a slash if it's not just "/"
  if [[ "$base_path_val" != "/" && "$base_path_val" != */ ]]; then
    base_path_val="${base_path_val}/"
  fi

  cat > vite.config.js << EOF
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '${base_path_val}',
  server: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    cors: true,
    allowedHosts: ['.lpachristian.com', 'localhost', 'all'],
    hmr: {
      // host: 'localhost',
      // protocol: 'ws'
    },
    watch: {
      usePolling: true
    },
    proxy: {},
    headers: {
      'Access-Control-Allow-Origin': '*'
    }
  },
  preview: {
    host: '0.0.0.0',
    port: 5173,
    strictPort: true,
    cors: true,
    headers: {
      'Access-Control-Allow-Origin': '*'
    }
  }
})
EOF
  echo "✅ Generated vite.config.js with base: '${base_path_val}' and CORS access control headers"
}

if [ ! -f "package.json" ]; then
  echo "📦 No package.json found. Setting up a new React (Vite) project..."
  # Create a new Vite+React project
  # Using 'y' to auto-confirm, and creating in current directory '.'
  echo "y" | npm create vite@latest . -- --template react
  generate_vite_config
  echo "✅ New React project created and configured."
else
  echo "📦 Found existing package.json, using existing project."
  if [ -f "vite.config.js" ]; then
    echo "🔧 Found vite.config.js. Ensuring critical settings..."
    cp vite.config.js vite.config.js.bak # Backup

    # This is a more robust way to update the vite.config.js file
    base_path_val="${WEB_SUBPATH:-/}"
    if [[ "$base_path_val" != "/" && "$base_path_val" != */ ]]; then
        base_path_val="${base_path_val}/"
    fi

    # Rather than trying complex sed operations, we'll create a temporary file with our desired config
    # and then check if we need to override the existing file
    generate_vite_config
    echo "✅ Updated vite.config.js with proper settings"
  else
    echo "📦 No vite.config.js found in existing project. Generating one..."
    generate_vite_config
  fi
fi

# Install dependencies if node_modules folder doesn't exist or package-lock.json is newer
if [ ! -d "node_modules" ] || ( [ -f "package-lock.json" ] && [ "package-lock.json" -nt "node_modules" ] ); then
  echo "📦 Installing dependencies..."
  npm install
else
  echo "✅ Dependencies seem up to date."
fi

# Force restart Vite server to apply configuration changes
if [ -f "node_modules/.vite/config-temp.json" ]; then
  echo "🔄 Clearing Vite cache to ensure config changes are applied..."
  rm -rf node_modules/.vite
fi

# Create a .env file to enhance Vite configuration
cat > .env << EOF
# Vite Environment Variables
VITE_BASE_URL=${WEB_SUBPATH:-/}
EOF
echo "✅ Created .env with important environment variables"

# Start the development server with supported CLI options
echo "🚀 Starting React development server on 0.0.0.0:5173 with base path '${WEB_SUBPATH:-/}'"
exec npm run dev -- --host 0.0.0.0 --strictPort --port 5173 --cors