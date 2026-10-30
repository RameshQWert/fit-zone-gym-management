from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import AttendanceRecord, Booking, ContactInquiry, Equipment, FitnessClass, MembershipPlan, NewsletterSignup, Payment, Subscription, Trainer, User

admin.site.site_header = "Fit Zone Management"
admin.site.site_title = "Fit Zone Admin"
admin.site.index_title = "Keep the good energy moving"


@admin.register(User)
class StudioUserAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (("Fit Zone", {"fields": ("role", "phone")}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Fit Zone", {"fields": ("role", "phone")}),)
    list_display = ("username", "email", "first_name", "last_name", "role", "is_active")
    list_filter = ("role", "is_active")


@admin.register(MembershipPlan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "duration_days", "active", "popular")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Trainer)
class TrainerAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "specialties", "years_experience", "active")


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("name", "brand", "quantity", "category", "active", "sort_order")
    list_filter = ("category", "active")
    search_fields = ("name", "brand", "description")


@admin.register(FitnessClass)
class FitnessClassAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "trainer", "starts_at", "capacity", "active")
    list_filter = ("category", "level", "active")
    search_fields = ("title", "trainer__user__first_name", "trainer__user__last_name")


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("member", "fitness_class", "status", "booked_at")
    list_filter = ("status",)


@admin.register(AttendanceRecord)
class AttendanceAdmin(admin.ModelAdmin):
    list_display = ("member", "checked_in_at", "checked_out_at")
    search_fields = ("member__first_name", "member__last_name", "member__email")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("member", "plan", "amount", "status", "method", "paid_at")
    list_filter = ("status", "method")
    search_fields = ("member__first_name", "member__last_name", "member__email", "reference")


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ("member", "plan", "started_at", "ends_at", "active")
    list_filter = ("active", "plan")


@admin.register(ContactInquiry)
class InquiryAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "created_at", "resolved")
    list_filter = ("resolved",)
    search_fields = ("name", "email", "message")


@admin.register(NewsletterSignup)
class NewsletterSignupAdmin(admin.ModelAdmin):
    list_display = ("email", "subscribed_at", "active")
    list_filter = ("active",)
    search_fields = ("email",)
