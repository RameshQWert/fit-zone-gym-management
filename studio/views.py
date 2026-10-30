import csv
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import AccountForm, AttendanceForm, BookingForm, ContactForm, ContactInquiryForm, EmailAuthenticationForm, EquipmentForm, FitnessClassForm, MembershipPlanForm, MemberForm, NewsletterForm, NewsletterSignupForm, PaymentForm, RegistrationForm, SitePageForm, SubscriptionForm, TrainerForm
from .models import AttendanceRecord, Booking, ContactInquiry, Equipment, FitnessClass, MembershipPlan, NewsletterSignup, Payment, SitePage, Subscription, Trainer, User
from .nosql import is_configured, record_event


def page_content(slug):
    return SitePage.objects.filter(slug=slug, active=True).first()


def home(request):
    record_event("page_view", user_id=request.user.pk if request.user.is_authenticated else None, path=request.path, metadata={"page": "home"})
    now = timezone.now()
    context = {
        "classes": FitnessClass.objects.filter(active=True, starts_at__gte=now).select_related("trainer")[:3],
        "trainers": Trainer.objects.filter(active=True)[:4],
        "plans": MembershipPlan.objects.filter(active=True)[:3],
        "member_count": User.objects.filter(role=User.Roles.MEMBER, is_active=True).count(),
        "class_count": FitnessClass.objects.filter(active=True).count(),
    }
    context["page"] = page_content("home")
    return render(request, "studio/home.html", context)


def about(request):
    return render(request, "studio/about.html", {"trainers": Trainer.objects.filter(active=True)[:3], "page": page_content("about")})


def programs(request):
    return render(request, "studio/programs.html", {"classes": FitnessClass.objects.filter(active=True, starts_at__gte=timezone.now()).select_related("trainer")[:9], "page": page_content("programs")})


def facilities(request):
    equipment = [{
        "name": item.name, "brand": item.brand, "count": item.quantity,
        "category": item.category, "category_name": item.get_category_display(),
        "image_url": item.image_url or "https://images.unsplash.com/photo-1534438327276-14e5300c3a48?auto=format&fit=crop&w=760&q=82",
        "description": item.description,
    } for item in Equipment.objects.filter(active=True)]
    groups = []
    categories = [
        ("cardio", "Cardio", "🏃"),
        ("strength", "Strength", "💪"),
        ("free-weights", "Free Weights", "🏋️"),
        ("machines", "Machines", "⚙️"),
        ("accessories", "Accessories", "🎯"),
        ("other", "Other", "📦"),
    ]
    for key, title, icon in categories:
        items = [item for item in equipment if item["category"] == key]
        groups.append({"key": key, "title": title, "icon": icon, "items": items})
    return render(request, "studio/facilities.html", {
        "facility_groups": groups,
        "equipment_count": len(equipment),
        "cardio_count": len(next(group["items"] for group in groups if group["key"] == "cardio")),
        "strength_count": sum(len(group["items"]) for group in groups if group["key"] in {"strength", "free-weights", "machines"}),
        "zone_count": sum(bool(group["items"]) for group in groups),
        "page": page_content("facilities"),
    })

def trainers(request):
    trainer_list = list(Trainer.objects.filter(active=True).prefetch_related("classes"))
    specialty_terms = ("strength", "yoga", "hiit", "nutrition", "boxing", "cardio", "wellness", "crossfit", "swimming")
    specialties = set()
    total_experience = 0
    for trainer in trainer_list:
        text = trainer.specialties.lower()
        trainer.filter_categories = [term for term in specialty_terms if term in text] or ["wellness"]
        trainer.class_count = trainer.classes.filter(active=True, starts_at__gte=timezone.now()).count()
        specialties.update(trainer.filter_categories)
        total_experience += trainer.years_experience
    return render(request, "studio/trainers.html", {
        "trainers": trainer_list,
        "trainer_count": len(trainer_list),
        "specialty_count": len(specialties),
        "average_experience": round(total_experience / len(trainer_list), 1) if trainer_list else 0,
        "classes_taught": sum(trainer.class_count for trainer in trainer_list),
        "specialty_filters": [(term, term.title()) for term in specialty_terms if term in specialties],
        "page": page_content("trainers"),
    })


