# Fit Zone — Fitness Center Management System

A server-rendered fitness club website and management system built with Python and Django. It includes a full-screen rotating photo hero with hoverable image controls, public pages for the club, facilities, programs, classes, memberships, and a role-aware member, trainer, and admin area.

## Stack

- Python 3.10+
- Django 5.2
- SQLite for local development
- Optional MongoDB event analytics through PyMongo
- Django templates, CSS, and a small amount of vanilla JavaScript

## Run locally

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver
```

Open `http://127.0.0.1:8000/`. Use the superuser account at `/admin/login/` to sign in to the custom admin console; the same account can also access `/django-admin/`. There is no hard-coded default admin account. New public registrations receive the Member role.

`.env.example` documents the supported environment variable names. Django does not load `.env` files by itself, so set `DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, or `DJANGO_ALLOWED_HOSTS` in your shell before starting the app. The built-in key is for local development only. Locally, password reset emails are printed in the server console; configure an email backend for deployment.

## Roles and workflows

- **Members** can create an account, browse the class schedule, reserve or cancel a class, select a membership plan, and review upcoming bookings from `/dashboard/`.
- **Trainers** can see classes assigned to their linked trainer profile. Create a Django user with the Trainer role, then connect it to a Trainer profile in Django admin.
- **Admins** can sign in at `/admin/login/`, review activity on `/admin/`, and add, edit, remove, search, or export accounts, members, trainers, classes, plans, equipment, bookings, attendance, payments, subscriptions, contact messages, and newsletter signups. `/admin/reports/` summarizes saved activity. Django admin is available at `/django-admin/` for the full record interface.

Membership activation is a local demo workflow; it does not process payments. Admin payment entries are manual records only. Contact requests are saved for staff follow-up.
The homepage newsletter form saves unique email signups for staff to review in Django admin.

## Sample content

`python manage.py seed_demo` creates three membership plans, four coach profiles, and six upcoming classes. It can be rerun to refresh that sample content. The command does not create users or passwords.

### Optional NoSQL analytics

The core relational workflows continue to use SQLite. When `MONGODB_URI` is set, the app additionally records lightweight page-view and newsletter events in the MongoDB `events` collection. MongoDB is optional: if it is not installed or unavailable, the website continues operating normally and the admin dashboard displays SQLite mode.

Set these variables in `.env` or the shell before starting the server:

```text
MONGODB_URI=mongodb://127.0.0.1:27017
MONGODB_DATABASE=fitzone
```

## Main routes

| Route | Purpose |
| --- | --- |
| `/` | Landing page |
| `/about/`, `/programs/`, `/facilities/`, `/trainers/` | Club, training, and facility pages |
| `/schedule/`, `/pricing/`, `/contact/` | Classes, memberships, and contact form |
| `/newsletter/` | Save an email address from the homepage newsletter form (POST) |
| `/register/`, `/login/` | Member account access |
| `/password-reset/` | Request a password reset by email |
| `/dashboard/` | Role-aware member, trainer, or admin dashboard |
| `/admin/login/` | Administrator sign-in |
| `/admin/` | Admin dashboard and management navigation |
| `/admin/members/`, `/admin/trainers/`, `/admin/classes/`, `/admin/plans/` | Admin record management |
| `/django-admin/` | Django's full admin interface |

## Production notes

Set a strong `DJANGO_SECRET_KEY`, turn `DJANGO_DEBUG` off, configure `DJANGO_ALLOWED_HOSTS`, use a production database, and serve static assets through a production web server or CDN before deployment. Replace the sample address, phone number, email, prices, and class content with your club’s details. The public-facing layout uses Google Fonts and image URLs from Unsplash.
