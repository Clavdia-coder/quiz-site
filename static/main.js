// Scroll reveal
const revealItems = document.querySelectorAll('[data-reveal]');
if (revealItems.length) {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        entry.target.classList.add('is-visible');
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.12, rootMargin: '0px 0px -8% 0px' }
  );
  revealItems.forEach((item, index) => {
    item.style.transitionDelay = `${Math.min(index * 40, 200)}ms`;
    observer.observe(item);
  });
}

// FAQ accordion — close others when one opens
const faqItems = document.querySelectorAll('.faq-list details');
faqItems.forEach((item) => {
  item.addEventListener('toggle', () => {
    if (!item.open) return;
    faqItems.forEach((other) => {
      if (other !== item) other.open = false;
    });
  });
});

// Hamburger menu
const burger = document.getElementById('nav-burger');
const navLinks = document.getElementById('nav-links');
if (burger && navLinks) {
  burger.addEventListener('click', () => {
    const isOpen = navLinks.classList.toggle('is-open');
    burger.classList.toggle('is-open', isOpen);
    burger.setAttribute('aria-expanded', String(isOpen));
  });
  // Close on nav link click
  navLinks.querySelectorAll('a').forEach((link) => {
    link.addEventListener('click', () => {
      navLinks.classList.remove('is-open');
      burger.classList.remove('is-open');
      burger.setAttribute('aria-expanded', 'false');
    });
  });
}

// Particles
const particleCanvas = document.getElementById('particles');
const prefersReducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

if (particleCanvas && !prefersReducedMotion) {
  const ctx = particleCanvas.getContext('2d');
  const particles = [];
  let animationFrame = null;
  const pointer = { x: window.innerWidth / 2, y: window.innerHeight / 2 };

  const resize = () => {
    particleCanvas.width = window.innerWidth;
    particleCanvas.height = window.innerHeight;
  };

  const build = () => {
    particles.length = 0;
    const count = window.innerWidth < 760 ? 16 : 28;
    for (let i = 0; i < count; i++) {
      particles.push({
        x: Math.random() * particleCanvas.width,
        y: Math.random() * particleCanvas.height,
        radius: Math.random() * 4 + 1.5,
        speedX: (Math.random() - 0.5) * 0.1,
        speedY: (Math.random() - 0.5) * 0.1,
        depth: Math.random() * 0.8 + 0.2,
        streak: Math.random() > 0.78,
        streakLen: Math.random() * 32 + 16,
      });
    }
  };

  const draw = () => {
    ctx.clearRect(0, 0, particleCanvas.width, particleCanvas.height);
    const offX = (pointer.x / window.innerWidth - 0.5) * 28;
    const offY = (pointer.y / window.innerHeight - 0.5) * 28;

    particles.forEach((p) => {
      p.x += p.speedX;
      p.y += p.speedY;
      if (p.x < -20) p.x = particleCanvas.width + 20;
      if (p.x > particleCanvas.width + 20) p.x = -20;
      if (p.y < -20) p.y = particleCanvas.height + 20;
      if (p.y > particleCanvas.height + 20) p.y = -20;

      const dx = p.x + offX * p.depth;
      const dy = p.y + offY * p.depth;
      const warm = p.depth > 0.55;

      ctx.beginPath();
      ctx.arc(dx, dy, p.radius, 0, Math.PI * 2);
      const g = ctx.createRadialGradient(dx, dy, 0, dx, dy, p.radius * 4);
      if (warm) {
        g.addColorStop(0, `rgba(232,52,26,${0.14 + p.depth * 0.14})`);
        g.addColorStop(1, 'rgba(232,52,26,0)');
      } else {
        g.addColorStop(0, `rgba(245,162,32,${0.16 + p.depth * 0.16})`);
        g.addColorStop(1, 'rgba(245,162,32,0)');
      }
      ctx.fillStyle = g;
      ctx.fill();

      if (p.streak) {
        ctx.beginPath();
        ctx.moveTo(dx, dy);
        ctx.lineTo(dx + p.streakLen * p.depth, dy - p.streakLen * 0.3 * p.depth);
        ctx.strokeStyle = warm ? 'rgba(232,52,26,0.15)' : 'rgba(245,162,32,0.15)';
        ctx.lineWidth = Math.max(1, p.radius * 0.2);
        ctx.stroke();
      }
    });

    animationFrame = requestAnimationFrame(draw);
  };

  resize();
  build();
  draw();

  window.addEventListener('resize', () => { resize(); build(); });
  window.addEventListener('mousemove', (e) => { pointer.x = e.clientX; pointer.y = e.clientY; });
  window.addEventListener('beforeunload', () => { if (animationFrame) cancelAnimationFrame(animationFrame); });
}
