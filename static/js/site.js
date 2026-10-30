document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-password-toggle]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = button.closest(".login-input-wrap")?.querySelector("input");
      if (!input) return;
      const show = input.type === "password";
      input.type = show ? "text" : "password";
      button.setAttribute("aria-pressed", String(show));
      button.setAttribute("aria-label", show ? "Hide password" : "Show password");
    });
  });

  document.querySelectorAll("[data-filter-group]").forEach((group) => {
    const controls = [...group.querySelectorAll("[data-filter-control]")];
    const items = [...group.querySelectorAll("[data-filter-item]")];
    const search = group.querySelector("[data-filter-search]");
    const emptyState = group.querySelector("[data-filter-empty]");
    let activeFilter = "all";
    const update = () => {
      const term = search?.value.trim().toLocaleLowerCase() || "";
      let visibleCount = 0;
      items.forEach((item) => {
        const tags = (item.dataset.filterValue || "").toLocaleLowerCase().split(/\s+/);
        const filterMatches = activeFilter === "all" || tags.includes(activeFilter) || (activeFilter === "strength" && tags.some((tag) => ["free-weights", "machines"].includes(tag)));
        const searchMatches = !term || item.textContent.toLocaleLowerCase().includes(term);
        item.hidden = !(filterMatches && searchMatches);
        if (!item.hidden) visibleCount += 1;
      });
      group.querySelectorAll("[data-filter-section]").forEach((section) => {
        section.hidden = !section.querySelector("[data-filter-item]:not([hidden])");
      });
      if (emptyState) emptyState.hidden = visibleCount > 0;
    };
    controls.forEach((control) => control.addEventListener("click", () => {
      activeFilter = control.dataset.filterControl || "all";
      controls.forEach((button) => button.classList.toggle("is-active", button === control));
      update();
    }));
    search?.addEventListener("input", update);
    update();
  });

  const scheduleResults = document.querySelector("[data-schedule-results]");
  if (scheduleResults) {
    document.querySelectorAll("[data-schedule-view]").forEach((button) => button.addEventListener("click", () => {
      const view = button.dataset.scheduleView;
      scheduleResults.dataset.view = view;
      document.querySelectorAll("[data-schedule-view]").forEach((control) => {
        const selected = control === button;
        control.classList.toggle("is-active", selected);
        control.setAttribute("aria-pressed", String(selected));
      });
    }));
  }

  const menuButton = document.querySelector(".menu-toggle");
  const nav = document.querySelector(".main-nav");
  if (menuButton && nav) {
    menuButton.addEventListener("click", () => {
      const expanded = menuButton.getAttribute("aria-expanded") === "true";
      menuButton.setAttribute("aria-expanded", String(!expanded));
      nav.classList.toggle("open", !expanded);
    });
    nav.querySelectorAll("a").forEach((link) => link.addEventListener("click", () => {
      menuButton.setAttribute("aria-expanded", "false");
      nav.classList.remove("open");
    }));
  }

  document.querySelectorAll(".account-menu").forEach((menu) => {
    const trigger = menu.querySelector(".account-trigger");
    const dropdown = menu.querySelector(".account-dropdown");
    if (!trigger || !dropdown) return;
    const close = () => {
      trigger.setAttribute("aria-expanded", "false");
      dropdown.hidden = true;
    };
    trigger.addEventListener("click", () => {
      const open = trigger.getAttribute("aria-expanded") !== "true";
      trigger.setAttribute("aria-expanded", String(open));
      dropdown.hidden = !open;
    });
    document.addEventListener("click", (event) => {
      if (!menu.contains(event.target)) close();
    });
    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") close();
    });
  });

  const hero = document.querySelector("[data-hero-carousel]");
  if (hero) {
    const images = [...hero.querySelectorAll("[data-hero-image]")];
    const dots = [...hero.querySelectorAll("[data-hero-dot]")];
    const firstLine = hero.querySelector("[data-hero-first]");
    const secondLine = hero.querySelector("[data-hero-second]");
    const tagline = hero.querySelector("[data-hero-tagline]");
    const slides = [
      { first: "BECOME", second: "UNSTOPPABLE", tagline: "Join the elite. Train with the best. Achieve the impossible." },
      { first: "IGNITE YOUR", second: "POTENTIAL", tagline: "Transform your body, elevate your mind, unleash your inner champion." },
      { first: "TRAIN WITH", second: "PURPOSE", tagline: "Find your rhythm. Build your strength. Keep moving forward." },
    ];
    let active = 0;
    let timer;
    const showSlide = (index) => {
      active = (index + slides.length) % slides.length;
      images.forEach((image, i) => image.classList.toggle("is-active", i === active));
      dots.forEach((dot, i) => {
        const selected = i === active;
        dot.classList.toggle("is-active", selected);
        dot.setAttribute("aria-pressed", String(selected));
      });
      firstLine.textContent = slides[active].first;
      secondLine.textContent = slides[active].second;
      tagline.textContent = slides[active].tagline;
    };
    const startTimer = () => {
      if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      window.clearInterval(timer);
      timer = window.setInterval(() => showSlide(active + 1), 6500);
    };
    dots.forEach((dot, index) => {
      dot.addEventListener("pointerenter", () => { showSlide(index); startTimer(); });
      dot.addEventListener("click", () => { showSlide(index); startTimer(); });
    });
    hero.addEventListener("mouseenter", () => {
      window.clearInterval(timer);
      showSlide(active + 1);
    });
    hero.addEventListener("mouseleave", startTimer);
    startTimer();
  }

  const revealItems = document.querySelectorAll("[data-reveal]");
  if ("IntersectionObserver" in window && !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    const observer = new IntersectionObserver((entries, instance) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("reveal-visible");
          instance.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: "0px 0px -35px 0px" });
    revealItems.forEach((item) => observer.observe(item));
  } else {
    revealItems.forEach((item) => item.classList.add("reveal-visible"));
  }

  document.querySelectorAll(".flash").forEach((flash) => {
    window.setTimeout(() => {
      flash.style.opacity = "0";
      flash.style.transform = "translateX(12px)";
      window.setTimeout(() => flash.remove(), 300);
    }, 6500);
  });
});
