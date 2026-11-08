/* ZUNO — umumiy interaktivlik (base.html). Har bir qism tegishli element
   sahifada bo'lmasa hech narsa qilmaydi; listenerlar bir marta, delegatsiya orqali. */
(function () {
    'use strict';

    // Parolni ko'rsatish/yashirish (components/field.html)
    document.addEventListener('click', function (e) {
        var btn = e.target.closest('.zuno-pw-toggle');
        if (!btn) return;
        var input = document.getElementById(btn.getAttribute('aria-controls'));
        if (!input) return;
        var show = input.type === 'password';
        input.type = show ? 'text' : 'password';
        btn.setAttribute('aria-pressed', show ? 'true' : 'false');
        btn.setAttribute('aria-label', show ? 'Parolni yashirish' : "Parolni ko'rsatish");
    });

    document.addEventListener('submit', function (e) {
        var form = e.target;
        // Yuborishdan oldin parollar yana yashiriladi
        form.querySelectorAll('.zuno-pw-toggle[aria-pressed="true"]').forEach(function (btn) {
            btn.click();
        });
        // Haqiqiy so'rov ketayotganini ko'rsatish va ikki marta yuborishning oldini olish
        if (form.hasAttribute('data-loading-form') && !e.defaultPrevented) {
            if (form.dataset.submitting) {
                e.preventDefault();
                return;
            }
            form.dataset.submitting = '1';
            var btn = form.querySelector('[data-loading-text]');
            if (btn) {
                btn.classList.add('is-loading');
                btn.setAttribute('aria-disabled', 'true');
                var label = btn.querySelector('span');
                if (label) label.textContent = btn.getAttribute('data-loading-text');
            }
        }
    });

    // Sahifa "orqaga" tugmasi bilan keshdan qaytsa, tugma yana faol bo'lsin
    window.addEventListener('pageshow', function (e) {
        if (!e.persisted) return;
        document.querySelectorAll('form[data-submitting]').forEach(function (form) {
            delete form.dataset.submitting;
            var btn = form.querySelector('.is-loading');
            if (btn) {
                btn.classList.remove('is-loading');
                btn.removeAttribute('aria-disabled');
            }
        });
    });

    // Saralash tanlanganda forma darhol yuboriladi (JS bo'lmasa <noscript> tugma bor)
    document.addEventListener('change', function (e) {
        var form = e.target.closest('form[data-autosubmit]');
        if (form && e.target.tagName === 'SELECT') form.submit();
    });

    document.addEventListener('DOMContentLoaded', function () {
        // Server tasdiqlagan natija (masalan, buyurtma qabul qilindi) - ekranga olib kelinadi
        var focusEl = document.querySelector('[data-focus-on-load]');
        if (focusEl) {
            focusEl.scrollIntoView({block: 'center'});
            focusEl.focus({preventScroll: true});
        }
        // Xatoli maydon bo'lsa (modal tashqarisida) - birinchisiga fokus
        var invalid = document.querySelector('main [aria-invalid="true"], .pd-order [aria-invalid="true"]');
        if (invalid && !focusEl) {
            invalid.scrollIntoView({block: 'center'});
            invalid.focus({preventScroll: true});
        }

        // Bo'limlarning yumshoq paydo bo'lishi. Kontent JS bo'lmasa ham ko'rinadi:
        // yashiruvchi .is-pending klassini faqat shu skript, ekrandan tashqaridagi elementlarga qo'shadi.
        var items = document.querySelectorAll('.zuno-reveal');
        var reduce = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        if (!items.length || reduce || !('IntersectionObserver' in window)) return;
        var io = new IntersectionObserver(function (entries) {
            entries.forEach(function (entry) {
                if (entry.isIntersecting) {
                    entry.target.classList.add('is-visible');
                    io.unobserve(entry.target);
                }
            });
        }, {rootMargin: '0px 0px -8% 0px'});
        var pending = [];
        items.forEach(function (el) {
            if (el.getBoundingClientRect().top < window.innerHeight) return; // birinchi ekrandagilar darhol ko'rinadi
            el.classList.add('is-pending');
            pending.push(el);
            io.observe(el);
        });

        // Zaxira: tez sakrashda (End tugmasi, havola) observer hech bir kesishishni ko'rmaydi -
        // ekrandan o'tib ketilgan elementlar ham ochiladi. rAF bilan cheklangan, passiv.
        var ticking = false;
        window.addEventListener('scroll', function () {
            if (ticking || !pending.length) return;
            ticking = true;
            requestAnimationFrame(function () {
                pending = pending.filter(function (el) {
                    if (el.getBoundingClientRect().top < window.innerHeight) {
                        el.classList.add('is-visible');
                        io.unobserve(el);
                        return false;
                    }
                    return true;
                });
                ticking = false;
            });
        }, {passive: true});
    });
})();

/* Telefon maydoni: har qanday kiritishni +998 (90) 123-45-67 ko'rinishiga keltiradi. */
(function () {
    'use strict';

    function format(raw) {
        var value = raw.trim();
        var digits = value.replace(/\D/g, '');
        if (digits.indexOf('998') === 0) {
            digits = digits.slice(3);
        } else if (value.charAt(0) === '+') {
            digits = '';  // "+998" prefiksi o'chirilayotgan holat
        }
        digits = digits.slice(0, 9);

        var out = '+998';
        if (digits.length) { out += ' (' + digits.slice(0, 2); }
        if (digits.length >= 2) { out += ')'; }
        if (digits.length > 2) { out += ' ' + digits.slice(2, 5); }
        if (digits.length > 5) { out += '-' + digits.slice(5, 7); }
        if (digits.length > 7) { out += '-' + digits.slice(7, 9); }
        return out;
    }

    document.querySelectorAll('#phone-mask, #register-phone, #order-phone').forEach(function (input) {
        input.setAttribute('inputmode', 'tel');
        input.addEventListener('focus', function () {
            if (!input.value) { input.value = '+998'; }
        });
        input.addEventListener('blur', function () {
            if (input.value === '+998') { input.value = ''; }
        });
        input.addEventListener('input', function () {
            input.value = format(input.value);
        });
    });
}());