def schedule(request):
    all_classes = FitnessClass.objects.filter(active=True, starts_at__gte=timezone.now()).select_related("trainer").annotate(
        booked_count=Count("bookings", filter=Q(bookings__status=Booking.Status.BOOKED))
    )
    category = request.GET.get("category", "")
    selected_trainer = request.GET.get("trainer", "")
    day_values = [("monday", "Monday", 2), ("tuesday", "Tuesday", 3), ("wednesday", "Wednesday", 4), ("thursday", "Thursday", 5), ("friday", "Friday", 6), ("saturday", "Saturday", 7), ("sunday", "Sunday", 1)]
    day = request.GET.get("day", "monday").lower()
    if day not in {value[0] for value in day_values}:
        day = "monday"
    day_number = next(value[2] for value in day_values if value[0] == day)
    classes = all_classes.filter(starts_at__week_day=day_number)
    if category:
        classes = classes.filter(category__iexact=category)
    if selected_trainer.isdigit():
        classes = classes.filter(trainer_id=selected_trainer)
    categories = FitnessClass.objects.filter(active=True).values_list("category", flat=True).distinct()
    day_counts = {key: 0 for key, _, _ in day_values}
    for fitness_class in all_classes:
        local_day = timezone.localtime(fitness_class.starts_at).strftime("%A").lower()
        day_counts[local_day] += 1
    week_days = [{"value": key, "label": label, "count": day_counts[key]} for key, label, _ in day_values]
    return render(request, "studio/schedule.html", {
        "classes": classes,
        "categories": categories,
        "selected_category": category,
        "selected_trainer": selected_trainer,
        "trainers": Trainer.objects.filter(active=True),
        "week_days": week_days,
        "selected_day": day,
        "week_total": all_classes.count(),
        "page": page_content("schedule"),
    })


def pricing(request):
    plans = list(MembershipPlan.objects.filter(active=True))
    feature_names = []
    for plan in plans:
        for feature in plan.features or []:
            if feature not in feature_names:
                feature_names.append(feature)
    compare_rows = [
        {"name": feature, "included": [feature in (plan.features or []) for plan in plans]}
        for feature in feature_names
    ]
    return render(request, "studio/pricing.html", {"plans": plans, "compare_rows": compare_rows, "page": page_content("pricing")})


def contact(request):
    form = ContactForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        ContactInquiry.objects.create(**form.cleaned_data)
        messages.success(request, "Thanks for reaching out. Our team will be in touch soon.")
        return redirect("contact")
    return render(request, "studio/contact.html", {"form": form, "page": page_content("contact")})


class FitZoneLoginView(LoginView):
    template_name = "registration/login.html"
    authentication_form = EmailAuthenticationForm

    def form_valid(self, form):
        if not self.request.POST.get("remember_me"):
            self.request.session.set_expiry(0)
        return super().form_valid(form)

    def get_success_url(self):
        # Send members and trainers back to the public home page after sign-in.
        # Admin accounts use the management dashboard, including when they sign
        # in through the general login form.
        if is_admin(self.request.user):
            return "/admin/"
        return "/"


