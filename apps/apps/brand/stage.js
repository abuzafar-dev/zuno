/* ZUNO — "sahna" qatlami. Har bir qism tegishli element bo'lmasa hech narsa qilmaydi.
   - Jonli fon: sekin suzuvchi yashil "orb"lar va kengayuvchi halqalar (saai.pro g'oyasi),
     sichqonchaga yumshoq ergashadi; hero ekrandan chiqsa yoki tab yashirilsa to'xtaydi.
   - Hero bosqichma-bosqich yig'iladi (.st-armed -> .is-built).
   - Kategoriyalarda kursor ortidan yuruvchi nur (Magic UI MagicCard g'oyasi).
   - 3D vitrina: kartalar to'plami — surish, ‹ › tugmalari, avto-almashish, klaviatura.
   - Mahsulot kartalari 3D egiladi va yaltiraydi (vanilla-tilt.js g'oyasi).
   - Magnit tugma, raqamlarni sanash (NumberTicker g'oyasi).
   "Harakatni kamaytirish" yoqilgan bo'lsa faqat statik ko'rinish qoladi. */
(function () {
    'use strict';

    var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var finePointer = window.matchMedia('(hover: hover) and (pointer: fine)').matches;

    /* ---------- Jonli fon ---------- */
    function ambientCanvas(hero) {
        var canvas = hero.querySelector('.st-hero__canvas');
        if (!canvas || !canvas.getContext) { return; }
        var ctx = canvas.getContext('2d');
        var dpr = Math.min(window.devicePixelRatio || 1, 2);
        var w = 0, h = 0, frame = 0, raf = null, running = false, visible = true;
        var mouse = { x: 0.5, y: 0.5, tx: 0.5, ty: 0.5 };

        var orbs = [
            { x: 0.78, y: 0.30, r: 0.55, vx: 0.00022, vy: 0.00016, c: [31, 107, 87, 0.42] },
            { x: 0.30, y: 0.75, r: 0.45, vx: -0.00018, vy: 0.00020, c: [168, 213, 188, 0.10] },
            { x: 0.60, y: 0.90, r: 0.50, vx: 0.00015, vy: -0.00017, c: [20, 44, 37, 0.55] }
        ];

        function resize() {
            var box = hero.getBoundingClientRect();
            w = box.width;
            h = box.height;
            canvas.width = Math.round(w * dpr);
            canvas.height = Math.round(h * dpr);
            ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        }

        function draw() {
            frame++;
            mouse.x += (mouse.tx - mouse.x) * 0.045;
            mouse.y += (mouse.ty - mouse.y) * 0.045;
            ctx.clearRect(0, 0, w, h);

            orbs.forEach(function (o) {
                if (!reduce) {
                    o.x += o.vx;
                    o.y += o.vy;
                    if (o.x < 0.1 || o.x > 0.9) { o.vx *= -1; }
                    if (o.y < 0.1 || o.y > 0.9) { o.vy *= -1; }
                }
                var px = (o.x + (mouse.x - 0.5) * 0.08) * w;
                var py = (o.y + (mouse.y - 0.5) * 0.08) * h;
                var r = o.r * Math.max(w, h);
                var g = ctx.createRadialGradient(px, py, 0, px, py, r);
                g.addColorStop(0, 'rgba(' + o.c.join(',') + ')');
                g.addColorStop(1, 'rgba(' + o.c.slice(0, 3).join(',') + ',0)');
                ctx.fillStyle = g;
                ctx.fillRect(0, 0, w, h);
            });

            // Op-art halqalar: vizual (o'ng) tomonda markazlashgan
            var cx = w * 0.74 + (mouse.x - 0.5) * 30;
            var cy = h * 0.48 + (mouse.y - 0.5) * 30;
            var base = (frame * 0.35) % 110;
            var maxR = Math.max(w, h) * 0.75;
            ctx.lineWidth = 1;
            for (var i = 0; i < 7; i++) {
                var rr = base + i * 110;
                var a = 0.07 * (1 - rr / maxR);
                if (a <= 0.004) { continue; }
                ctx.strokeStyle = 'rgba(168, 213, 188,' + a.toFixed(3) + ')';
                ctx.beginPath();
                ctx.arc(cx, cy, rr, 0, Math.PI * 2);
                ctx.stroke();
            }

            if (running) { raf = requestAnimationFrame(draw); }
        }

        function start() {
            if (running || reduce || !visible || document.hidden) { return; }
            running = true;
            raf = requestAnimationFrame(draw);
        }
        function stop() {
            running = false;
            if (raf) { cancelAnimationFrame(raf); raf = null; }
        }

        resize();
        draw();  // bitta statik kadr (reduce bo'lsa ham fon chiroyli turadi)

        var resizeTimer;
        window.addEventListener('resize', function () {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function () { resize(); if (!running) { draw(); } }, 120);
        }, { passive: true });

        if (reduce) { return; }

        if (finePointer) {
            hero.addEventListener('pointermove', function (e) {
                var box = hero.getBoundingClientRect();
                mouse.tx = (e.clientX - box.left) / box.width;
                mouse.ty = (e.clientY - box.top) / box.height;
            }, { passive: true });
        }

        document.addEventListener('visibilitychange', function () {
            if (document.hidden) { stop(); } else { start(); }
        });

        if ('IntersectionObserver' in window) {
            new IntersectionObserver(function (entries) {
                visible = entries[0].isIntersecting;
                if (visible) { start(); } else { stop(); }
            }).observe(hero);
        }
        start();
    }

    /* ---------- Hero yig'ilishi ---------- */
    function buildHero(hero) {
        if (reduce) { return; }
        hero.classList.add('st-armed');
        requestAnimationFrame(function () {
            requestAnimationFrame(function () { hero.classList.add('is-built'); });
        });
    }

    /* ---------- Raqamlarni sanash ---------- */
    function countUp(root) {
        if (reduce) { return; }
        root.querySelectorAll('[data-count]').forEach(function (el, index) {
            var target = parseInt(el.textContent.replace(/\D/g, ''), 10);
            if (!target) { return; }
            var duration = 1100;
            var delay = 500 + index * 120;
            el.textContent = '0';
            setTimeout(function () {
                var t0 = performance.now();
                (function tick(now) {
                    var p = Math.min((now - t0) / duration, 1);
                    el.textContent = String(Math.round(target * (1 - Math.pow(1 - p, 4))));
                    if (p < 1) { requestAnimationFrame(tick); }
                }(t0));
            }, delay);
        });
    }

    /* ---------- Spotlight kartalar ---------- */
    function spotlight() {
        if (!finePointer) { return; }
        var SEL = '.zuno-cat';
        document.querySelectorAll('[data-spotlight]').forEach(function (grid) {
            grid.addEventListener('pointermove', function (e) {
                var card = e.target.closest(SEL);
                if (!card || !grid.contains(card)) { return; }
                var box = card.getBoundingClientRect();
                card.style.setProperty('--st-x', (e.clientX - box.left) + 'px');
                card.style.setProperty('--st-y', (e.clientY - box.top) + 'px');
            }, { passive: true });
        });
    }

    /* ---------- Magnit tugma ---------- */
    function magnets() {
        if (reduce || !finePointer) { return; }
        document.querySelectorAll('.st-magnet').forEach(function (btn) {
            var zone = btn.parentElement;
            zone.addEventListener('pointermove', function (e) {
                var box = btn.getBoundingClientRect();
                var dx = e.clientX - (box.left + box.width / 2);
                var dy = e.clientY - (box.top + box.height / 2);
                var dist = Math.hypot(dx, dy);
                var pull = dist < 120 ? (1 - dist / 120) : 0;
                btn.style.setProperty('--st-mx', (dx * 0.25 * pull).toFixed(1) + 'px');
                btn.style.setProperty('--st-my', (dy * 0.35 * pull).toFixed(1) + 'px');
            }, { passive: true });
            zone.addEventListener('pointerleave', function () {
                btn.style.setProperty('--st-mx', '0px');
                btn.style.setProperty('--st-my', '0px');
            });
        });
    }

    /* ---------- 3D vitrina: kartalar to'plami ---------- */
    function deck(root) {
        var cards = Array.prototype.slice.call(root.querySelectorAll('.st-deck__card'));
        var n = cards.length;
        var stack = root.querySelector('.st-deck__stack');
        var current = root.querySelector('[data-deck-current]');
        var progress = root.querySelector('[data-deck-progress]');
        if (n < 2 || !stack) { return; }
        var active = 0, busy = false, paused = false, inView = true;
        var INTERVAL = 4800, elapsed = 0, last = performance.now();

        function layout() {
            cards.forEach(function (card, i) {
                var k = (i - active + n) % n;
                card.style.setProperty('--k', k);
                card.classList.toggle('is-front', k === 0);
                card.classList.toggle('is-hidden', k > 3);
                // faqat oldingi karta klaviatura va ekran o'quvchisi uchun faol
                card.toggleAttribute('inert', k !== 0);
            });
            if (current) { current.textContent = String(active + 1).padStart(2, '0'); }
        }

        function go(dir) {
            if (busy) { return; }
            busy = true;
            var leaving = cards[active];
            active = (active + dir + n) % n;
            var cls = dir > 0 ? 'is-out' : 'is-in';
            var mover = dir > 0 ? leaving : cards[active];
            if (!reduce) { mover.classList.add(cls); }
            layout();
            elapsed = 0;
            setTimeout(function () { mover.classList.remove(cls); busy = false; }, reduce ? 0 : 620);
        }

        root.querySelector('[data-deck-next]').addEventListener('click', function () { go(1); });
        root.querySelector('[data-deck-prev]').addEventListener('click', function () { go(-1); });
        root.addEventListener('keydown', function (e) {
            if (e.key === 'ArrowRight') { e.preventDefault(); go(1); }
            if (e.key === 'ArrowLeft') { e.preventDefault(); go(-1); }
        });

        // Surish: 50px dan ko'p — almashadi; sudralgan bo'lsa havola ochilmaydi
        var startX = null, moved = 0;
        stack.addEventListener('pointerdown', function (e) { startX = e.clientX; moved = 0; });
        window.addEventListener('pointermove', function (e) {
            if (startX !== null) { moved = Math.max(moved, Math.abs(e.clientX - startX)); }
        }, { passive: true });
        window.addEventListener('pointerup', function (e) {
            if (startX === null) { return; }
            var dx = e.clientX - startX;
            startX = null;
            if (Math.abs(dx) > 50) { go(dx < 0 ? 1 : -1); }
        });
        stack.addEventListener('click', function (e) {
            if (moved > 8) { e.preventDefault(); moved = 0; }
        }, true);

        // Oldingi karta 3D egiladi
        if (finePointer && !reduce) {
            stack.addEventListener('pointermove', function (e) {
                var front = cards[active];
                var box = front.getBoundingClientRect();
                var px = (e.clientX - box.left) / box.width - 0.5;
                var py = (e.clientY - box.top) / box.height - 0.5;
                front.classList.add('is-tilting');
                front.style.setProperty('--ry', (px * 14).toFixed(2) + 'deg');
                front.style.setProperty('--rx', (-py * 10).toFixed(2) + 'deg');
            }, { passive: true });
            stack.addEventListener('pointerleave', function () {
                cards.forEach(function (c) {
                    c.classList.remove('is-tilting');
                    c.style.setProperty('--rx', '0deg');
                    c.style.setProperty('--ry', '0deg');
                });
            });
        }

        // Avto-almashish: sichqoncha ustida, fokusda, ekrandan tashqarida yoki tab yashirin bo'lsa to'xtaydi
        root.addEventListener('pointerenter', function () { paused = true; });
        root.addEventListener('pointerleave', function () { paused = false; });
        root.addEventListener('focusin', function () { paused = true; });
        root.addEventListener('focusout', function () { paused = false; });
        if ('IntersectionObserver' in window) {
            new IntersectionObserver(function (entries) { inView = entries[0].isIntersecting; }).observe(root);
        }

        layout();
        if (reduce) { return; }
        (function tick(now) {
            var dt = now - last;
            last = now;
            if (!paused && inView && !document.hidden) {
                elapsed += dt;
                if (elapsed >= INTERVAL) { go(1); }
            }
            if (progress) { progress.style.setProperty('--p', Math.min(elapsed / INTERVAL, 1).toFixed(3)); }
            requestAnimationFrame(tick);
        }(last));
    }

    /* ---------- 3D egiluvchi kartalar ---------- */
    function tiltCards() {
        if (reduce || !finePointer) { return; }
        var MAX = 7;   // gradus: sezilarli, lekin bosh aylantirmaydi
        document.addEventListener('pointermove', function (e) {
            var card = e.target.closest && e.target.closest('[data-tilt]');
            if (!card) { return; }
            var max = parseFloat(card.getAttribute('data-tilt-max')) || MAX;
            var box = card.getBoundingClientRect();
            var px = (e.clientX - box.left) / box.width;
            var py = (e.clientY - box.top) / box.height;
            if (!card.classList.contains('is-tilting')) {
                card.style.setProperty('--mo-delay', '0ms');
                card.classList.add('is-tilting');
            }
            card.style.setProperty('--ry', ((px - 0.5) * 2 * max).toFixed(2) + 'deg');
            card.style.setProperty('--rx', ((0.5 - py) * 2 * max).toFixed(2) + 'deg');
            card.style.setProperty('--gx', (px * 100).toFixed(1) + '%');
            card.style.setProperty('--gy', (py * 100).toFixed(1) + '%');
        }, { passive: true });
        document.addEventListener('pointerout', function (e) {
            var card = e.target.closest && e.target.closest('[data-tilt]');
            if (!card || (e.relatedTarget && card.contains(e.relatedTarget))) { return; }
            card.classList.remove('is-tilting');
            card.style.setProperty('--rx', '0deg');
            card.style.setProperty('--ry', '0deg');
        });
    }

    /* ---------- Telefonda xarid paneli ---------- */
    function buybar() {
        var bar = document.querySelector('[data-buybar]');
        var form = document.getElementById('buyurtma');
        if (!bar || !form) { return; }
        bar.hidden = false;
        if (!('IntersectionObserver' in window)) { return; }
        // forma ekranda bo'lsa panel kerak emas; boshqa paytda doim qo'l ostida
        new IntersectionObserver(function (entries) {
            bar.classList.toggle('is-away', entries[0].isIntersecting);
        }, { rootMargin: '0px 0px -20% 0px' }).observe(form);
    }

    function init() {
        var hero = document.querySelector('[data-stage]');
        if (hero) {
            ambientCanvas(hero);
            buildHero(hero);
            countUp(hero);
        }
        document.querySelectorAll('[data-deck]').forEach(deck);
        tiltCards();
        buybar();
        spotlight();
        magnets();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}());
