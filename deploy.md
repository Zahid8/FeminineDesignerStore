# Free Deployment Guide

This guide deploys the FemDes Django site for free on PythonAnywhere using:

- PythonAnywhere free web app: `https://<username>.pythonanywhere.com`
- SQLite database file on PythonAnywhere storage
- local uploaded media files on PythonAnywhere storage
- Django admin at `/admin/`

This is suitable for a demo, early store preview, or very small launch. For a
serious production store, move later to paid hosting with managed PostgreSQL and
object storage.

## 1. Prepare The Code Locally

From your computer:

```bash
cd /home/zahid/Projects/Zahid/Fem_des_shop/kaira-1.0.0
python -m pip install -r requirements.txt
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

If the app has demo products/images ready, push the project to GitHub:

```bash
git status
git add .
git commit -m "Prepare FemDes site for deployment"
git branch -M main
git remote add origin https://github.com/<your-github-username>/<repo-name>.git
git push -u origin main
```

If `git remote add origin` says the remote already exists, use:

```bash
git remote set-url origin https://github.com/<your-github-username>/<repo-name>.git
git push -u origin main
```

Do not commit `.env`, `db.sqlite3`, or real customer data.

## 2. Create A Free PythonAnywhere Account

1. Open `https://www.pythonanywhere.com/`.
2. Create a free Beginner account.
3. Choose a username carefully. Your free site URL will be:

```text
https://<username>.pythonanywhere.com
```

In the commands below, replace `USERNAME` with your PythonAnywhere username.

## 3. Open A PythonAnywhere Bash Console

1. Log in to PythonAnywhere.
2. Open the `Consoles` tab.
3. Start a new `Bash` console.

## 4. Clone The Project On PythonAnywhere

In the PythonAnywhere Bash console:

```bash
cd ~
git clone https://github.com/Zahid8/FeminineDesignerStore.git femdes
cd ~/femdes
```

Confirm `manage.py` exists:

```bash
ls manage.py requirements.txt femdes_site/settings.py
```

## 5. Create The Python Virtualenv

Use the newest Python version available in your PythonAnywhere account. This
example uses Python 3.13:

```bash
mkvirtualenv --python=/usr/bin/python3.13 femdes-venv
pip install --upgrade pip
pip install -r requirements.txt
```

If PythonAnywhere says `/usr/bin/python3.13` does not exist, list available
versions:

```bash
ls /usr/bin/python3*
```

Then recreate the virtualenv with an available Python 3 version, for example:

```bash
mkvirtualenv --python=/usr/bin/python3.12 femdes-venv
```

Later, whenever you open a new console, activate the environment with:

```bash
workon femdes-venv
cd ~/femdes
```

## 6. Create The Production `.env`

Generate a Django secret key:

```bash
python - <<'PY'
from django.core.management.utils import get_random_secret_key
print(get_random_secret_key())
PY
```

Create the server `.env` file:

```bash
nano ~/femdes/.env
```

Paste this, replacing `USERNAME` and `PASTE_GENERATED_SECRET_HERE`:

```env
DJANGO_SECRET_KEY=PASTE_GENERATED_SECRET_HERE
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=USERNAME.pythonanywhere.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://USERNAME.pythonanywhere.com
DATABASE_URL=sqlite:////home/USERNAME/femdes/db.sqlite3
DJANGO_MEDIA_STORAGE=local
```

Save in nano:

- press `Ctrl+O`
- press `Enter`
- press `Ctrl+X`

Load the `.env` values into the current Bash console:

```bash
set -a; source ~/femdes/.env; set +a
```

## 7. Run Database And Static Setup

In the PythonAnywhere Bash console:

```bash
workon femdes-venv
cd ~/femdes
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

Optional demo data:

```bash
python manage.py seed_demo_store
```

Run a basic check:

```bash
python manage.py check
```

## 8. Create The Web App

1. Open the PythonAnywhere `Web` tab.
2. Click `Add a new web app`.
3. Choose your free domain:

```text
USERNAME.pythonanywhere.com
```

4. Choose `Manual configuration`.
5. Choose the same Python version used for the virtualenv.
6. Do not choose the default Django wizard for this existing project.

## 9. Set The Virtualenv In The Web Tab

In the PythonAnywhere `Web` tab:

1. Find the `Virtualenv` section.
2. Enter:

```text
/home/USERNAME/.virtualenvs/femdes-venv
```

3. Save.

## 10. Set The Source Code Paths

In the PythonAnywhere `Web` tab, set:

```text
Source code: /home/USERNAME/femdes
Working directory: /home/USERNAME/femdes
```

Replace `USERNAME` with your PythonAnywhere username.

## 11. Edit The WSGI File

In the PythonAnywhere `Web` tab:

1. Find the `Code` section.
2. Click the WSGI configuration file link.
3. Delete the existing contents.
4. Paste this, replacing `USERNAME`:

```python
import os
import sys

