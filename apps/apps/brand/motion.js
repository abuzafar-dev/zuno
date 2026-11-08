/* ZUNO — jonli harakatlar. Har bir qism element bo'lmasa hech narsa qilmaydi. */
(function () {
    'use strict';

    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function stickyHeader() {
        var header = document.querySelector('.modern-header');
        if (!header) { return; }
        var update = function () { header.classList.toggle('is-scrolled', window.scrollY > 8); };
        window.addEventListener('scroll', update, { passive: true });
        update();
    }

    var CARDS = '.zuno-grid > *, .zuno-cats > *, .ui-prod, .ui-link, .ui-tile, .ui-stat, .pd-card, .zuno-page .zuno-card';

    function enterCards() {
        var cards = Array.prototype.slice.call(document.querySelectorAll(CARDS));
        if (!cards.length || !('IntersectionObserver' in window)) { return; }

        var show = function (card) {
            card.classList.remove('mo-wait');
            card.classList.add('mo-in');
        };
        var observer = new IntersectionObserver(function (entries) {
            var visible = entries.filter(function (entry) { return entry.isIntersecting; });
            visible.forEach(function (entry, index) {
                entry.target.style.setProperty('--mo-delay', Math.min(index, 8) * 55 + 'ms');
                show(entry.target);
                observer.unobserve(entry.target);
            });
        }, { rootMargin: '0px 0px -4% 0px' });

        cards.forEach(function (card) {
            card.classList.add('mo-wait');
            observer.observe(card);
        });

        // Zaxira: tez sakrashda ham hech bir karta yashirin qolmasin
        window.addEventListener('scroll', function revealPassed() {
            var waiting = document.querySelectorAll('.mo-wait');
            if (!waiting.length) {
                window.removeEventListener('scroll', revealPassed);
                return;
            }
            waiting.forEach(function (card) {
                if (card.getBoundingClientRect().bottom < 0) {
                    show(card);
                    observer.unobserve(card);
                }
            });
        }, { passive: true });
    }

    function countUp() {
        document.querySelectorAll('.ui-stat__value').forEach(function (el) {
            var finalText = el.textContent;
            var target = parseInt(finalText.replace(/\D/g, ''), 10);
            if (!target) { return; }
            var suffix = finalText.replace(/[\d\s]/g, '') ? " so'm" : '';
            var started = performance.now();
            var duration = 900;

            (function frame(now) {
                var progress = Math.min((now - started) / duration, 1);
                if (progress === 1) {
                    el.textContent = finalText;
                    return;
                }
                var value = Math.round(target * (1 - Math.pow(1 - progress, 3)));
                el.textContent = String(value).replace(/\B(?=(\d{3})+(?!\d))/g, ' ') + suffix;
                requestAnimationFrame(frame);
            }(started));
        });
    }

    function rotateWords() {
        var el = document.querySelector('[data-rotate]');
        if (!el) { return; }
        var words = el.getAttribute('data-rotate').split('|');
        var index = 0;
        setInterval(function () {
            if (document.hidden) { return; }
            el.classList.add('is-out');
            setTimeout(function () {
                index = (index + 1) % words.length;
                el.textContent = words[index];
                el.classList.remove('is-out');
            }, 280);
        }, 2800);
    }

    function heroParallax() {
        var hero = document.querySelector('.zuno-hero');
        if (!hero || !window.matchMedia('(hover: hover)').matches) { return; }
        var tiles = hero.querySelectorAll('.zuno-hero__tile');
        hero.addEventListener('pointermove', function (e) {
            var box = hero.getBoundingClientRect();
            var x = (e.clientX - box.left) / box.width - 0.5;
            var y = (e.clientY - box.top) / box.height - 0.5;
            tiles.forEach(function (tile, index) {
                var depth = (index + 1) * 12;
                tile.style.setProperty('--mo-x', (x * depth).toFixed(1) + 'px');
                tile.style.setProperty('--mo-y', (y * depth).toFixed(1) + 'px');
            });
        });
    }

    function bumpTotal() {
        var quantity = document.getElementById('quantity');
        var sum = document.querySelector('[data-total="sum"]');
        if (!quantity || !sum) { return; }
        sum.style.display = 'inline-block';
        quantity.addEventListener('change', function () {
            sum.classList.remove('mo-bump');
            void sum.offsetWidth;  // animatsiyani qayta boshlash uchun
            sum.classList.add('mo-bump');
        });
    }

    function init() {
        stickyHeader();
        if (reduce) { return; }
        enterCards();
        countUp();
        rotateWords();
        heroParallax();
        bumpTotal();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}());
