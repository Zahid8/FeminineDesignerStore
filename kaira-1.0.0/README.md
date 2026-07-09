# FemDes Webstore: Run And Deploy

This is a Django 5.2 webstore. These instructions cover only local startup and production deployment.

## Run Locally

### 1. Enter the project

```bash
cd /home/zahid/Projects/Zahid/Fem_des_shop/kaira-1.0.0
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Local `.env` values:

```env
DJANGO_SECRET_KEY=replace-with-a-long-random-secret
DJANGO_DEBUG=True
DJANGO_ALLOWED_HOSTS=127.0.0.1,localhost
DATABASE_URL=sqlite:///db.sqlite3
DJANGO_CSRF_TRUSTED_ORIGINS=
```

### 3. Install dependencies

Using the existing conda environment:

```bash
conda activate femdes
python -m pip install -r requirements.txt
```

Or with a fresh virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Prepare the database and static files

```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 5. Add demo/store data

If `seed_demo_store` has been implemented:

```bash
python manage.py seed_demo_store
```

If the seed command is not available yet, add data manually at `/admin/`:

- one `SiteSettings` row;
- active categories;
- active products with SKU, price, stock, and category;
- product images if needed;
- discounts if needed.

### 6. Start the local server

```bash
python manage.py runserver 127.0.0.1:8000
```

Open:

- Storefront: `http://127.0.0.1:8000/`
- Shop: `http://127.0.0.1:8000/shop/`
- Admin: `http://127.0.0.1:8000/admin/`

### 7. Local verification

```bash
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test
python manage.py collectstatic --noinput
```

With conda without activating the shell:

```bash
conda run -n femdes python manage.py check
conda run -n femdes python manage.py test
```

## Deploy Online

The simplest path is a Python web service plus PostgreSQL on a host such as Render, Railway, Fly.io, or a VPS. The commands below use Render-style settings, but the same build/start commands apply elsewhere.

### 1. Add a production WSGI server

`requirements.txt` currently does not include a production process server. Add Gunicorn before deploying:

```bash
python -m pip install gunicorn
python -m pip freeze | rg "gunicorn"
```

Add the resulting `gunicorn==...` line to `requirements.txt`, then commit it.

### 2. Push the project to GitHub

If this directory is not already inside a Git repository:

```bash
git init
git add .
git commit -m "Deploy FemDes webstore"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```

If it is inside a parent repository, commit and push from the parent repository instead.

### 3. Create a production database

Create PostgreSQL on your hosting provider and copy its database URL.

Production environment variables:

```env
DJANGO_SECRET_KEY=<long-random-secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<your-hostname>,www.<your-domain>
DATABASE_URL=<postgres-database-url>
DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-hostname>,https://www.<your-domain>
```

Examples:

```env
DJANGO_ALLOWED_HOSTS=femdes.onrender.com,femdes.com,www.femdes.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://femdes.onrender.com,https://femdes.com,https://www.femdes.com
```

### 4. Configure the web service

Build command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

Start command:

```bash
python manage.py migrate && gunicorn femdes_site.wsgi:application
```

Do not use `python manage.py runserver` in production.

### 5. Create the online admin user

Open the host's shell/console and run:

```bash
python manage.py createsuperuser
```

Then open:

```text
https://<your-hostname>/admin/
```

### 6. Add production data

If available:

```bash
python manage.py seed_demo_store
```

Then use `/admin/` to edit products, prices, stock, images, discounts, orders, and site settings.

### 7. Attach a custom domain

1. Add the domain in the hosting provider dashboard.
2. Add the provider's DNS records at your domain registrar.
3. Wait for DNS propagation.
4. Update:

```env
DJANGO_ALLOWED_HOSTS=<provider-host>,yourdomain.com,www.yourdomain.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://<provider-host>,https://yourdomain.com,https://www.yourdomain.com
```

5. Redeploy.

### 8. Production checks

Run before or immediately after deploy:

```bash
python manage.py check
DJANGO_DEBUG=False python manage.py check --deploy
python manage.py migrate
python manage.py collectstatic --noinput
```

Review every `check --deploy` warning. Configure HTTPS redirects, secure cookies, and proxy headers according to the hosting provider before accepting real traffic.

### 9. Media files (production object storage)

Local development uses filesystem storage at `media/` by default — no configuration needed.

For production, enable S3-compatible object storage so uploaded product images survive deploys:

```env
DJANGO_MEDIA_STORAGE=s3
AWS_ACCESS_KEY_ID=<your-access-key>
AWS_SECRET_ACCESS_KEY=<your-secret-key>
AWS_STORAGE_BUCKET_NAME=<your-bucket-name>
```

Optional variables for S3-compatible providers (Cloudflare R2, DigitalOcean Spaces, Backblaze B2, etc.):

```env
AWS_S3_REGION_NAME=auto           # or your provider's region
AWS_S3_ENDPOINT_URL=https://<account-id>.r2.cloudflarestorage.com
AWS_S3_CUSTOM_DOMAIN=cdn.example.com   # if using a CDN
```

Example for Cloudflare R2:

```env
DJANGO_MEDIA_STORAGE=s3
AWS_ACCESS_KEY_ID=abc123
AWS_SECRET_ACCESS_KEY=xyz789
AWS_STORAGE_BUCKET_NAME=my-bucket
AWS_S3_ENDPOINT_URL=https://abc123.r2.cloudflarestorage.com
```

Static files (`css/`, `js/`, `images/`) still use `collectstatic` and are not affected by the media storage setting.

If `DJANGO_MEDIA_STORAGE` is not set or is `local`, the local `media/` directory is used. Missing `AWS_STORAGE_BUCKET_NAME` in S3 mode will cause a clear startup error.
