# FemDes Webstore

Concise runbook for local startup, admin access, and deployment.

## Run Locally

```bash
cd /home/zahid/Projects/Zahid/Fem_des_shop/kaira-1.0.0
cp .env.example .env
conda activate femdes
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py runserver 127.0.0.1:8000
```

Open:

- Storefront: `http://127.0.0.1:8000/`
- Shop: `http://127.0.0.1:8000/shop/`
- Admin: `http://127.0.0.1:8000/admin/`

Useful checks:

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Without activating conda:

```bash
conda run -n femdes python manage.py runserver 127.0.0.1:8000
```

## Admin Panel

Create an admin user:

```bash
python manage.py createsuperuser
```

Start the server and open:

```text
http://127.0.0.1:8000/admin/
```

Use the admin panel to manage:

- site settings;
- categories;
- products, prices, stock, images, measurements;
- discounts;
- orders;
- customization requests;
- newsletter subscribers;
- customer users.

Optional demo data:

```bash
python manage.py seed_demo_store
```

## Deploy

Use any Python/Django host with PostgreSQL, for example Render, Railway, Fly.io,
or a VPS.

Add Gunicorn before deploying if it is not already in `requirements.txt`:

```bash
python -m pip install gunicorn
python -m pip freeze | grep gunicorn >> requirements.txt
```

Production environment variables:

```env
DJANGO_SECRET_KEY=<long-random-secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=<your-hostname>,<your-domain>
DJANGO_CSRF_TRUSTED_ORIGINS=https://<your-hostname>,https://<your-domain>
DATABASE_URL=<postgres-database-url>
```

Build command:

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput
```

Start command:

```bash
python manage.py migrate && gunicorn femdes_site.wsgi:application
```

After deployment, create the production admin user from the host shell:

```bash
python manage.py createsuperuser
```

Then open:

```text
https://<your-hostname>/admin/
```

## Uploaded Images In Production

For persistent product/admin uploads, use S3-compatible storage:

```env
DJANGO_MEDIA_STORAGE=s3
AWS_ACCESS_KEY_ID=<access-key>
AWS_SECRET_ACCESS_KEY=<secret-key>
AWS_STORAGE_BUCKET_NAME=<bucket>
AWS_S3_REGION_NAME=<region>
AWS_S3_ENDPOINT_URL=<optional-provider-endpoint>
AWS_S3_CUSTOM_DOMAIN=<optional-cdn-domain>
```

Local development can keep:

```env
DJANGO_MEDIA_STORAGE=local
```
