from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from studio.models import FitnessClass, MembershipPlan, SitePage, Trainer


class Command(BaseCommand):
    help = "Create sample Fit Zone membership plans, coaches, and upcoming classes."

    def handle(self, *args, **options):
        pages = [
            ("home", "Home page", "Become Unstoppable", "Join the elite. Train with the best. Achieve the impossible."),
            ("about", "About page", "Meet Our Team", "Get to know the coaches who bring expertise, care, and energy to every session."),
            ("programs", "Programs page", "Find Your Training", "Choose a program that fits your goals and keeps you moving."),
            ("facilities", "Facilities page", "Everything You Need", "Explore the equipment and spaces built for your best training."),
            ("trainers", "Trainers page", "Meet Our Team", "Coaches who bring expertise, care, and energy to every session."),
            ("schedule", "Schedule page", "Weekly Timetable", "Plan your week with classes that fit your goals."),
            ("pricing", "Pricing page", "Choose Your Perfect Plan", "No hidden fees. No surprises. Just straightforward pricing for your fitness goals."),
            ("contact", "Contact page", "We'd Love to Hear From You", "Have questions about membership, classes, or personal training? Reach out."),
        ]
        for slug, name, hero_title, hero_subtitle in pages:
            SitePage.objects.update_or_create(slug=slug, defaults={
                "name": name, "hero_title": hero_title, "hero_subtitle": hero_subtitle, "active": True,
            })
        plans = [
            ("Pro", "pro", 999, 30, "Most popular choice for dedicated fitness enthusiasts", [
                "Full gym access 24/7", "All equipment & amenities", "Unlimited group classes",
                "Sauna & steam room", "1 personal training session/month", "Nutrition consultation",
                "Towel service", "Priority booking", "FitZone app premium",
            ], True),
            ("Elite", "elite", 1999, 30, "Premium experience with exclusive perks and personalized attention", [
                "Everything in Pro plan", "Unlimited personal training", "Custom meal plans",
                "Recovery room access", "Private locker", "Complimentary supplements",
                "Priority class booking", "5 guest passes/month", "Exclusive member events",
                "Free parking", "Spa discounts", "24/7 trainer support",
            ], False),
            ("Basic", "basic", 499, 30, "Perfect for beginners starting their fitness journey", [
                "Access to gym facilities", "Basic equipment usage", "2 group classes per week",
                "Locker room access", "Free WiFi", "Fitness assessment",
            ], False),
        ]
        for order, (name, slug, price, days, description, features, popular) in enumerate(plans):
            MembershipPlan.objects.update_or_create(slug=slug, defaults={
                "name": name, "price": price, "duration_days": days,
                "description": description, "features": features,
                "popular": popular, "active": True, "sort_order": order,
            })
        MembershipPlan.objects.exclude(slug__in=[plan[1] for plan in plans]).update(active=False)

        coaches = [
            ("Maya Chen", "maya@fitzone.club", "Strength · mobility", 8, "https://images.unsplash.com/photo-1558611848-73f7eb4001a1?auto=format&fit=crop&w=800&q=80"),
            ("Jordan Ellis", "jordan@fitzone.club", "Conditioning · boxing", 6, "https://images.unsplash.com/photo-1583454110551-21f2fa2afe61?auto=format&fit=crop&w=800&q=80"),
            ("Alex Rivera", "alex@fitzone.club", "Movement · recovery", 10, "https://images.unsplash.com/photo-1518611012118-696072aa579a?auto=format&fit=crop&w=800&q=80"),
            ("Noah Patel", "noah@fitzone.club", "Boxing · conditioning", 9, "https://images.unsplash.com/photo-1517836357463-d25dfeac3438?auto=format&fit=crop&w=800&q=80"),
        ]
        trainers = {}
        for name, email, specialties, years, photo_url in coaches:
            trainers[name] = Trainer.objects.update_or_create(name=name, defaults={
                "email": email, "specialties": specialties,
                "years_experience": years, "photo_url": photo_url, "active": True,
                "bio": "A coach who makes the work feel welcoming, thoughtful, and yours.",
            })[0]

        now = timezone.localtime()
        def next_weekday(weekday, start_time):
            days_ahead = (weekday - now.weekday()) % 7
            if days_ahead == 0 and now.time() >= start_time:
                days_ahead = 7
            return (now + timedelta(days=days_ahead)).date()

        sessions = [
            ("Lift Lab", "Strength", 0, time(6, 0), 45, 14, "intermediate", trainers["Maya Chen"]),
            ("Spin Class", "Cardio", 0, time(7, 30), 45, 25, "all", trainers["Jordan Ellis"]),
            ("Power Yoga", "Mobility", 0, time(9, 0), 60, 20, "all", trainers["Alex Rivera"]),
            ("Box & Burn", "Conditioning", 0, time(17, 30), 45, 12, "intermediate", trainers["Jordan Ellis"]),
            ("Strength Circuit", "Strength", 0, time(19, 0), 45, 16, "beginner", trainers["Maya Chen"]),
            ("Engine Room", "Conditioning", 1, time(7, 30), 40, 12, "all", trainers["Jordan Ellis"]),
            ("Flow & Restore", "Mobility", 2, time(18, 0), 50, 16, "all", trainers["Alex Rivera"]),
            ("Friday Fundamentals", "Strength", 4, time(17, 30), 45, 16, "beginner", trainers["Maya Chen"]),
            ("Sunday Reset", "Mobility", 6, time(9, 0), 55, 16, "all", trainers["Alex Rivera"]),
        ]
        for title, category, weekday, start_time, duration, capacity, level, trainer in sessions:
            date = next_weekday(weekday, start_time)
            starts_at = timezone.make_aware(datetime.combine(date, start_time), timezone.get_current_timezone())
            FitnessClass.objects.update_or_create(title=title, defaults={
                "category": category, "trainer": trainer,
                "description": f"A focused {duration}-minute {category.lower()} session. All you need is a willingness to show up.",
                "starts_at": starts_at, "duration_minutes": duration,
                "capacity": capacity, "level": level, "active": True,
            })
        self.stdout.write(self.style.SUCCESS("Added Pro, Elite, and Basic plans, 4 coaches, and 9 upcoming classes."))
