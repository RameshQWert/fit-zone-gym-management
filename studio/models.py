from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = "admin", "Admin"
        TRAINER = "trainer", "Trainer"
        MEMBER = "member", "Member"

    role = models.CharField(max_length=12, choices=Roles.choices, default=Roles.MEMBER)
    phone = models.CharField(max_length=24, blank=True)

    @property
    def display_name(self):
        return self.get_full_name().strip() or self.username


class MembershipPlan(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(unique=True)
    price = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(0)])
    duration_days = models.PositiveIntegerField(default=30)
    description = models.CharField(max_length=180)
    features = models.JSONField(default=list, blank=True)
    popular = models.BooleanField(default=False)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "price"]

    def __str__(self):
        return self.name


class Trainer(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="trainer_profile")
    name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    specialties = models.CharField(max_length=180, help_text="Separate specialties with commas")
    bio = models.TextField(blank=True)
    years_experience = models.PositiveSmallIntegerField(default=1)
    photo_url = models.URLField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["user__first_name", "user__last_name"]

    def __str__(self):
        return self.name or (self.user.display_name if self.user else "Trainer")


class Equipment(models.Model):
    class Categories(models.TextChoices):
        CARDIO = "cardio", "Cardio"
        STRENGTH = "strength", "Strength"
        FREE_WEIGHTS = "free-weights", "Free Weights"
        MACHINES = "machines", "Machines"
        ACCESSORIES = "accessories", "Accessories"
        OTHER = "other", "Other"

    name = models.CharField(max_length=100)
    brand = models.CharField(max_length=80, blank=True)
    quantity = models.CharField(max_length=60, help_text="For example: 20 units or 5-150 lbs")
    category = models.CharField(max_length=20, choices=Categories.choices, default=Categories.CARDIO)
    image_url = models.URLField(blank=True)
    description = models.CharField(max_length=240, blank=True)
    active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class FitnessClass(models.Model):
    class Levels(models.TextChoices):
        ALL = "all", "All levels"
        BEGINNER = "beginner", "Beginner"
        INTERMEDIATE = "intermediate", "Intermediate"
        ADVANCED = "advanced", "Advanced"

    title = models.CharField(max_length=100)
    category = models.CharField(max_length=60, default="Training")
    trainer = models.ForeignKey(Trainer, on_delete=models.SET_NULL, null=True, blank=True, related_name="classes")
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    duration_minutes = models.PositiveSmallIntegerField(default=45)
    capacity = models.PositiveSmallIntegerField(default=16)
    level = models.CharField(max_length=16, choices=Levels.choices, default=Levels.ALL)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["starts_at"]

    def __str__(self):
        return self.title

    @property
    def spots_left(self):
        active_bookings = getattr(self, "booked_count", None)
        if active_bookings is None:
            active_bookings = self.bookings.filter(status=Booking.Status.BOOKED).count()
        return max(self.capacity - active_bookings, 0)


class Booking(models.Model):
    class Status(models.TextChoices):
        BOOKED = "booked", "Booked"
        CANCELLED = "cancelled", "Cancelled"

    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="bookings")
    fitness_class = models.ForeignKey(FitnessClass, on_delete=models.CASCADE, related_name="bookings")
    booked_at = models.DateTimeField(default=timezone.now)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.BOOKED)

    class Meta:
        ordering = ["fitness_class__starts_at"]
        constraints = [models.UniqueConstraint(fields=["member", "fitness_class"], name="one_booking_per_member_class")]

    def __str__(self):
        return f"{self.member} · {self.fitness_class}"


class AttendanceRecord(models.Model):
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance_records")
    checked_in_at = models.DateTimeField(default=timezone.now)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    note = models.CharField(max_length=180, blank=True)

    class Meta:
        ordering = ["-checked_in_at"]

    def __str__(self):
        return f"{self.member} · {self.checked_in_at:%b %d, %Y}"

    @property
    def is_checked_in(self):
        return self.checked_out_at is None


class Payment(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Paid"
        PENDING = "pending", "Pending"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    class Methods(models.TextChoices):
        CASH = "cash", "Cash"
        CARD = "card", "Card"
        UPI = "upi", "UPI"
        ONLINE = "online", "Online"
        OTHER = "other", "Other"

    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")
    plan = models.ForeignKey(MembershipPlan, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    amount = models.DecimalField(max_digits=9, decimal_places=2, validators=[MinValueValidator(0)])
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PAID)
    method = models.CharField(max_length=12, choices=Methods.choices, default=Methods.UPI)
    reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-paid_at"]

    def __str__(self):
        return f"{self.member} · {self.amount} · {self.get_status_display()}"


class Subscription(models.Model):
    member = models.ForeignKey(User, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(MembershipPlan, on_delete=models.PROTECT, related_name="subscriptions")
    started_at = models.DateField(default=timezone.localdate)
    ends_at = models.DateField()
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-started_at"]

    def __str__(self):
        return f"{self.member} · {self.plan}"

    @property
    def is_current(self):
        return self.active and self.ends_at >= timezone.localdate()


class ContactInquiry(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=24, blank=True)
    message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)
    resolved = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} · {self.created_at:%b %d}"


class NewsletterSignup(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(default=timezone.now)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-subscribed_at"]

    def __str__(self):
        return self.email


class SitePage(models.Model):
    slug = models.SlugField(unique=True)
    name = models.CharField(max_length=80)
    hero_title = models.CharField(max_length=180, blank=True)
    hero_subtitle = models.TextField(blank=True)
    body = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name