class AdminLoginView(FitZoneLoginView):
    template_name = "registration/admin_login.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and is_admin(request.user):
            return redirect("admin_dashboard")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        if not is_admin(form.get_user()):
            form.add_error(None, "This sign-in is for FitZone administrators.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self):
        return "/admin/"


@require_POST
def newsletter_signup(request):
    form = NewsletterForm(request.POST)
    if form.is_valid():
        _, created = NewsletterSignup.objects.get_or_create(email=form.cleaned_data["email"])
        if created:
            record_event("newsletter_signup", user_id=request.user.pk if request.user.is_authenticated else None, path=request.path)
            messages.success(request, "You're on the FitZone list. Watch your inbox for good things.")
        else:
            messages.info(request, "That email is already subscribed to FitZone updates.")
    else:
        messages.error(request, "Enter a valid email address to join the list.")
    return redirect("home")


def register(request):
    if request.user.is_authenticated:
        return redirect("admin_dashboard" if is_admin(request.user) else "home")
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user =         form.save()
        record_event("newsletter_signup", user_id=request.user.pk if request.user.is_authenticated else None, path=request.path)
        login(request, user)
        messages.success(request, "Your Fit Zone account is ready.")
        return redirect("home")
    return render(request, "registration/register.html", {"form": form})


def is_admin(user):
    return user.is_authenticated and (user.is_superuser or user.role == User.Roles.ADMIN)


@login_required
def dashboard(request):
    user = request.user
    if is_admin(user):
        return redirect("admin_dashboard")
    if user.role == User.Roles.TRAINER:
        trainer = Trainer.objects.filter(user=user).first()
        classes = FitnessClass.objects.filter(trainer=trainer, starts_at__gte=timezone.now()).annotate(booking_count=Count("bookings", filter=Q(bookings__status=Booking.Status.BOOKED))) if trainer else FitnessClass.objects.none()
        return render(request, "studio/dashboard_trainer.html", {"trainer": trainer, "classes": classes})
    bookings = Booking.objects.filter(member=user, status=Booking.Status.BOOKED, fitness_class__starts_at__gte=timezone.now()).select_related("fitness_class", "fitness_class__trainer")
    subscription = user.subscriptions.filter(active=True, ends_at__gte=timezone.localdate()).select_related("plan").first()
    upcoming = FitnessClass.objects.filter(active=True, starts_at__gte=timezone.now()).exclude(bookings__member=user, bookings__status=Booking.Status.BOOKED).select_related("trainer")[:4]
    return render(request, "studio/dashboard_member.html", {"bookings": bookings, "subscription": subscription, "classes": upcoming})


@login_required
@require_POST
def book_class(request, class_id):
    if request.user.role != User.Roles.MEMBER:
        raise PermissionDenied
    with transaction.atomic():
        fitness_class = get_object_or_404(FitnessClass.objects.select_for_update(), pk=class_id, active=True)
        if fitness_class.starts_at <= timezone.now():
            messages.error(request, "This class has already started.")
        else:
            booking = Booking.objects.select_for_update().filter(member=request.user, fitness_class=fitness_class).first()
            if booking and booking.status == Booking.Status.BOOKED:
                messages.info(request, "You already have a spot in this class.")
            elif fitness_class.spots_left <= 0:
                messages.error(request, "This class is full. Try another session.")
            elif booking:
                booking.status = Booking.Status.BOOKED
                booking.booked_at = timezone.now()
                booking.save(update_fields=["status", "booked_at"])
                messages.success(request, f"You're booked for {fitness_class.title}.")
            else:
                Booking.objects.create(member=request.user, fitness_class=fitness_class)
                messages.success(request, f"You're booked for {fitness_class.title}.")
    return redirect("dashboard")


@login_required
@require_POST
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, pk=booking_id, member=request.user, status=Booking.Status.BOOKED)
    booking.status = Booking.Status.CANCELLED
    booking.save(update_fields=["status"])
    messages.success(request, "Your class booking was cancelled.")
    return redirect("dashboard")


@login_required
@require_POST
def subscribe(request, plan_id):
    if request.user.role != User.Roles.MEMBER:
        raise PermissionDenied
    plan = get_object_or_404(MembershipPlan, pk=plan_id, active=True)
    today = timezone.localdate()
    Subscription.objects.filter(member=request.user, active=True).update(active=False)
    Subscription.objects.create(member=request.user, plan=plan, started_at=today, ends_at=today + timedelta(days=plan.duration_days))
    messages.success(request, f"Your {plan.name} membership is now active.")
    return redirect("dashboard")


