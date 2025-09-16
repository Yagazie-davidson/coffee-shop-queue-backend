# Environment Variables Setup Guide

## Overview

This guide explains how to properly manage environment variables in your Coffee Shop Queue System using `.env` files.

## 1. Create Your .env File

Create a `.env` file in your backend directory:

```bash
# In your backend directory
touch .env
```

## 2. Environment Variable Format

### ✅ **Correct Format**

```bash
# .env file format
VARIABLE_NAME=value
VARIABLE_NAME_WITH_UNDERSCORES=value
VARIABLE_NAME_WITH_NUMBERS=123
VARIABLE_NAME_WITH_QUOTES="value with spaces"
VARIABLE_NAME_WITHOUT_QUOTES=value_without_spaces
```

### ❌ **Incorrect Format**

```bash
# DON'T do this
VARIABLE_NAME = value  # No spaces around =
VARIABLE_NAME= value   # No space after =
VARIABLE_NAME =value   # No space before =
VARIABLE_NAME=value with spaces  # Use quotes for spaces
```

## 3. Your .env File Content

Copy this content to your `.env` file:

```bash
# Coffee Shop Queue System - Environment Variables

# Flask Configuration
FLASK_ENV=development
FLASK_DEBUG=True

# Server Configuration
PORT=5002
HOST=0.0.0.0

# Frontend URL (for CORS)
FRONTEND_URL=http://localhost:3000

# Production Environment Detection
RENDER_ENVIRONMENT=False

# Logging Configuration
LOG_LEVEL=INFO

# Cache Configuration
CACHE_TTL=300
```

## 4. Environment-Specific Files

### Development (.env.development)

```bash
FLASK_ENV=development
FLASK_DEBUG=True
FRONTEND_URL=http://localhost:3000
RENDER_ENVIRONMENT=False
LOG_LEVEL=DEBUG
```

### Production (.env.production)

```bash
FLASK_ENV=production
FLASK_DEBUG=False
FRONTEND_URL=https://your-frontend-domain.com
RENDER_ENVIRONMENT=True
LOG_LEVEL=WARNING
```

### Testing (.env.testing)

```bash
FLASK_ENV=testing
FLASK_DEBUG=False
FRONTEND_URL=http://localhost:3001
RENDER_ENVIRONMENT=False
LOG_LEVEL=ERROR
```

## 5. Loading Environment Variables

### Method 1: Using python-dotenv (Recommended)

```python
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Access variables
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
port = int(os.environ.get('PORT', 5002))
debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
```

### Method 2: Direct os.environ (Current approach)

```python
import os

# Access variables directly
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
port = int(os.environ.get('PORT', 5002))
```

## 6. Best Practices

### ✅ **Do This**

```python
# Use .get() with default values
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

# Convert types properly
port = int(os.environ.get('PORT', 5002))
debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'

# Handle boolean values
is_production = os.environ.get('RENDER_ENVIRONMENT', 'False').lower() == 'true'
```

### ❌ **Don't Do This**

```python
# Don't access without defaults
frontend_url = os.environ['FRONTEND_URL']  # Will crash if not set

# Don't forget type conversion
port = os.environ.get('PORT', 5002)  # Returns string, not int
```

## 7. Security Considerations

### ✅ **Secure Practices**

```bash
# .env file (never commit to git)
SECRET_KEY=your-super-secret-key-here
DATABASE_PASSWORD=your-database-password

# .env.example file (safe to commit)
SECRET_KEY=your-secret-key-here
DATABASE_PASSWORD=your-database-password
```

### ❌ **Insecure Practices**

```bash
# Don't put real secrets in .env.example
SECRET_KEY=abc123  # Real secret in example file
DATABASE_PASSWORD=realpassword  # Real password in example file
```

## 8. Git Integration

### .gitignore

```bash
# Environment files
.env
.env.local
.env.production
.env.staging

# But keep example files
!.env.example
```

### .env.example

```bash
# Safe example values
SECRET_KEY=your-secret-key-here
DATABASE_PASSWORD=your-database-password
FRONTEND_URL=http://localhost:3000
```

## 9. Deployment Considerations

### Local Development

```bash
# Load from .env file
python app.py
```

### Production (Render, Heroku, etc.)

```bash
# Set environment variables in platform
export FRONTEND_URL=https://your-frontend.com
export RENDER_ENVIRONMENT=True
python app.py
```

### Docker

```dockerfile
# Dockerfile
FROM python:3.13
COPY . .
RUN pip install -r requirements.txt
CMD ["python", "app.py"]
```

```bash
# docker-compose.yml
version: '3.8'
services:
  backend:
    build: .
    environment:
      - FRONTEND_URL=http://localhost:3000
      - RENDER_ENVIRONMENT=False
    ports:
      - "5002:5002"
```

## 10. Testing Environment Variables

```python
# test_env.py
import os
from dotenv import load_dotenv

def test_env_variables():
    load_dotenv()

    # Test required variables
    assert os.environ.get('FRONTEND_URL') is not None
    assert os.environ.get('PORT') is not None

    # Test default values
    frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
    assert frontend_url == 'http://localhost:3000'

    print("✅ All environment variables loaded correctly!")

if __name__ == "__main__":
    test_env_variables()
```

## 11. Common Issues and Solutions

### Issue: Variables not loading

```python
# Solution: Check if .env file exists and is in correct location
import os
print(os.path.exists('.env'))  # Should be True
print(os.getcwd())  # Check current directory
```

### Issue: Type conversion errors

```python
# Solution: Always convert types explicitly
port = int(os.environ.get('PORT', '5002'))  # Convert to int
debug = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'  # Convert to bool
```

### Issue: Missing variables in production

```python
# Solution: Always provide defaults
frontend_url = os.environ.get('FRONTEND_URL', 'http://localhost:3000')
if not frontend_url:
    raise ValueError("FRONTEND_URL environment variable is required")
```

## 12. Complete Example

### .env file

```bash
FLASK_ENV=development
FLASK_DEBUG=True
PORT=5002
HOST=0.0.0.0
FRONTEND_URL=http://localhost:3000
RENDER_ENVIRONMENT=False
LOG_LEVEL=INFO
```

### app.py

```python
from flask import Flask
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config['DEBUG'] = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
app.config['HOST'] = os.environ.get('HOST', '0.0.0.0')
app.config['PORT'] = int(os.environ.get('PORT', 5002))

# CORS configuration
allowed_origins = os.environ.get('FRONTEND_URL', 'http://localhost:3000')

if __name__ == '__main__':
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
    )
```

This setup ensures your environment variables are properly loaded and managed across different environments!
