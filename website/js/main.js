/**
 * SonoPlex Landing Page JavaScript
 */
document.addEventListener('DOMContentLoaded', () => {
  // ========================================
  // Mobile Navigation Toggle
  // ========================================
  const navToggle = document.querySelector('.nav-toggle');
  const navLinks = document.querySelector('.nav-links');

  if (navToggle && navLinks) {
    navToggle.addEventListener('click', () => {
      navLinks.classList.toggle('active');
      navToggle.classList.toggle('active');
    });

    // Close menu when clicking a link
    navLinks.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        navLinks.classList.remove('active');
        navToggle.classList.remove('active');
      });
    });
  }

  // ========================================
  // Hero Carousel
  // ========================================
  const slides = document.querySelectorAll('.hero-slide');
  const dots = document.querySelectorAll('.slider-dots .dot');
  let slideIndex = 0;
  let slideInterval;

  function showSlide(index) {
    if (slides.length === 0) return;

    slides.forEach(s => s.classList.remove('active'));
    dots.forEach(d => d.classList.remove('active'));

    slideIndex = (index + slides.length) % slides.length;
    slides[slideIndex].classList.add('active');
    if (dots[slideIndex]) {
      dots[slideIndex].classList.add('active');
    }
  }

  function nextSlide() {
    showSlide(slideIndex + 1);
  }

  function startCarousel() {
    slideInterval = setInterval(nextSlide, 5000);
  }

  function stopCarousel() {
    clearInterval(slideInterval);
  }

  // Initialize carousel
  if (slides.length > 0) {
    showSlide(0);
    startCarousel();

    // Dot navigation
    dots.forEach((dot, index) => {
      dot.addEventListener('click', () => {
        stopCarousel();
        showSlide(index);
        startCarousel();
      });
    });

    // Pause on hover
    const slider = document.querySelector('.hero-slider');
    if (slider) {
      slider.addEventListener('mouseenter', stopCarousel);
      slider.addEventListener('mouseleave', startCarousel);
    }
  }

  // ========================================
  // Lightbox
  // ========================================
  const lightbox = document.getElementById('lightbox');
  const lightboxImage = lightbox?.querySelector('.lightbox-image');
  const lightboxCaption = lightbox?.querySelector('.lightbox-caption');
  const lightboxClose = lightbox?.querySelector('.lightbox-close');
  const lightboxPrev = lightbox?.querySelector('.lightbox-prev');
  const lightboxNext = lightbox?.querySelector('.lightbox-next');
  const galleryItems = document.querySelectorAll('.gallery-item');
  let currentLightboxIndex = 0;

  function openLightbox(index) {
    if (!lightbox || galleryItems.length === 0) return;
    currentLightboxIndex = index;
    const item = galleryItems[index];
    const img = item.querySelector('img');
    const caption = item.dataset.caption || '';
    
    // Update lightbox image
    if (lightboxImage && img) {
      lightboxImage.src = img.src;
      lightboxImage.alt = caption;
    }
    if (lightboxCaption) {
      lightboxCaption.textContent = caption;
    }
    
    lightbox.classList.add('active');
    document.body.style.overflow = 'hidden';
  }

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove('active');
    document.body.style.overflow = '';
  }

  function showLightboxSlide(direction) {
    currentLightboxIndex = (currentLightboxIndex + direction + galleryItems.length) % galleryItems.length;
    openLightbox(currentLightboxIndex);
  }

  // Gallery item clicks
  galleryItems.forEach((item, index) => {
    item.addEventListener('click', () => openLightbox(index));
  });

  // Lightbox controls
  if (lightboxClose) {
    lightboxClose.addEventListener('click', closeLightbox);
  }

  if (lightboxPrev) {
    lightboxPrev.addEventListener('click', () => showLightboxSlide(-1));
  }

  if (lightboxNext) {
    lightboxNext.addEventListener('click', () => showLightboxSlide(1));
  }

  // Close on backdrop click
  if (lightbox) {
    lightbox.addEventListener('click', (e) => {
      if (e.target === lightbox) {
        closeLightbox();
      }
    });
  }

  // Keyboard navigation
  document.addEventListener('keydown', (e) => {
    if (!lightbox?.classList.contains('active')) return;
    
    if (e.key === 'Escape') {
      closeLightbox();
    } else if (e.key === 'ArrowLeft') {
      showLightboxSlide(-1);
    } else if (e.key === 'ArrowRight') {
      showLightboxSlide(1);
    }
  });

  // ========================================
  // Install Tabs
  // ========================================
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const tabId = btn.dataset.tab;

      // Remove active from all
      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      // Add active to clicked
      btn.classList.add('active');
      const targetTab = document.getElementById(`tab-${tabId}`);
      if (targetTab) {
        targetTab.classList.add('active');
      }
    });
  });

  // ========================================
  // Copy to Clipboard
  // ========================================
  const copyBtns = document.querySelectorAll('.copy-btn');

  copyBtns.forEach(btn => {
    btn.addEventListener('click', async () => {
      const targetId = btn.dataset.target;
      const targetEl = document.getElementById(targetId);
      const code = targetEl?.querySelector('code')?.textContent;

      if (code) {
        try {
          await navigator.clipboard.writeText(code);
          const span = btn.querySelector('span');
          const originalText = span.textContent;
          span.textContent = 'Copied!';
          btn.classList.add('copied');

          setTimeout(() => {
            span.textContent = originalText;
            btn.classList.remove('copied');
          }, 2000);
        } catch (err) {
          console.error('Failed to copy:', err);
        }
      }
    });
  });
});