MANAGEMENT = {
    "members": {"title": "Members", "singular": "member", "form": MemberForm, "query": lambda: User.objects.filter(role=User.Roles.MEMBER).order_by("first_name", "last_name"), "search": ("first_name", "last_name", "email", "phone"), "status": "is_active"},
    "accounts": {"title": "Accounts", "singular": "account", "form": AccountForm, "query": lambda: User.objects.order_by("role", "first_name", "last_name"), "search": ("first_name", "last_name", "email", "username", "phone", "role"), "status": "is_active"},
    "trainers": {"title": "Trainers", "singular": "trainer", "form": TrainerForm, "query": lambda: Trainer.objects.select_related("user").all(), "search": ("name", "email", "specialties"), "status": "active"},
    "equipment": {"title": "Equipment", "singular": "equipment item", "form": EquipmentForm, "query": lambda: Equipment.objects.all(), "search": ("name", "brand", "category", "description"), "status": "active"},
    "attendance": {"title": "Attendance", "singular": "attendance record", "form": AttendanceForm, "query": lambda: AttendanceRecord.objects.select_related("member").all(), "search": ("member__first_name", "member__last_name", "member__email", "note"), "status": "attendance"},
    "classes": {"title": "Classes", "singular": "class", "form": FitnessClassForm, "query": lambda: FitnessClass.objects.select_related("trainer").annotate(booked_count=Count("bookings", filter=Q(bookings__status=Booking.Status.BOOKED))), "search": ("title", "category", "trainer__name"), "status": "active"},
    "plans": {"title": "Membership plans", "singular": "membership plan", "form": MembershipPlanForm, "query": lambda: MembershipPlan.objects.all(), "search": ("name", "description"), "status": "active"},
    "bookings": {"title": "Bookings", "singular": "booking", "form": BookingForm, "query": lambda: Booking.objects.select_related("member", "fitness_class").all(), "search": ("member__first_name", "member__last_name", "member__email", "fitness_class__title"), "status": "status"},
    "subscriptions": {"title": "Subscriptions", "singular": "subscription", "form": SubscriptionForm, "query": lambda: Subscription.objects.select_related("member", "plan").all(), "search": ("member__first_name", "member__last_name", "member__email", "plan__name"), "status": "active"},
    "inquiries": {"title": "Messages", "singular": "message", "form": ContactInquiryForm, "query": lambda: ContactInquiry.objects.all(), "search": ("name", "email", "phone", "message"), "status": "resolved"},
    "newsletter": {"title": "Newsletter signups", "singular": "signup", "form": NewsletterSignupForm, "query": lambda: NewsletterSignup.objects.all(), "search": ("email",), "status": "active"},
    "payments": {"title": "Payments", "singular": "payment", "form": PaymentForm, "query": lambda: Payment.objects.select_related("member", "plan").all(), "search": ("member__first_name", "member__last_name", "member__email", "plan__name", "reference", "method"), "status": "payment_status"},
    "pages": {"title": "Site pages", "singular": "site page", "form": SitePageForm, "query": lambda: SitePage.objects.all(), "search": ("slug", "name", "hero_title", "hero_subtitle", "body"), "status": "active"},
}


def admin_required(view):
    from functools import wraps

    @wraps(view)
    @login_required(login_url="admin_login")
    def wrapped(request, *args, **kwargs):
        if not is_admin(request.user):
            raise PermissionDenied
        return view(request, *args, **kwargs)
    return wrapped


def _admin_dashboard_context():
    today = timezone.localdate()
    week_start = today - timedelta(days=6)
    raw_activity = Booking.objects.filter(booked_at__date__range=(week_start, today)).values("booked_at__date").annotate(total=Count("id"))
    activity_counts = {row["booked_at__date"]: row["total"] for row in raw_activity}
    max_activity = max(activity_counts.values(), default=0)
    booking_week = []
    for offset in range(7):
        day = week_start + timedelta(days=offset)
        count = activity_counts.get(day, 0)
        booking_week.append({"label": day.strftime("%a"), "count": count, "height": max(12, round(count / max_activity * 100)) if max_activity else 12})
    distribution = MembershipPlan.objects.annotate(active_count=Count("subscriptions", filter=Q(subscriptions__active=True, subscriptions__ends_at__gte=today))).order_by("sort_order", "name")
    return {
        "nosql_configured": is_configured(),
        "member_count": User.objects.filter(role=User.Roles.MEMBER, is_active=True).count(),
        "account_count": User.objects.count(),
        "trainer_count": Trainer.objects.filter(active=True).count(),
        "class_count": FitnessClass.objects.filter(active=True).count(),
        "booking_count": Booking.objects.filter(status=Booking.Status.BOOKED).count(),
        "subscription_count": Subscription.objects.filter(active=True, ends_at__gte=today).count(),
        "upcoming": FitnessClass.objects.filter(active=True, starts_at__gte=timezone.now()).count(),
        "pending_inquiries": ContactInquiry.objects.filter(resolved=False).count(),
        "month_revenue": Payment.objects.filter(status=Payment.Status.PAID, paid_at__date__range=(today.replace(day=1), today)).aggregate(total=Sum("amount"))["total"] or 0,
        "today_checkins": AttendanceRecord.objects.filter(checked_in_at__date=today).count(),
        "recent_bookings": Booking.objects.select_related("member", "fitness_class").order_by("-booked_at")[:6],
        "recent_inquiries": ContactInquiry.objects.order_by("-created_at")[:5],
        "booking_week": booking_week,
        "week_booking_count": sum(day["count"] for day in booking_week),
        "membership_distribution": distribution,
    }


