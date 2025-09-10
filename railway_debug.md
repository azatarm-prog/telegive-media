# Railway Deployment Debugging Guide

## Current Status
- **Domain**: telegive-media-production.up.railway.app
- **Issue**: 502 Application failed to respond
- **Last Deploy**: Simplified app for debugging

## Immediate Steps to Debug

### 1. Check Railway Logs
In your Railway dashboard:
1. Go to your media service
2. Click on "Deployments" tab
3. Click on the latest deployment
4. Check the "Logs" section for error messages

### 2. Common Issues to Look For

#### A. Port Binding Issues
Look for logs like:
```
Error: bind EADDRINUSE :::8005
```
**Solution**: Ensure `PORT` environment variable is set correctly

#### B. Memory Issues
Look for logs like:
```
Process killed (OOM)
```
**Solution**: Reduce workers/threads in Procfile

#### C. Database Connection Issues
Look for logs like:
```
could not connect to server
```
**Solution**: Check PostgreSQL service connection

#### D. Missing Dependencies
Look for logs like:
```
ModuleNotFoundError: No module named 'xyz'
```
**Solution**: Check requirements.txt

### 3. Environment Variables Check
Ensure these are set in Railway:
```
PORT=(automatically set by Railway)
DATABASE_URL=${{Postgres.DATABASE_URL}}
SECRET_KEY=your-secret-key
FLASK_ENV=production
SERVICE_NAME=media-service
```

### 4. Quick Fixes to Try

#### Option 1: Minimal Procfile
```
web: python simple_app.py
```

#### Option 2: Basic Gunicorn
```
web: gunicorn --bind 0.0.0.0:$PORT simple_app:app
```

#### Option 3: Debug Mode
Add to environment variables:
```
FLASK_DEBUG=true
```

### 5. Test Locally First
Before deploying, test locally:
```bash
export PORT=8005
export SECRET_KEY=test-key
python simple_app.py
```

### 6. Progressive Deployment Strategy

#### Step 1: Get Basic App Working
Use simple_app.py (currently deployed)

#### Step 2: Add Database
Once basic app works, add database connection

#### Step 3: Add Full Features
Gradually add back full functionality

## Next Actions

1. **Check Railway logs** for specific error messages
2. **Try the quick fixes** above based on what you see in logs
3. **Report back** with the specific error messages from logs
4. **We'll fix** the specific issues step by step

## Emergency Rollback
If needed, we can create an even simpler version:
```python
from flask import Flask
app = Flask(__name__)

@app.route('/')
def hello():
    return "Media Service is running!"

if __name__ == '__main__':
    import os
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 8005)))
```

## Contact Points
- Check Railway dashboard logs
- Verify environment variables
- Test with minimal configuration first
- Build up complexity gradually