from dotenv import load_dotenv

path = "/home/USERNAME/femdes"
if path not in sys.path:
    sys.path.insert(0, path)

load_dotenv(os.path.join(path, ".env"))

os.environ["DJANGO_SETTINGS_MODULE"] = "femdes_site.settings"

from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()
```

5. Save the file.

## 12. Configure Static And Media Files

In the PythonAnywhere `Web` tab, find `Static files`.

Add this static files mapping:

```text
URL:       /static/
Directory: /home/USERNAME/femdes/staticfiles
```

Add this media files mapping:

```text
URL:       /media/
Directory: /home/USERNAME/femdes/media
```

Replace `USERNAME` with your PythonAnywhere username.

## 13. Reload The Website

In the PythonAnywhere `Web` tab:

1. Click `Reload USERNAME.pythonanywhere.com`.
2. Wait for reload to finish.
3. Open:

```text
https://USERNAME.pythonanywhere.com/
```

Admin panel:

```text
https://USERNAME.pythonanywhere.com/admin/
```

Log in with the superuser created in step 7.

## 14. Verify The Live Site

Open these URLs:

```text
https://USERNAME.pythonanywhere.com/
https://USERNAME.pythonanywhere.com/shop/
https://USERNAME.pythonanywhere.com/admin/
```

Check these actions:

1. Storefront loads without a 500 error.
2. CSS and images load.
3. Admin login works.
4. Product list loads.
5. Product detail page loads.
6. Add-to-cart works.
7. Admin product image upload works.
8. Uploaded image URL starts with `/media/`.

If CSS does not load, re-run:

```bash
workon femdes-venv
cd ~/femdes
python manage.py collectstatic --noinput
```

Then reload the PythonAnywhere web app.

## 15. Updating The Live Site Later

After making changes locally:

```bash
git add .
git commit -m "Update FemDes site"
git push
```

On PythonAnywhere Bash:

```bash
workon femdes-venv
cd ~/femdes
git pull
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py check
```

Then open the PythonAnywhere `Web` tab and click `Reload`.

## 16. Common Problems

### 500 Error

Open the PythonAnywhere `Web` tab and check:

- `Error log`
- `Server log`

Most common fixes:

```bash
workon femdes-venv
cd ~/femdes
set -a; source .env; set +a
python manage.py check
python manage.py migrate
```

### DisallowedHost Error

Edit `~/femdes/.env`:

```env
DJANGO_ALLOWED_HOSTS=USERNAME.pythonanywhere.com
```

Then reload the web app.

### CSRF Verification Failed

Edit `~/femdes/.env`:

```env
DJANGO_CSRF_TRUSTED_ORIGINS=https://USERNAME.pythonanywhere.com
```

Then reload the web app.

### Static Files Missing

Confirm this mapping exists in the PythonAnywhere `Web` tab:

```text
/static/ -> /home/USERNAME/femdes/staticfiles
```

Then run:

```bash
workon femdes-venv
cd ~/femdes
python manage.py collectstatic --noinput
```

Reload the web app.

### Uploaded Images Missing

Confirm this mapping exists in the PythonAnywhere `Web` tab:

```text
/media/ -> /home/USERNAME/femdes/media
```

Then reload the web app.

### ModuleNotFoundError

Check the WSGI file has:

```python
path = "/home/USERNAME/femdes"
os.environ["DJANGO_SETTINGS_MODULE"] = "femdes_site.settings"
```

Also check the web app virtualenv is:

```text
/home/USERNAME/.virtualenvs/femdes-venv
```

## 17. Free Hosting Limits To Remember

PythonAnywhere free hosting is enough to put the site online, but it has limits:

- free site URL is `USERNAME.pythonanywhere.com`;
- custom domains require a paid plan;
- free account storage is limited;
- free account has one web app;
- SQLite is acceptable for a small demo but not ideal for a busy store;
- if the store starts receiving real orders, move to managed PostgreSQL and
  production media storage.

## 18. Official References

- PythonAnywhere pricing/free account:
  `https://www.pythonanywhere.com/pricing/`
- PythonAnywhere existing Django deployment:
  `https://help.pythonanywhere.com/pages/DeployExistingDjangoProject/`
- PythonAnywhere environment variables:
  `https://help.pythonanywhere.com/pages/EnvironmentVariables/`
- PythonAnywhere Django static/media files:
  `https://help.pythonanywhere.com/pages/DjangoStaticFiles/`