@admin_required
def admin_dashboard(request):
    return render(request, "studio/dashboard_admin.html", _admin_dashboard_context())


@admin_required
def admin_reports(request):
    today = timezone.localdate()
    month_start = today.replace(day=1)
    month_paid = Payment.objects.filter(status=Payment.Status.PAID, paid_at__date__range=(month_start, today))
    return render(request, "studio/admin_reports.html", {
        "month_paid": month_paid.aggregate(total=Sum("amount"))["total"] or 0,
        "month_payment_count": month_paid.count(),
        "all_paid": Payment.objects.filter(status=Payment.Status.PAID).aggregate(total=Sum("amount"))["total"] or 0,
        "all_payment_count": Payment.objects.count(),
        "attendance_week": AttendanceRecord.objects.filter(checked_in_at__date__gte=today - timedelta(days=6), checked_in_at__date__lte=today).count(),
        "active_subscriptions": Subscription.objects.filter(active=True, ends_at__gte=today).count(),
        "member_count": User.objects.filter(role=User.Roles.MEMBER, is_active=True).count(),
        "booking_count": Booking.objects.filter(status=Booking.Status.BOOKED).count(),
        "payment_statuses": Payment.objects.values("status").annotate(total=Count("id")).order_by("status"),
    })


def _csv_export(resource, objects):
    columns = {
        "members": ("Name", "Email", "Phone", "Active"),
        "accounts": ("Name", "Username", "Email", "Phone", "Role", "Active"),
        "trainers": ("Name", "Email", "Specialties", "Experience", "Active"),
        "equipment": ("Equipment", "Brand", "Quantity", "Category", "Description", "Active"),
        "classes": ("Class", "Category", "Trainer", "Starts at", "Duration", "Capacity", "Active"),
        "plans": ("Plan", "Price", "Duration days", "Active"),
        "bookings": ("Member", "Email", "Class", "Class starts at", "Status", "Booked at"),
        "subscriptions": ("Member", "Email", "Plan", "Started", "Ends", "Active"),
        "inquiries": ("Name", "Email", "Phone", "Message", "Received", "Resolved"),
        "newsletter": ("Email", "Subscribed at", "Active"),
        "attendance": ("Member", "Email", "Checked in", "Checked out", "Note"),
        "payments": ("Member", "Email", "Plan", "Amount", "Status", "Method", "Reference", "Paid at"),
    }
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="fitzone-{resource}.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(columns[resource])
    for item in objects:
        if resource in {"members", "accounts"}:
            row = [item.display_name, item.username, item.email, item.phone, item.get_role_display(), item.is_active] if resource == "accounts" else [item.display_name, item.email, item.phone, item.is_active]
        elif resource == "trainers":
            row = [item.name or item.user, item.email, item.specialties, item.years_experience, item.active]
        elif resource == "equipment":
            row = [item.name, item.brand, item.quantity, item.get_category_display(), item.description, item.active]
        elif resource == "classes":
            row = [item.title, item.category, item.trainer, item.starts_at, item.duration_minutes, item.capacity, item.active]
        elif resource == "plans":
            row = [item.name, item.price, item.duration_days, item.active]
        elif resource == "bookings":
            row = [item.member.display_name, item.member.email, item.fitness_class.title, item.fitness_class.starts_at, item.get_status_display(), item.booked_at]
        elif resource == "subscriptions":
            row = [item.member.display_name, item.member.email, item.plan.name, item.started_at, item.ends_at, item.active]
        elif resource == "inquiries":
            row = [item.name, item.email, item.phone, item.message, item.created_at, item.resolved]
        elif resource == "attendance":
            row = [item.member.display_name, item.member.email, item.checked_in_at, item.checked_out_at or "", item.note]
        elif resource == "payments":
            row = [item.member.display_name, item.member.email, item.plan or "", item.amount, item.get_status_display(), item.get_method_display(), item.reference, item.paid_at]
        else:
            row = [item.email, item.subscribed_at, item.active]
        writer.writerow(row)
    return response


