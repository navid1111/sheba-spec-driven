# Render Deployment Guide - ShoktiAI Backend

## Prerequisites

1. **Neon Database** (Already set up)
   - Connection string: `postgresql://default:...@ep-lively-smoke-a4s1oha4-pooler.us-east-1.aws.neon.tech/verceldb?sslmode=require`

2. **OpenAI API Key**
   - Your key for GPT-4o-mini

3. **Gmail SMTP Credentials**
   - Email: navidkamal568@gmail.com
   - App Password: (your 16-character app password)

4. **GitHub Repository**
   - Push your code to GitHub: `navid1111/sheba-spec-driven`

---

## Deployment Steps

### Option 1: Using Render Dashboard (Recommended)

1. **Go to Render Dashboard**: https://dashboard.render.com

2. **Create New Web Service**
   - Click "New +" → "Web Service"
   - Connect your GitHub repository: `navid1111/sheba-spec-driven`
   - Branch: `master` (or your deployment branch)

3. **Configure Build Settings**
   - **Name**: `shoktiai-backend`
   - **Region**: Singapore (or closest to you)
   - **Environment**: Docker
   - **Dockerfile Path**: `./Dockerfile`
   - **Docker Build Context**: `.` (root)
   - **Plan**: Free or Starter ($7/month)

4. **Set Environment Variables**

   Click "Advanced" and add these environment variables:

   ```bash
   # Database (CRITICAL - Use your Neon URL with psycopg2 driver)
   DATABASE_URL=postgresql+psycopg2://default:3F5SCcDAbWYM@ep-lively-smoke-a4s1oha4-pooler.us-east-1.aws.neon.tech/verceldb?sslmode=require

   # OpenAI
   OPENAI_API_KEY=your_openai_api_key_here

   # JWT (Auto-generate secret in Render)
   JWT_SECRET=your_jwt_secret_here
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_MINUTES=10080

   # OTP
   OTP_PROVIDER=email
   OTP_EXPIRATION_MINUTES=10

   # SMTP (Gmail)
   SMTP_HOST=smtp.gmail.com
   SMTP_PORT=465
   SMTP_USER=navidkamal568@gmail.com
   SMTP_PASSWORD=your_16_char_app_password
   SMTP_FROM_EMAIL=navidkamal568@gmail.com

   # App URLs
   BASE_URL=https://app.sheba.xyz
   DEEP_LINK_BASE_URL=https://app.sheba.xyz/book

   # Port (automatically set by Render)
   PORT=8000
   ```

5. **Health Check Path**
   - Set to: `/health`

6. **Click "Create Web Service"**

7. **Wait for Deployment** (3-5 minutes)
   - Watch logs for:
     - ✅ `Running database migrations...`
     - ✅ `Starting Uvicorn server...`
     - ✅ `Application startup complete`

---

### Option 2: Using render.yaml Blueprint

1. **Push render.yaml to your repo**
   ```bash
   git add render.yaml Dockerfile backend/start.sh
   git commit -m "Add Render deployment config"
   git push origin master
   ```

2. **Create Blueprint in Render**
   - Go to: https://dashboard.render.com/blueprints
   - Click "New Blueprint Instance"
   - Connect repository: `navid1111/sheba-spec-driven`
   - Render will read `render.yaml` and configure everything

3. **Set Secret Environment Variables**
   - Render will prompt you to set:
     - `DATABASE_URL`
     - `OPENAI_API_KEY`
     - `SMTP_USER`
     - `SMTP_PASSWORD`
     - `SMTP_FROM_EMAIL`

4. **Deploy**

---

## Verify Deployment

### 1. Check Health Endpoint
```bash
curl https://shoktiai-backend.onrender.com/health
```

Expected response:
```json
{"status": "ok"}
```

### 2. Check API Docs
Visit: https://shoktiai-backend.onrender.com/docs

### 3. Check Metrics
```bash
curl https://shoktiai-backend.onrender.com/metrics
```

### 4. Test Authentication
```bash
curl -X POST https://shoktiai-backend.onrender.com/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone": "+8801712345678"}'
```

---

## Troubleshooting

### Issue: "Connection to localhost:5432 refused"
**Solution**: Make sure `DATABASE_URL` uses your Neon connection string, NOT localhost.

Correct format:
```
postgresql+psycopg2://default:PASSWORD@HOST/DATABASE?sslmode=require
```

### Issue: "Alembic migrations fail"
**Solution**: The `start.sh` script runs migrations before starting the server. Check logs for specific migration errors.

### Issue: "SMTP authentication failed"
**Solution**: 
1. Use Gmail App Password (not regular password)
2. Generate at: https://myaccount.google.com/apppasswords
3. Make sure 2FA is enabled on your Google account

### Issue: "OpenAI API errors"
**Solution**: Verify your `OPENAI_API_KEY` is set correctly in environment variables.

### Issue: "Health check failing"
**Solution**: 
1. Check logs: `render logs shoktiai-backend`
2. Ensure port 8000 is exposed in Dockerfile
3. Verify `/health` endpoint returns 200

---

## Monitoring

### View Logs
```bash
# Real-time logs
render logs shoktiai-backend --follow

# Recent logs
render logs shoktiai-backend --tail 100
```

### Metrics
- **Prometheus**: Available at `/metrics`
- **Health**: Available at `/health`
- **Uptime**: Check Render dashboard

### Auto-Scaling
Render automatically:
- Restarts on crashes
- Scales on Free tier: 1 instance
- Scales on Paid tier: Configure in dashboard

---

## Custom Domain (Optional)

1. Go to your service in Render Dashboard
2. Click "Settings" → "Custom Domains"
3. Add your domain: `api.sheba.xyz`
4. Update DNS records as instructed
5. Render provisions SSL automatically

---

## Production Checklist

Before going live:

- [ ] Use paid Render plan ($7+/month for always-on)
- [ ] Set strong `JWT_SECRET` (use Render's auto-generate)
- [ ] Configure custom domain with SSL
- [ ] Set up monitoring/alerts in Render
- [ ] Enable auto-deploy from main branch
- [ ] Test all API endpoints in production
- [ ] Set up database backups (Neon has automatic backups)
- [ ] Review and optimize Neon connection pooling
- [ ] Configure CORS for your frontend domain
- [ ] Set up Sentry or error tracking
- [ ] Document your API with proper OpenAPI specs

---

## Useful Commands

```bash
# Deploy manually
git push origin master

# Check service status
render services list

# View environment variables
render env list --service shoktiai-backend

# Restart service
render services restart shoktiai-backend

# Shell into running container (paid plans)
render shell shoktiai-backend
```

---

## Render vs Docker Compose

**Local Development**: Use `docker-compose.yml` with local Postgres
**Production**: Use Render + Neon (managed services, auto-scaling, zero-downtime deploys)

---

## Support

- **Render Docs**: https://render.com/docs
- **Render Status**: https://status.render.com
- **Discord**: https://render.com/discord

---

**Your deployment URL will be**: `https://shoktiai-backend.onrender.com`

Replace this in your frontend and mobile apps! 🚀
