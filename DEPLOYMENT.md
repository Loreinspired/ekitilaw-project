# Railway Deployment Guide

## 🚀 Quick Deploy to Railway

### Option 1: Deploy via Railway Web Dashboard (Easiest)

1. **Go to Railway**: https://railway.app
2. **Sign up/Login** with your GitHub account
3. **Click "New Project"**
4. **Select "Deploy from GitHub repo"**
5. **Connect your repository**: `Loreinspired/ekitilaw-project`
6. **Select branch**: `claude/testing-mi98rlkluc0cosp4-012p5hnVYiUcrce1Bh8oax3d` (or your main branch)
7. **Railway will auto-detect** Django and start building

### Step 2: Add PostgreSQL Database

1. In your project dashboard, click **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway will automatically:
   - Create a PostgreSQL database
   - Set the `DATABASE_URL` environment variable
   - Link it to your Django app

### Step 3: Configure Environment Variables

In Railway project settings → Variables, add:

```bash
SECRET_KEY=your-long-random-secret-key-here-generate-a-secure-one
DEBUG=False
ALLOWED_HOSTS=.railway.app
DJANGO_SETTINGS_MODULE=ekitilaw_project.settings

# Optional (if using Gemini AI for text cleaning)
GEMINI_API_KEY=your-gemini-api-key

# Optional (if using external MeiliSearch)
MEILI_HOST=your-meilisearch-host
MEILI_PORT=7700
MEILI_MASTER_KEY=your-meili-key
```

**Generate a secure SECRET_KEY:**
```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

### Step 4: Deploy and Migrate

1. Railway will automatically deploy your app
2. Once deployed, go to your project → **"Settings"** → **"Deployments"**
3. Find the latest deployment and click **"View Logs"**
4. To run migrations, click on your service → **"Settings"** → **"Custom Start Command"**:
   ```bash
   python manage.py migrate && gunicorn ekitilaw_project.wsgi
   ```

Alternatively, use Railway CLI to run one-off commands:
```bash
railway run python manage.py migrate
railway run python manage.py createsuperuser
```

### Step 5: Create Superuser

Using Railway CLI:
```bash
railway run python manage.py createsuperuser
```

Or add this to your deployment with a Django management command.

### Step 6: Access Your App

1. Railway will provide a URL like: `https://your-app.up.railway.app`
2. Visit: `https://your-app.up.railway.app/admin/` to access admin
3. Visit: `https://your-app.up.railway.app/laws/search/` for the search interface

---

## Option 2: Deploy via Railway CLI

### Prerequisites
```bash
npm install -g @railway/cli
```

### Steps

1. **Login to Railway**
```bash
railway login
```

2. **Link to Your Project** (or create new)
```bash
# Create new project
railway init

# Or link to existing project
railway link
```

3. **Add PostgreSQL Database**
```bash
railway add --database postgresql
```

4. **Set Environment Variables**
```bash
railway variables set SECRET_KEY="your-secret-key-here"
railway variables set DEBUG="False"
railway variables set ALLOWED_HOSTS=".railway.app"
```

5. **Deploy**
```bash
railway up
```

6. **Run Migrations**
```bash
railway run python manage.py migrate
railway run python manage.py collectstatic --noinput
railway run python manage.py createsuperuser
```

7. **Get Your URL**
```bash
railway open
```

---

## 🔧 Post-Deployment Setup

### 1. Setup MeiliSearch (for Search Functionality)

**Option A: Use Railway Template**
1. In Railway, click "New" → "Template"
2. Search for "MeiliSearch"
3. Deploy MeiliSearch instance
4. Copy the connection details to your app's environment variables

**Option B: Use External MeiliSearch Cloud**
1. Sign up at https://www.meilisearch.com/cloud
2. Create an instance
3. Add credentials to Railway environment variables

### 2. Rebuild Search Index

After deploying and setting up MeiliSearch:
```bash
railway run python manage.py rebuild_meili
```

### 3. Import Your First Law

1. Go to your deployed admin: `https://your-app.railway.app/admin/`
2. Add a Law with AI-prepared text
3. Use the admin action to import it
4. The law will be searchable!

---

## 📊 Monitoring

- **View Logs**: Railway Dashboard → Your Service → "Deployments" → "View Logs"
- **Metrics**: Railway Dashboard → Your Service → "Metrics"
- **Database**: Railway Dashboard → PostgreSQL Service → "Data" (query your DB)

---

## 🔄 Continuous Deployment

Railway automatically redeploys when you push to your connected GitHub branch:

```bash
git add .
git commit -m "Update feature"
git push origin main
```

Railway will detect the push and automatically deploy!

---

## 🐛 Troubleshooting

### Static Files Not Loading
Make sure `STATIC_ROOT` is set and collectstatic runs:
```bash
railway run python manage.py collectstatic --noinput
```

### Database Connection Issues
Check that `DATABASE_URL` is set by Railway (it should be automatic).

### App Won't Start
Check logs:
```bash
railway logs
```

Common issues:
- Missing `SECRET_KEY` environment variable
- Migration errors (run `railway run python manage.py migrate`)
- Missing dependencies (check `requirements.txt`)

---

## 💰 Pricing

- **Starter Plan**: $5/month
  - Includes $5 credit
  - PostgreSQL database included
  - Custom domains
  - Automatic SSL

- **Developer Plan**: $20/month
  - More resources
  - Priority support

**Free Trial**: Railway offers trial credits for new users!

---

## 🔐 Security Checklist

- [ ] SECRET_KEY is set to a random value (not the default)
- [ ] DEBUG is set to False in production
- [ ] ALLOWED_HOSTS includes your Railway domain
- [ ] Database uses strong password (Railway generates this)
- [ ] CSRF_TRUSTED_ORIGINS includes your domain
- [ ] Sensitive data is in environment variables, not code

---

## 📚 Resources

- Railway Docs: https://docs.railway.app
- Django Deployment: https://docs.djangoproject.com/en/4.2/howto/deployment/
- Railway Discord: https://discord.gg/railway

---

Your app is configured and ready to deploy! 🚀