@admin_required
def manage_list(request, resource):
    config = MANAGEMENT.get(resource)
    if config is None:
        raise PermissionDenied
    objects = config["query"]()
    query = request.GET.get("q", "").strip()
    if query:
        search = Q()
        for field in config["search"]:
            search |= Q(**{f"{field}__icontains": query})
        objects = objects.filter(search)
    status = request.GET.get("status", "")
    if status and config.get("status"):
        status_field = config["status"]
        if status_field in {"status", "payment_status"}:
            objects = objects.filter(status=status)
        elif status_field == "attendance":
            if status == "checked-in":
                objects = objects.filter(checked_out_at__isnull=True)
            elif status == "checked-out":
                objects = objects.filter(checked_out_at__isnull=False)
        else:
            objects = objects.filter(**{status_field: status == "active"})
    objects = objects.distinct()
    if request.GET.get("format") == "csv":
        return _csv_export(resource, objects)
    return render(request, "studio/admin_manage_list.html", {
        "resource": resource, "title": config["title"], "singular": config["singular"],
        "objects": objects, "query": query, "status": status, "status_filter": config.get("status"),
        "record_count": objects.count(),
    })


@admin_required
def manage_form(request, resource, pk=None):
    config = MANAGEMENT.get(resource)
    if config is None:
        raise PermissionDenied
    instance = get_object_or_404(config["query"](), pk=pk) if pk is not None else None
    form = config["form"](request.POST or None, instance=instance)
    if request.method == "POST" and resource == "accounts" and instance and instance.pk == request.user.pk:
        remains_admin = request.POST.get("role") == User.Roles.ADMIN or instance.is_superuser
        if not remains_admin or not request.POST.get("is_active"):
            form.add_error(None, "You cannot remove your own active administrator access.")
    if request.method == "POST" and resource == "accounts" and instance and is_admin(instance):
        remains_admin = (request.POST.get("role") == User.Roles.ADMIN or instance.is_superuser) and bool(request.POST.get("is_active"))
        active_admin_count = User.objects.filter(is_active=True).filter(Q(role=User.Roles.ADMIN) | Q(is_superuser=True)).distinct().count()
        if active_admin_count <= 1 and not remains_admin:
            form.add_error(None, "Keep at least one active administrator account.")
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        if resource == "members" and item.pk is None:
            item.role = User.Roles.MEMBER
        item.save()
        if hasattr(form, "save_m2m"):
            form.save_m2m()
        messages.success(request, f"{config['singular'].capitalize()} saved.")
        return redirect("admin_manage_list", resource=resource)
    return render(request, "studio/admin_manage_form.html", {"resource": resource, "title": config["title"], "singular": config["singular"], "form": form, "editing": instance is not None})


@admin_required
@require_POST
def manage_delete(request, resource, pk):
    config = MANAGEMENT.get(resource)
    if config is None:
        raise PermissionDenied
    item = get_object_or_404(config["query"](), pk=pk)
    if resource == "accounts" and item.pk == request.user.pk:
        messages.error(request, "You cannot delete your own administrator account.")
        return redirect("admin_manage_list", resource=resource)
    active_admin_count = User.objects.filter(is_active=True).filter(Q(role=User.Roles.ADMIN) | Q(is_superuser=True)).distinct().count()
    if resource == "accounts" and is_admin(item) and active_admin_count <= 1:
        messages.error(request, "Keep at least one active administrator account.")
        return redirect("admin_manage_list", resource=resource)
    try:
        item.delete()
        messages.success(request, "Record removed.")
    except ProtectedError:
        messages.error(request, "This plan is in use by a member. Mark it inactive instead of deleting it.")
        return redirect("admin_manage_list", resource=resource)
    return redirect("admin_manage_list", resource=resource)
