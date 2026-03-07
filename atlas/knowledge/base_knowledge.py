"""Base knowledge entries for ATLAS.

Pre-populated deployment guides and platform knowledge.
"""

from datetime import datetime

BASE_KNOWLEDGE = [
    # ==========================================================================
    # iOS Platform
    # ==========================================================================
    {
        "id": "ios-deployment",
        "title": "iOS App Store Deployment Guide",
        "category": "deployment",
        "platform": "ios",
        "tags": ["ios", "app store", "apple", "deployment", "mobile"],
        "prerequisites": [
            "Apple Developer Account ($99/year)",
            "Xcode installed",
            "Valid signing certificate",
            "App Store Connect account",
        ],
        "commands": [
            "xcodebuild -scheme MyApp -configuration Release archive",
            "xcodebuild -exportArchive -archivePath MyApp.xcarchive -exportPath ./build -exportOptionsPlist ExportOptions.plist",
            "xcrun altool --upload-app -f MyApp.ipa -t ios -u EMAIL -p APP_SPECIFIC_PASSWORD",
        ],
        "content": """# iOS App Store Deployment

## Prerequisites
1. **Apple Developer Account** - Enroll at developer.apple.com ($99/year)
2. **Xcode** - Latest version from Mac App Store
3. **Certificates & Provisioning** - Create in Apple Developer Portal

## Step-by-Step Deployment

### 1. Prepare Your App
```bash
# Clean build folder
xcodebuild clean -project MyApp.xcodeproj -scheme MyApp

# Archive for release
xcodebuild -scheme MyApp -configuration Release archive -archivePath ./build/MyApp.xcarchive
```

### 2. Create App in App Store Connect
1. Go to appstoreconnect.apple.com
2. Click "My Apps" → "+" → "New App"
3. Fill in: Name, Primary Language, Bundle ID, SKU

### 3. Prepare App Store Listing
- **Screenshots**: Required sizes for each device
  - iPhone 6.7" (1290 x 2796)
  - iPhone 6.5" (1284 x 2778)
  - iPad Pro 12.9" (2048 x 2732)
- **App Description**: Up to 4000 characters
- **Keywords**: 100 characters max
- **Privacy Policy URL**: Required
- **Support URL**: Required

### 4. Export and Upload
```bash
# Export IPA
xcodebuild -exportArchive \\
  -archivePath ./build/MyApp.xcarchive \\
  -exportPath ./build \\
  -exportOptionsPlist ExportOptions.plist

# Upload via Transporter app or altool
xcrun altool --upload-app -f ./build/MyApp.ipa -t ios \\
  -u your@email.com -p @keychain:AC_PASSWORD
```

### 5. Submit for Review
1. Select build in App Store Connect
2. Complete App Information
3. Answer Export Compliance questions
4. Submit for Review (typically 24-48 hours)

## Common Issues
- **Code Signing**: Ensure certificates match provisioning profiles
- **Icon Missing**: Include all required icon sizes in Assets.xcassets
- **Privacy**: Add all required usage descriptions to Info.plist

## Timeline
- Review: 24-48 hours (can be longer for first submission)
- After approval: Live within 24 hours
""",
        "source": "Apple Developer Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # Android Platform
    # ==========================================================================
    {
        "id": "android-deployment",
        "title": "Google Play Store Deployment Guide",
        "category": "deployment",
        "platform": "android",
        "tags": ["android", "google play", "deployment", "mobile", "aab"],
        "prerequisites": [
            "Google Play Developer Account ($25 one-time)",
            "Android Studio",
            "Signed release keystore",
        ],
        "commands": [
            "./gradlew bundleRelease",
            "jarsigner -keystore my-release-key.jks app-release.aab alias_name",
            "bundletool build-apks --bundle=app.aab --output=app.apks",
        ],
        "content": """# Google Play Store Deployment

## Prerequisites
1. **Google Play Developer Account** - Register at play.google.com/console ($25 one-time)
2. **Android Studio** - Latest version
3. **Signing Key** - Generate a release keystore

## Step-by-Step Deployment

### 1. Generate Signing Key
```bash
keytool -genkey -v -keystore my-release-key.jks \\
  -keyalg RSA -keysize 2048 -validity 10000 \\
  -alias my-key-alias
```

### 2. Configure Build
In `app/build.gradle`:
```groovy
android {
    signingConfigs {
        release {
            storeFile file("my-release-key.jks")
            storePassword System.getenv("KEYSTORE_PASSWORD")
            keyAlias "my-key-alias"
            keyPassword System.getenv("KEY_PASSWORD")
        }
    }
    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled true
            proguardFiles getDefaultProguardFile('proguard-android.txt')
        }
    }
}
```

### 3. Build Release Bundle (AAB)
```bash
# Build Android App Bundle (required by Google Play)
./gradlew bundleRelease

# Output: app/build/outputs/bundle/release/app-release.aab
```

### 4. Create App in Play Console
1. Go to play.google.com/console
2. Click "Create app"
3. Fill in: App name, Default language, App type

### 5. Prepare Store Listing
- **Screenshots**: Min 2, max 8 per device type
  - Phone: 320-3840px width
  - Tablet: 1080-7680px width
- **Feature Graphic**: 1024 x 500px
- **Short Description**: 80 characters
- **Full Description**: 4000 characters
- **Privacy Policy URL**: Required

### 6. Upload and Release
1. Go to Production → Create new release
2. Upload AAB file
3. Add release notes
4. Review and roll out

## Common Issues
- **64-bit Requirement**: Must include arm64-v8a libraries
- **Target API Level**: Must target recent Android API (currently 33+)
- **App Signing**: Google manages signing by default (App Signing by Google Play)

## Timeline
- Initial review: 3-7 days (first submission)
- Updates: Usually < 24 hours
""",
        "source": "Google Play Developer Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # React/Web Platform
    # ==========================================================================
    {
        "id": "react-deployment",
        "title": "React Web App Deployment Guide",
        "category": "deployment",
        "platform": "web",
        "tags": ["react", "web", "vercel", "netlify", "deployment", "frontend"],
        "prerequisites": [
            "Node.js 18+",
            "npm or yarn",
            "Git repository",
        ],
        "commands": [
            "npm run build",
            "npx vercel deploy --prod",
            "npx netlify deploy --prod --dir=build",
        ],
        "content": """# React Web App Deployment

## Prerequisites
1. **Node.js** - Version 18 or higher
2. **Package Manager** - npm or yarn
3. **Git** - For version control and CI/CD

## Build for Production
```bash
# Create optimized production build
npm run build

# Output: build/ directory with static files
```

## Deployment Options

### Option 1: Vercel (Recommended)
```bash
# Install Vercel CLI
npm i -g vercel

# Deploy
vercel deploy --prod

# Or connect GitHub for automatic deploys
# 1. Go to vercel.com
# 2. Import your repository
# 3. Vercel auto-detects React and configures build
```

### Option 2: Netlify
```bash
# Install Netlify CLI
npm i -g netlify-cli

# Deploy
netlify deploy --prod --dir=build

# Or drag-and-drop build folder at app.netlify.com
```

### Option 3: GitHub Pages
```bash
# Install gh-pages
npm install gh-pages --save-dev

# Add to package.json
"homepage": "https://username.github.io/repo-name",
"scripts": {
  "predeploy": "npm run build",
  "deploy": "gh-pages -d build"
}

# Deploy
npm run deploy
```

### Option 4: AWS S3 + CloudFront
```bash
# Build
npm run build

# Sync to S3
aws s3 sync build/ s3://your-bucket-name --delete

# Invalidate CloudFront cache
aws cloudfront create-invalidation --distribution-id XXXXX --paths "/*"
```

## Environment Variables
```bash
# Create .env.production
REACT_APP_API_URL=https://api.yourapp.com
REACT_APP_GA_ID=UA-XXXXXXXX

# These are embedded at build time
```

## Performance Checklist
- [ ] Enable gzip/brotli compression
- [ ] Set cache headers for static assets
- [ ] Use CDN for global distribution
- [ ] Enable HTTPS
- [ ] Add service worker for offline support

## Common Issues
- **Routing**: For SPA routing, configure redirects to index.html
- **Environment Variables**: Must start with REACT_APP_
- **Build Failures**: Check Node version matches local development
""",
        "source": "React Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # Python Backend
    # ==========================================================================
    {
        "id": "python-deployment",
        "title": "Python Backend Deployment Guide",
        "category": "deployment",
        "platform": "python",
        "tags": ["python", "django", "fastapi", "flask", "backend", "docker"],
        "prerequisites": [
            "Python 3.9+",
            "pip or poetry",
            "Docker (optional)",
        ],
        "commands": [
            "pip install gunicorn",
            "gunicorn app:app --workers 4 --bind 0.0.0.0:8000",
            "docker build -t myapp . && docker run -p 8000:8000 myapp",
        ],
        "content": """# Python Backend Deployment

## Prerequisites
1. **Python** - Version 3.9 or higher
2. **Dependencies** - requirements.txt or pyproject.toml
3. **Production Server** - Gunicorn, Uvicorn, etc.

## Production Setup

### Create requirements.txt
```bash
pip freeze > requirements.txt

# Or with production dependencies
# requirements/prod.txt:
gunicorn==21.2.0
uvicorn[standard]==0.24.0
```

### FastAPI with Uvicorn
```bash
# Install
pip install uvicorn[standard] gunicorn

# Run with Gunicorn + Uvicorn workers
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### Django with Gunicorn
```bash
# Install
pip install gunicorn

# Collect static files
python manage.py collectstatic --noinput

# Run
gunicorn myproject.wsgi:application --workers 4 --bind 0.0.0.0:8000
```

## Deployment Options

### Option 1: Docker
```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

```bash
docker build -t myapp .
docker run -p 8000:8000 myapp
```

### Option 2: Railway
```bash
# railway.toml
[build]
builder = "nixpacks"

[deploy]
startCommand = "gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker"
```

### Option 3: Render
```yaml
# render.yaml
services:
  - type: web
    name: myapp
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker
```

### Option 4: AWS (EC2 + Nginx)
```bash
# Install on server
sudo apt update
sudo apt install nginx python3-pip

# Setup systemd service
sudo nano /etc/systemd/system/myapp.service

# Nginx reverse proxy
sudo nano /etc/nginx/sites-available/myapp
```

## Environment Variables
```bash
# .env (never commit!)
DATABASE_URL=postgresql://user:pass@host:5432/db
SECRET_KEY=your-secret-key
DEBUG=false

# Load with python-dotenv
from dotenv import load_dotenv
load_dotenv()
```

## Production Checklist
- [ ] Set DEBUG=false
- [ ] Use production database (PostgreSQL)
- [ ] Configure CORS properly
- [ ] Set up logging
- [ ] Use HTTPS
- [ ] Set secure headers
- [ ] Configure rate limiting
""",
        "source": "Python/FastAPI Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # Node.js Backend
    # ==========================================================================
    {
        "id": "nodejs-deployment",
        "title": "Node.js Backend Deployment Guide",
        "category": "deployment",
        "platform": "node",
        "tags": ["node", "nodejs", "express", "backend", "docker", "pm2"],
        "prerequisites": [
            "Node.js 18+",
            "npm or yarn",
            "PM2 (for process management)",
        ],
        "commands": [
            "npm install pm2 -g",
            "pm2 start app.js --name myapp -i max",
            "docker build -t myapp . && docker run -p 3000:3000 myapp",
        ],
        "content": """# Node.js Backend Deployment

## Prerequisites
1. **Node.js** - Version 18 LTS or higher
2. **Package Manager** - npm or yarn
3. **Process Manager** - PM2 for production

## Production Setup

### Install PM2
```bash
npm install pm2 -g

# Start app with clustering
pm2 start app.js --name myapp -i max

# Save process list
pm2 save

# Setup startup script
pm2 startup
```

### ecosystem.config.js
```javascript
module.exports = {
  apps: [{
    name: 'myapp',
    script: './dist/index.js',
    instances: 'max',
    exec_mode: 'cluster',
    env_production: {
      NODE_ENV: 'production',
      PORT: 3000
    }
  }]
};
```

## Deployment Options

### Option 1: Docker
```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production

COPY . .
EXPOSE 3000

CMD ["node", "dist/index.js"]
```

```bash
docker build -t myapp .
docker run -p 3000:3000 myapp
```

### Option 2: Vercel (Serverless)
```json
// vercel.json
{
  "version": 2,
  "builds": [{ "src": "api/**/*.js", "use": "@vercel/node" }],
  "routes": [{ "src": "/api/(.*)", "dest": "/api/$1" }]
}
```

### Option 3: Railway/Render
```bash
# Procfile
web: node dist/index.js
```

### Option 4: AWS Elastic Beanstalk
```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init

# Deploy
eb create production
eb deploy
```

## Environment Variables
```bash
# .env (never commit!)
NODE_ENV=production
PORT=3000
DATABASE_URL=postgresql://...
JWT_SECRET=your-secret

# Load with dotenv
require('dotenv').config();
```

## Production Checklist
- [ ] Set NODE_ENV=production
- [ ] Use npm ci (not npm install)
- [ ] Enable gzip compression
- [ ] Configure CORS
- [ ] Add rate limiting
- [ ] Set secure HTTP headers (helmet)
- [ ] Enable HTTPS
- [ ] Set up health checks
- [ ] Configure logging (winston/pino)
""",
        "source": "Node.js Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # Flutter (Cross-Platform)
    # ==========================================================================
    {
        "id": "flutter-deployment",
        "title": "Flutter Cross-Platform Deployment Guide",
        "category": "deployment",
        "platform": "flutter",
        "tags": ["flutter", "dart", "ios", "android", "cross-platform", "mobile"],
        "prerequisites": [
            "Flutter SDK",
            "Xcode (for iOS)",
            "Android Studio",
            "Apple Developer Account (iOS)",
            "Google Play Account (Android)",
        ],
        "commands": [
            "flutter build apk --release",
            "flutter build appbundle --release",
            "flutter build ios --release",
        ],
        "related_entries": ["ios-deployment", "android-deployment"],
        "content": """# Flutter Cross-Platform Deployment

## Prerequisites
1. **Flutter SDK** - Latest stable version
2. **Xcode** - For iOS builds (Mac only)
3. **Android Studio** - For Android builds
4. **Developer Accounts** - Apple ($99/yr) and Google ($25)

## Build for Release

### Android (AAB for Play Store)
```bash
# Build Android App Bundle
flutter build appbundle --release

# Output: build/app/outputs/bundle/release/app-release.aab

# For APK (direct install)
flutter build apk --release --split-per-abi
```

### iOS
```bash
# Build iOS release
flutter build ios --release

# Open in Xcode for archive
open ios/Runner.xcworkspace

# Then: Product → Archive → Distribute App
```

## Configuration

### Android (android/app/build.gradle)
```groovy
android {
    defaultConfig {
        applicationId "com.yourcompany.appname"
        minSdkVersion 21
        targetSdkVersion 34
        versionCode 1
        versionName "1.0.0"
    }

    signingConfigs {
        release {
            keyAlias keystoreProperties['keyAlias']
            keyPassword keystoreProperties['keyPassword']
            storeFile file(keystoreProperties['storeFile'])
            storePassword keystoreProperties['storePassword']
        }
    }
}
```

### iOS (ios/Runner/Info.plist)
```xml
<key>CFBundleDisplayName</key>
<string>Your App Name</string>
<key>CFBundleIdentifier</key>
<string>com.yourcompany.appname</string>
<key>CFBundleVersion</key>
<string>1</string>
<key>CFBundleShortVersionString</key>
<string>1.0.0</string>
```

## App Icons & Splash
```yaml
# pubspec.yaml
flutter_icons:
  android: true
  ios: true
  image_path: "assets/icon/app_icon.png"

flutter_native_splash:
  color: "#ffffff"
  image: assets/splash/splash.png
```

```bash
flutter pub run flutter_launcher_icons:main
flutter pub run flutter_native_splash:create
```

## Deployment Steps

### Android to Play Store
1. Build: `flutter build appbundle --release`
2. Upload to Play Console
3. Complete store listing
4. Submit for review

### iOS to App Store
1. Build: `flutter build ios --release`
2. Archive in Xcode
3. Upload to App Store Connect
4. Complete app information
5. Submit for review

## Common Issues
- **Cocoapods**: Run `cd ios && pod install` for iOS
- **Gradle**: Check Java version compatibility
- **Signing**: Ensure certificates/profiles match
""",
        "source": "Flutter Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # Docker/Container Deployment
    # ==========================================================================
    {
        "id": "docker-deployment",
        "title": "Docker Container Deployment Guide",
        "category": "deployment",
        "platform": "docker",
        "tags": ["docker", "container", "kubernetes", "deployment", "devops"],
        "prerequisites": [
            "Docker installed",
            "Docker Hub account (optional)",
            "Container registry access",
        ],
        "commands": [
            "docker build -t myapp:latest .",
            "docker push myregistry.com/myapp:latest",
            "docker-compose up -d",
        ],
        "content": """# Docker Container Deployment

## Prerequisites
1. **Docker** - Docker Desktop or Docker Engine
2. **Registry** - Docker Hub, AWS ECR, or private registry
3. **Orchestration** - Docker Compose, Kubernetes, or similar

## Build and Tag

```bash
# Build image
docker build -t myapp:latest .

# Tag for registry
docker tag myapp:latest myregistry.com/myapp:1.0.0
docker tag myapp:latest myregistry.com/myapp:latest
```

## Dockerfile Best Practices

```dockerfile
# Multi-stage build
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Production image
FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules ./node_modules

# Non-root user
RUN addgroup -g 1001 appgroup && \\
    adduser -u 1001 -G appgroup -D appuser
USER appuser

EXPOSE 3000
CMD ["node", "dist/index.js"]
```

## Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://db:5432/app
    depends_on:
      - db
    restart: unless-stopped

  db:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=secret

volumes:
  postgres_data:
```

## Push to Registry

```bash
# Docker Hub
docker login
docker push username/myapp:latest

# AWS ECR
aws ecr get-login-password | docker login --username AWS --password-stdin AWS_ACCOUNT.dkr.ecr.REGION.amazonaws.com
docker push AWS_ACCOUNT.dkr.ecr.REGION.amazonaws.com/myapp:latest

# GitHub Container Registry
echo $GITHUB_TOKEN | docker login ghcr.io -u USERNAME --password-stdin
docker push ghcr.io/username/myapp:latest
```

## Deployment Options

### Docker Compose (Single Server)
```bash
docker-compose up -d
docker-compose logs -f
```

### Kubernetes
```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: myapp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: myapp
  template:
    spec:
      containers:
      - name: myapp
        image: myregistry.com/myapp:latest
        ports:
        - containerPort: 3000
```

## Security Checklist
- [ ] Use specific image tags (not :latest in prod)
- [ ] Scan images for vulnerabilities
- [ ] Run as non-root user
- [ ] Don't store secrets in images
- [ ] Use .dockerignore
- [ ] Enable resource limits
""",
        "source": "Docker Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # Best Practices
    # ==========================================================================
    {
        "id": "security-best-practices",
        "title": "Security Best Practices",
        "category": "best_practice",
        "platform": None,
        "tags": ["security", "best-practices", "owasp", "authentication"],
        "content": """# Security Best Practices

## Authentication & Authorization
- Use industry-standard auth (OAuth 2.0, OpenID Connect)
- Implement proper password hashing (bcrypt, Argon2)
- Enable MFA where possible
- Use JWT with short expiration times
- Implement proper session management

## Input Validation
- Validate all user input server-side
- Use parameterized queries (prevent SQL injection)
- Sanitize output (prevent XSS)
- Implement rate limiting
- Validate file uploads (type, size, content)

## Data Protection
- Encrypt sensitive data at rest
- Use HTTPS everywhere
- Implement proper CORS policies
- Secure HTTP headers (CSP, HSTS, etc.)
- Don't log sensitive information

## Secrets Management
- Never commit secrets to version control
- Use environment variables or secret managers
- Rotate secrets regularly
- Use different secrets per environment

## API Security
- Authenticate all API endpoints
- Implement proper authorization checks
- Rate limit API requests
- Validate request payloads
- Log security events

## Dependency Security
- Keep dependencies updated
- Scan for vulnerabilities (npm audit, pip-audit)
- Use lockfiles
- Remove unused dependencies
""",
        "source": "OWASP",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # Amazon Platforms
    # ==========================================================================
    {
        "id": "amazon-appstore-deployment",
        "title": "Amazon Appstore Deployment Guide",
        "category": "deployment",
        "platform": "amazon-appstore",
        "tags": ["amazon", "fire", "android", "appstore", "mobile", "alexa"],
        "prerequisites": [
            "Amazon Developer Account (free)",
            "APK or AAB file",
            "App icons and screenshots",
        ],
        "commands": [
            "./gradlew assembleRelease",
            "# Upload APK manually via developer.amazon.com",
        ],
        "content": """# Amazon Appstore Deployment

## Prerequisites
1. **Amazon Developer Account** - Register at developer.amazon.com (free)
2. **Android App** - APK or AAB file
3. **App Assets** - Icons, screenshots, descriptions

## Step-by-Step Deployment

### 1. Prepare Your App
```bash
# Build release APK
./gradlew assembleRelease

# Output: app/build/outputs/apk/release/app-release.apk
```

### 2. Create App in Amazon Developer Console
1. Go to developer.amazon.com/apps-and-games
2. Click "Add a New App"
3. Select "Android"
4. Fill in app details

### 3. App Submission Checklist
- **App Title**: Up to 250 characters
- **Short Description**: 80 characters
- **Long Description**: 4000 characters
- **Category**: Select appropriate category
- **Keywords**: Up to 30 keywords

### 4. Required Assets
- **App Icon**: 512x512 PNG
- **Screenshots**: 3-10 screenshots
  - Phone: 800x480 to 1920x1200
  - Tablet: 1280x800 to 2560x1600
- **Feature Graphic**: 1024x500 (optional)

### 5. Submit for Review
1. Upload APK/AAB file
2. Complete content rating questionnaire
3. Set pricing and availability
4. Submit for review

## Fire TV / Fire Tablet Specifics
- Test on Fire devices or emulator
- Support D-pad navigation for Fire TV
- Consider Fire OS specific features

## Timeline
- Review: 1-3 business days typically
- Updates: Usually faster than initial submission
""",
        "source": "Amazon Developer Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "alexa-skill-deployment",
        "title": "Amazon Alexa Skill Deployment Guide",
        "category": "deployment",
        "platform": "alexa",
        "tags": ["amazon", "alexa", "voice", "skill", "lambda"],
        "prerequisites": [
            "Amazon Developer Account",
            "AWS Account (for Lambda)",
            "ASK CLI installed",
        ],
        "commands": [
            "npm install -g ask-cli",
            "ask configure",
            "ask deploy",
            "ask smapi submit-skill-for-certification -s YOUR_SKILL_ID",
        ],
        "content": """# Amazon Alexa Skill Deployment

## Prerequisites
1. **Amazon Developer Account** - developer.amazon.com
2. **AWS Account** - For Lambda hosting
3. **ASK CLI** - Alexa Skills Kit Command Line Interface

## Setup ASK CLI
```bash
# Install ASK CLI
npm install -g ask-cli

# Configure with your Amazon developer account
ask configure
```

## Project Structure
```
skill/
├── skill-package/
│   ├── interactionModels/
│   │   └── custom/
│   │       └── en-US.json
│   └── skill.json
├── lambda/
│   ├── index.js
│   └── package.json
└── ask-resources.json
```

## Deploy Skill
```bash
# Deploy skill and Lambda
ask deploy

# Deploy only skill manifest
ask deploy --target skill-metadata

# Deploy only Lambda code
ask deploy --target lambda
```

## Testing
```bash
# Test locally
ask dialog

# Run simulation
ask smapi simulate-skill --skill-id YOUR_SKILL_ID --locale en-US --input-content "open my skill"
```

## Submit for Certification
```bash
# Submit for review
ask smapi submit-skill-for-certification -s YOUR_SKILL_ID

# Check certification status
ask smapi get-certification-review -s YOUR_SKILL_ID
```

## Certification Checklist
- [ ] All required intents implemented
- [ ] Error handling for edge cases
- [ ] Privacy policy URL
- [ ] Testing instructions
- [ ] Example phrases
- [ ] Skill icon (108x108 and 512x512)

## Timeline
- Certification review: 2-5 business days
""",
        "source": "Amazon Alexa Developer Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # Design & Creative Platforms
    # ==========================================================================
    {
        "id": "canva-app-deployment",
        "title": "Canva App Deployment Guide",
        "category": "deployment",
        "platform": "canva",
        "tags": ["canva", "design", "app", "plugin", "creative"],
        "prerequisites": [
            "Canva Developer Account",
            "Node.js 18+",
            "Canva Apps SDK",
        ],
        "commands": [
            "npm install @canva/app-ui-kit @canva/design",
            "npm run build",
            "# Submit via Canva Developer Portal",
        ],
        "content": """# Canva App Deployment

## Prerequisites
1. **Canva Developer Account** - Apply at canva.com/developers
2. **Node.js** - Version 18 or higher
3. **Canva Apps SDK** - For building Canva apps

## Getting Started
```bash
# Create new Canva app
npx @canva/create-app my-canva-app
cd my-canva-app

# Install dependencies
npm install

# Start development server
npm start
```

## App Types
- **Design Apps**: Add elements to designs
- **Content Apps**: Import external content
- **Export Apps**: Custom export options
- **AI Apps**: AI-powered features

## Development
```javascript
// src/app.tsx
import { Button, Rows, Text } from "@canva/app-ui-kit";
import { addNativeElement } from "@canva/design";

export function App() {
  const handleClick = () => {
    addNativeElement({
      type: "TEXT",
      children: ["Hello from my app!"],
    });
  };

  return (
    <Rows spacing="1u">
      <Text>My Canva App</Text>
      <Button variant="primary" onClick={handleClick}>
        Add Text
      </Button>
    </Rows>
  );
}
```

## Build for Production
```bash
# Build optimized bundle
npm run build

# Output: dist/ folder
```

## Submission Process
1. Go to canva.com/developers
2. Create new app listing
3. Upload app bundle
4. Complete app information:
   - Name and description
   - Screenshots (1280x800)
   - Privacy policy
   - Support contact
5. Submit for review

## Review Guidelines
- App must provide clear value
- Follow Canva design guidelines
- Responsive and accessible
- No malicious behavior
- Clear data handling

## Timeline
- Review: 5-10 business days
""",
        "source": "Canva Developer Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "figma-plugin-deployment",
        "title": "Figma Plugin Deployment Guide",
        "category": "deployment",
        "platform": "figma",
        "tags": ["figma", "design", "plugin", "ui"],
        "prerequisites": [
            "Figma Account",
            "Node.js",
            "TypeScript (recommended)",
        ],
        "commands": [
            "npm install",
            "npm run build",
            "# Publish via Figma Desktop App",
        ],
        "content": """# Figma Plugin Deployment

## Prerequisites
1. **Figma Account** - figma.com
2. **Figma Desktop App** - Required for development
3. **Node.js** - For build tools

## Create New Plugin
1. Open Figma Desktop
2. Plugins → Development → New Plugin
3. Choose template (Empty, UI, etc.)

## Project Structure
```
my-plugin/
├── manifest.json
├── code.ts          # Plugin logic
├── ui.html          # UI (optional)
├── package.json
└── tsconfig.json
```

## manifest.json
```json
{
  "name": "My Plugin",
  "id": "1234567890",
  "api": "1.0.0",
  "main": "code.js",
  "ui": "ui.html",
  "editorType": ["figma"]
}
```

## Development
```typescript
// code.ts
figma.showUI(__html__, { width: 300, height: 400 });

figma.ui.onmessage = (msg) => {
  if (msg.type === 'create-rectangle') {
    const rect = figma.createRectangle();
    rect.resize(100, 100);
    figma.currentPage.appendChild(rect);
  }
};
```

## Build
```bash
# Install dependencies
npm install

# Build TypeScript
npm run build

# Watch mode
npm run watch
```

## Publish Plugin
1. Open Figma Desktop
2. Plugins → Development → Publish Plugin
3. Fill in details:
   - Name and tagline
   - Description
   - Cover image (1920x960)
   - Icon (128x128)
4. Submit for review

## Review Guidelines
- Clear functionality
- Good performance
- No crashes or errors
- Follows Figma guidelines

## Timeline
- Review: 2-5 business days
""",
        "source": "Figma Developer Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # Browser Extensions
    # ==========================================================================
    {
        "id": "chrome-extension-deployment",
        "title": "Chrome Web Store Deployment Guide",
        "category": "deployment",
        "platform": "chrome",
        "tags": ["chrome", "extension", "browser", "web store"],
        "prerequisites": [
            "Google Developer Account ($5 one-time)",
            "Extension files (manifest.json, etc.)",
            "Chrome browser for testing",
        ],
        "commands": [
            "zip -r extension.zip . -x '*.git*'",
            "# Upload via Chrome Developer Dashboard",
        ],
        "content": """# Chrome Web Store Deployment

## Prerequisites
1. **Google Developer Account** - Pay $5 one-time fee
2. **Extension Package** - ZIP file with manifest.json
3. **Chrome Browser** - For local testing

## Project Structure
```
extension/
├── manifest.json
├── background.js
├── content.js
├── popup/
│   ├── popup.html
│   └── popup.js
├── icons/
│   ├── icon16.png
│   ├── icon48.png
│   └── icon128.png
└── _locales/
    └── en/
        └── messages.json
```

## manifest.json (V3)
```json
{
  "manifest_version": 3,
  "name": "My Extension",
  "version": "1.0.0",
  "description": "Description of my extension",
  "permissions": ["storage", "tabs"],
  "action": {
    "default_popup": "popup/popup.html",
    "default_icon": {
      "16": "icons/icon16.png",
      "48": "icons/icon48.png",
      "128": "icons/icon128.png"
    }
  },
  "background": {
    "service_worker": "background.js"
  }
}
```

## Local Testing
1. Go to chrome://extensions/
2. Enable "Developer mode"
3. Click "Load unpacked"
4. Select extension folder

## Package for Submission
```bash
# Create ZIP (exclude unnecessary files)
zip -r extension.zip . -x '*.git*' -x 'node_modules/*' -x '*.md'
```

## Submit to Chrome Web Store
1. Go to chrome.google.com/webstore/devconsole
2. Click "New Item"
3. Upload ZIP file
4. Fill in store listing:
   - Description
   - Category
   - Screenshots (1280x800 or 640x400)
   - Icon (128x128)
5. Submit for review

## Store Listing Assets
- **Icon**: 128x128 PNG
- **Screenshots**: Up to 5 (1280x800)
- **Promo tiles**: Small (440x280), Large (920x680)
- **Description**: Detailed, keyword-rich

## Timeline
- Review: 1-3 business days (can take longer)
- Updates: Usually faster
""",
        "source": "Chrome Developer Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # E-Commerce & Marketplaces
    # ==========================================================================
    {
        "id": "shopify-app-deployment",
        "title": "Shopify App Deployment Guide",
        "category": "deployment",
        "platform": "shopify",
        "tags": ["shopify", "ecommerce", "app", "store"],
        "prerequisites": [
            "Shopify Partner Account (free)",
            "Node.js 18+",
            "Shopify CLI",
        ],
        "commands": [
            "npm install -g @shopify/cli @shopify/app",
            "shopify app init",
            "shopify app deploy",
            "# Submit via Shopify Partner Dashboard",
        ],
        "content": """# Shopify App Deployment

## Prerequisites
1. **Shopify Partner Account** - partners.shopify.com (free)
2. **Node.js** - Version 18+
3. **Shopify CLI** - Development tools

## Setup
```bash
# Install Shopify CLI
npm install -g @shopify/cli @shopify/app

# Create new app
shopify app init

# Start development
shopify app dev
```

## App Types
- **Public Apps**: Listed on Shopify App Store
- **Custom Apps**: For specific merchants
- **Sales Channel Apps**: Sell on other platforms

## Development
```bash
# Run development server
shopify app dev

# Generate extension
shopify app generate extension

# Deploy to Shopify
shopify app deploy
```

## Required Scopes
```
# shopify.app.toml
[access_scopes]
scopes = "read_products,write_orders"
```

## App Store Listing
1. Go to partners.shopify.com
2. Apps → Your App → App Listing
3. Fill in:
   - App name and tagline
   - Description (detailed)
   - Screenshots
   - Demo video (recommended)
   - Pricing plans
4. Submit for review

## Review Checklist
- [ ] Clear value proposition
- [ ] GDPR compliant
- [ ] Secure data handling
- [ ] Works on all plans
- [ ] Mobile responsive
- [ ] Fast load times

## Timeline
- Review: 5-10 business days
- May require revisions
""",
        "source": "Shopify Developer Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "wordpress-plugin-deployment",
        "title": "WordPress Plugin Deployment Guide",
        "category": "deployment",
        "platform": "wordpress",
        "tags": ["wordpress", "plugin", "php", "cms"],
        "prerequisites": [
            "WordPress.org Account",
            "SVN client",
            "PHP development environment",
        ],
        "commands": [
            "svn co https://plugins.svn.wordpress.org/your-plugin/",
            "svn add trunk/*",
            "svn ci -m 'Initial release'",
        ],
        "content": """# WordPress Plugin Deployment

## Prerequisites
1. **WordPress.org Account** - wordpress.org
2. **SVN Client** - For repository access
3. **PHP Environment** - For local testing

## Plugin Structure
```
your-plugin/
├── your-plugin.php      # Main plugin file
├── readme.txt           # Required for WP.org
├── includes/
│   └── functions.php
├── admin/
│   └── admin.php
├── public/
│   └── public.php
└── assets/
    ├── icon-256x256.png
    └── banner-1544x500.png
```

## Main Plugin File Header
```php
<?php
/**
 * Plugin Name: Your Plugin Name
 * Plugin URI: https://yoursite.com/plugin
 * Description: Short description of the plugin.
 * Version: 1.0.0
 * Author: Your Name
 * Author URI: https://yoursite.com
 * License: GPL v2 or later
 * Text Domain: your-plugin
 */
```

## readme.txt
```
=== Your Plugin Name ===
Contributors: yourname
Tags: tag1, tag2, tag3
Requires at least: 5.0
Tested up to: 6.4
Stable tag: 1.0.0
License: GPLv2 or later

Short description (150 chars max).

== Description ==
Full description of your plugin...

== Installation ==
1. Upload to /wp-content/plugins/
2. Activate the plugin
3. Configure settings

== Changelog ==
= 1.0.0 =
* Initial release
```

## Submit to WordPress.org
1. Go to wordpress.org/plugins/developers/add/
2. Submit plugin for review
3. Wait for approval (manual review)

## After Approval
```bash
# Checkout your SVN repository
svn co https://plugins.svn.wordpress.org/your-plugin/

# Add files to trunk
cp -r your-plugin/* trunk/
svn add trunk/*

# Commit
svn ci -m 'Initial release version 1.0.0'

# Create tag for release
svn cp trunk tags/1.0.0
svn ci -m 'Tagging version 1.0.0'
```

## Timeline
- Initial review: 1-10+ business days
- Updates: Instant (just SVN commit)
""",
        "source": "WordPress Developer Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # Package Registries
    # ==========================================================================
    {
        "id": "npm-deployment",
        "title": "npm Package Publishing Guide",
        "category": "deployment",
        "platform": "npm",
        "tags": ["npm", "node", "javascript", "package", "registry"],
        "prerequisites": [
            "npm Account",
            "Node.js installed",
            "package.json configured",
        ],
        "commands": [
            "npm login",
            "npm version patch",
            "npm publish",
        ],
        "content": """# npm Package Publishing

## Prerequisites
1. **npm Account** - npmjs.com
2. **Node.js** - With npm CLI
3. **package.json** - Properly configured

## package.json Setup
```json
{
  "name": "your-package",
  "version": "1.0.0",
  "description": "Package description",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "files": ["dist"],
  "scripts": {
    "build": "tsc",
    "prepublishOnly": "npm run build"
  },
  "keywords": ["keyword1", "keyword2"],
  "author": "Your Name <you@email.com>",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/you/your-package"
  }
}
```

## Login to npm
```bash
npm login
# Enter username, password, email
```

## Publish Package
```bash
# First time publish
npm publish

# For scoped packages (@yourname/package)
npm publish --access public
```

## Version Updates
```bash
# Patch version (1.0.0 -> 1.0.1)
npm version patch

# Minor version (1.0.0 -> 1.1.0)
npm version minor

# Major version (1.0.0 -> 2.0.0)
npm version major

# Publish new version
npm publish
```

## .npmignore
```
src/
tests/
*.test.js
.github/
tsconfig.json
```

## Pre-publish Checklist
- [ ] README.md is complete
- [ ] package.json has all fields
- [ ] Tests pass
- [ ] Build succeeds
- [ ] .npmignore excludes dev files
- [ ] License file included

## Timeline
- Publishing: Instant
- Available: Within minutes
""",
        "source": "npm Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "pypi-deployment",
        "title": "PyPI Package Publishing Guide",
        "category": "deployment",
        "platform": "pypi",
        "tags": ["pypi", "python", "package", "pip"],
        "prerequisites": [
            "PyPI Account",
            "Python installed",
            "twine installed",
        ],
        "commands": [
            "pip install build twine",
            "python -m build",
            "twine upload dist/*",
        ],
        "content": """# PyPI Package Publishing

## Prerequisites
1. **PyPI Account** - pypi.org
2. **Python** - 3.8+
3. **Build Tools** - build, twine

## Project Structure
```
your-package/
├── src/
│   └── your_package/
│       ├── __init__.py
│       └── module.py
├── tests/
├── pyproject.toml
├── README.md
└── LICENSE
```

## pyproject.toml
```toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "your-package"
version = "1.0.0"
authors = [
  { name="Your Name", email="you@email.com" },
]
description = "A short description"
readme = "README.md"
requires-python = ">=3.8"
classifiers = [
    "Programming Language :: Python :: 3",
    "License :: OSI Approved :: MIT License",
    "Operating System :: OS Independent",
]
dependencies = [
    "requests>=2.25.0",
]

[project.urls]
Homepage = "https://github.com/you/your-package"
Issues = "https://github.com/you/your-package/issues"
```

## Build Package
```bash
# Install build tools
pip install build twine

# Build package
python -m build

# Output: dist/your_package-1.0.0.tar.gz
#         dist/your_package-1.0.0-py3-none-any.whl
```

## Upload to PyPI
```bash
# Upload to TestPyPI first (recommended)
twine upload --repository testpypi dist/*

# Upload to PyPI
twine upload dist/*
```

## API Token (Recommended)
```bash
# Create token at pypi.org/manage/account/token/

# Use in ~/.pypirc
[pypi]
username = __token__
password = pypi-YOUR-TOKEN-HERE
```

## Version Updates
```bash
# Update version in pyproject.toml
# Build new version
python -m build

# Upload
twine upload dist/*
```

## Timeline
- Publishing: Instant
- pip installable: Within minutes
""",
        "source": "PyPI Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },

    # ==========================================================================
    # Communication Platforms
    # ==========================================================================
    {
        "id": "slack-app-deployment",
        "title": "Slack App Deployment Guide",
        "category": "deployment",
        "platform": "slack",
        "tags": ["slack", "bot", "app", "messaging"],
        "prerequisites": [
            "Slack Workspace (admin access)",
            "Slack API Account",
            "Node.js or Python",
        ],
        "commands": [
            "npm install @slack/bolt",
            "# Configure app at api.slack.com/apps",
            "npm start",
        ],
        "content": """# Slack App Deployment

## Prerequisites
1. **Slack Workspace** - With admin access
2. **Slack API Account** - api.slack.com
3. **Hosting** - Server for your app

## Create Slack App
1. Go to api.slack.com/apps
2. Click "Create New App"
3. Choose "From scratch" or "From manifest"
4. Select workspace

## App Setup with Bolt.js
```bash
npm install @slack/bolt
```

```javascript
const { App } = require('@slack/bolt');

const app = new App({
  token: process.env.SLACK_BOT_TOKEN,
  signingSecret: process.env.SLACK_SIGNING_SECRET,
  socketMode: true,
  appToken: process.env.SLACK_APP_TOKEN,
});

app.message('hello', async ({ message, say }) => {
  await say(`Hey there <@${message.user}>!`);
});

(async () => {
  await app.start();
  console.log('⚡️ Bolt app started');
})();
```

## Required Scopes
- `chat:write` - Send messages
- `app_mentions:read` - Read @mentions
- `commands` - Slash commands
- `im:history` - Direct messages

## Event Subscriptions
1. Enable Events in app settings
2. Add Request URL (your server)
3. Subscribe to events:
   - `message.channels`
   - `message.im`
   - `app_mention`

## Distribution
### Internal (Workspace Only)
- Install directly to your workspace
- No review needed

### Public (App Directory)
1. Go to "Manage Distribution"
2. Enable "Public Distribution"
3. Fill out App Directory listing
4. Submit for review

## Listing Requirements
- Clear app description
- Privacy policy
- Support contact
- Screenshots/demo

## Timeline
- Internal: Instant
- App Directory: 2-4 weeks review
""",
        "source": "Slack API Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
    {
        "id": "discord-bot-deployment",
        "title": "Discord Bot Deployment Guide",
        "category": "deployment",
        "platform": "discord",
        "tags": ["discord", "bot", "gaming", "messaging"],
        "prerequisites": [
            "Discord Account",
            "Discord Developer Portal access",
            "Node.js or Python",
        ],
        "commands": [
            "npm install discord.js",
            "# Create bot at discord.com/developers",
            "npm start",
        ],
        "content": """# Discord Bot Deployment

## Prerequisites
1. **Discord Account** - discord.com
2. **Developer Portal** - discord.com/developers
3. **Hosting** - Server to run bot 24/7

## Create Discord Application
1. Go to discord.com/developers/applications
2. Click "New Application"
3. Name your application
4. Go to "Bot" section
5. Click "Add Bot"
6. Copy bot token (keep secret!)

## Bot with discord.js
```bash
npm install discord.js
```

```javascript
const { Client, GatewayIntentBits } = require('discord.js');

const client = new Client({
  intents: [
    GatewayIntentBits.Guilds,
    GatewayIntentBits.GuildMessages,
    GatewayIntentBits.MessageContent,
  ]
});

client.on('ready', () => {
  console.log(`Logged in as ${client.user.tag}!`);
});

client.on('messageCreate', message => {
  if (message.content === '!ping') {
    message.reply('Pong!');
  }
});

client.login(process.env.DISCORD_TOKEN);
```

## Slash Commands
```javascript
const { SlashCommandBuilder } = require('discord.js');

const command = new SlashCommandBuilder()
  .setName('ping')
  .setDescription('Replies with Pong!');

// Register command
await client.application.commands.create(command);
```

## Bot Permissions
- Message Content Intent (for reading messages)
- Server Members Intent (for member info)
- Presence Intent (for status)

## Invite Bot to Server
```
https://discord.com/api/oauth2/authorize?client_id=YOUR_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

## Hosting Options
- **Railway**: Easy deployment
- **Heroku**: Free tier available
- **VPS**: Full control
- **AWS/GCP**: Scalable

## App Directory (Verification)
For 100+ servers:
1. Apply for verification
2. Provide detailed info
3. Privacy policy required
4. May take weeks

## Timeline
- Development: Instant
- Verification: 5+ business days
""",
        "source": "Discord Developer Documentation",
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat(),
    },
]
