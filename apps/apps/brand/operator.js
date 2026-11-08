/* ==========================================================================
   Operator paneli - umumiy skript
   Hech qanday kutubxonaga bog'liq emas (jQuery kerak emas).
   Barcha xatti-harakatlar HTML'dagi data-* atributlari orqali ulanadi,
   shuning uchun keyinchalik Django shabloniga o'tkazganda JS o'zgarmaydi.
   ========================================================================== */

(function (window, document) {
    'use strict';

    var Op = {};

    /* ---------------------------------------------------------------------
       1. Kichik yordamchilar
       --------------------------------------------------------------------- */

    function $(selector, scope) {
        return (scope || document).querySelector(selector);
    }

    function $$(selector, scope) {
        return Array.prototype.slice.call((scope || document).querySelectorAll(selector));
    }

    Op.formatNumber = function (value) {
        var n = Math.round(Number(value) || 0);
        return n.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
    };

    Op.formatSom = function (value) {
        return Op.formatNumber(value) + " so'm";
    };

    function toNumber(text) {
        var cleaned = String(text).replace(/[^\d.-]/g, '');
        var n = parseFloat(cleaned);
        return isNaN(n) ? 0 : n;
    }

    function toDateValue(text) {
        var m = String(text).match(/(\d{2})\.(\d{2})\.(\d{4})(?:\s+(\d{2}):(\d{2}))?/);
        if (!m) {
            return 0;
        }
        return new Date(+m[3], +m[2] - 1, +m[1], +(m[4] || 0), +(m[5] || 0)).getTime();
    }

    function norm(text) {
        return String(text || '').toLowerCase().replace(/\s+/g, ' ').trim();
    }

    var ICONS = {
        success: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.1V12a10 10 0 1 1-5.9-9.1"/><polyline points="22 4 12 14.1 9 11.1"/></svg>',
        error: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
        warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
        info: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>'
    };

    /* ---------------------------------------------------------------------
       2. Xabarnomalar (toast)
       --------------------------------------------------------------------- */

    Op.toast = function (text, options) {
        options = options || {};
        var type = options.type || 'info';
        var box = $('.op-toasts');

        if (!box) {
            box = document.createElement('div');
            box.className = 'op-toasts';
            document.body.appendChild(box);
        }

        var el = document.createElement('div');
        el.className = 'op-toast is-' + type;
        el.setAttribute('role', 'status');
        // Matn mijoz kiritgan ma'lumotni (ism) o'z ichiga oladi - faqat
        // textContent orqali qo'yiladi, HTML sifatida hech qachon emas (XSS).
        el.innerHTML = ICONS[type] || ICONS.info;
        var body = document.createElement('div');
        if (options.title) {
            var titleEl = document.createElement('b');
            titleEl.textContent = options.title;
            body.appendChild(titleEl);
        }
        var textEl = document.createElement('p');
        textEl.textContent = text;
        body.appendChild(textEl);
        el.appendChild(body);
        box.appendChild(el);

        var hide = function () {
            el.classList.add('is-hiding');
            setTimeout(function () {
                if (el.parentNode) {
                    el.parentNode.removeChild(el);
                }
            }, 200);
        };

        el.addEventListener('click', hide);
        setTimeout(hide, options.timeout || 3200);
    };

    /* ---------------------------------------------------------------------
       3. Yon menyu (kichik ekranlarda ochiladi/yopiladi)
       --------------------------------------------------------------------- */

    function initSidebar() {
        var sidebar = $('.op-sidebar');
        var burger = $('[data-op-burger]');
        var backdrop = $('.op-sidebar-backdrop');

        if (!sidebar || !burger) {
            return;
        }

        function close() {
            sidebar.classList.remove('is-open');
            if (backdrop) {
                backdrop.classList.remove('is-open');
            }
        }

        burger.addEventListener('click', function () {
            sidebar.classList.toggle('is-open');
            if (backdrop) {
                backdrop.classList.toggle('is-open', sidebar.classList.contains('is-open'));
            }
        });

        if (backdrop) {
            backdrop.addEventListener('click', close);
        }

        $$('.op-nav a', sidebar).forEach(function (link) {
            link.addEventListener('click', close);
        });
    }

    /* ---------------------------------------------------------------------
       4. Soat va ish holati kaliti
       --------------------------------------------------------------------- */

    function initClock() {
        var el = $('[data-op-clock]');
        if (!el) {
            return;
        }

        function pad(value) {
            return String(value).length < 2 ? '0' + value : String(value);
        }

        function tick() {
            var now = new Date();
            el.textContent = pad(now.getHours()) + ':' + pad(now.getMinutes()) + ':' + pad(now.getSeconds());
        }

        tick();
        setInterval(tick, 1000);
    }

    function initWorkSwitch() {
        var sw = $('[data-op-switch]');
        if (!sw) {
            return;
        }

        var label = $('.op-switch-text', sw);
        var dot = $('.op-me .op-dot');
        var dotText = $('[data-op-status-text]');

        sw.addEventListener('click', function () {
            var off = sw.classList.toggle('is-off');

            if (label) {
                label.textContent = off ? 'Tanaffusda' : 'Ish rejimi';
            }
            if (dot) {
                dot.classList.toggle('is-off', off);
            }
            if (dotText) {
                dotText.textContent = off ? 'Tanaffusda' : 'Onlayn';
            }

            Op.toast(
                off ? "Tanaffus rejimi yoqildi - yangi buyurtmalar boshqa operatorlarga yo'naltiriladi."
                    : 'Ish rejimi yoqildi - yangi buyurtmalar sizga ham keladi.',
                {type: off ? 'warning' : 'success'}
            );
        });
    }

    /* ---------------------------------------------------------------------
       5. Modal oynalar
       Ochish:  <button data-op-modal-open="#modalId" data-fill-id="1042">
       Yopish:  <button data-op-modal-close>
       --------------------------------------------------------------------- */

    Op.openModal = function (selector, data) {
        var modal = typeof selector === 'string' ? $(selector) : selector;
        if (!modal) {
            return;
        }

        if (data) {
            Object.keys(data).forEach(function (key) {
                $$('[data-op-fill="' + key + '"]', modal).forEach(function (el) {
                    if (el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA') {
                        el.value = data[key];
                    } else {
                        el.textContent = data[key];
                    }
                });
            });
        }

        modal.classList.add('is-open');
        document.body.style.overflow = 'hidden';

        var focusable = $('input, select, textarea, button', modal);
        if (focusable) {
            focusable.focus();
        }
    };

    Op.closeModal = function (modal) {
        modal = modal || $('.op-modal.is-open');
        if (!modal) {
            return;
        }
        modal.classList.remove('is-open');
        document.body.style.overflow = '';
    };

    function initModals() {
        document.addEventListener('click', function (e) {
            var opener = e.target.closest('[data-op-modal-open]');
            if (opener) {
                e.preventDefault();
                var payload = {};
                Object.keys(opener.dataset).forEach(function (key) {
                    if (key.indexOf('fill') === 0 && key.length > 4) {
                        payload[key.slice(4).toLowerCase()] = opener.dataset[key];
                    }
                });
                var selector = opener.getAttribute('data-op-modal-open');

                var action = opener.getAttribute('data-action');
                if (action) {
                    var form = $(selector + ' form');
                    if (form) {
                        form.setAttribute('action', action);
                    }
                }

                Op.openModal(selector, payload);
                return;
            }

            if (e.target.closest('[data-op-modal-close]')) {
                e.preventDefault();
                Op.closeModal(e.target.closest('.op-modal'));
                return;
            }

            if (e.target.classList.contains('op-modal')) {
                Op.closeModal(e.target);
            }
        });

        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape') {
                Op.closeModal();
            }
        });
    }

    /* ---------------------------------------------------------------------
       6. Jadval: qidiruv + filtr + holat menyusi + saralash + sahifalash
       --------------------------------------------------------------------- */

    function OpTable(root) {
        this.root = root;
        this.table = $('table', root);
        this.tbody = this.table ? $('tbody', this.table) : null;
        if (!this.tbody) {
            return;
        }

        this.rows = $$('tr[data-status]', this.tbody);
        this.noResultRow = $('tr.op-no-result', this.tbody);
        this.serverSearch = root.getAttribute('data-op-search-mode') === 'server';
        this.search = this.serverSearch ? null : $('[data-op-search]', root);
        this.filters = $$('[data-op-filter]', root);
        this.tabs = $$('[data-op-tab]', root);
        this.perPage = parseInt(root.getAttribute('data-op-per-page'), 10) || 10;
        this.page = 1;
        this.visible = this.rows.slice();

        this.bind();
        this.apply();
    }

    OpTable.prototype.bind = function () {
        var self = this;

        if (this.search) {
            this.search.addEventListener('input', function () {
                self.page = 1;
                self.apply();
            });
        }

        this.filters.forEach(function (select) {
            select.addEventListener('change', function () {
                self.page = 1;
                self.apply();
            });
        });

        this.tabs.forEach(function (tab) {
            tab.addEventListener('click', function () {
                self.tabs.forEach(function (other) {
                    other.classList.remove('is-active');
                });
                tab.classList.add('is-active');
                self.page = 1;
                self.apply();
            });
        });

        $$('thead th', this.table).forEach(function (th, index) {
            if (!th.hasAttribute('data-sort')) {
                return;
            }
            th.addEventListener('click', function () {
                self.sort(th, index);
            });
        });

        var pager = $('[data-op-pages]', this.root);
        if (pager) {
            pager.addEventListener('click', function (e) {
                var btn = e.target.closest('button[data-page]');
                if (!btn || btn.disabled) {
                    return;
                }
                self.page = parseInt(btn.getAttribute('data-page'), 10);
                self.render();
                self.table.scrollIntoView({behavior: 'smooth', block: 'start'});
            });
        }
    };

    OpTable.prototype.activeTab = function () {
        var active = this.tabs.filter(function (tab) {
            return tab.classList.contains('is-active');
        })[0];
        return active ? active.getAttribute('data-op-tab') : 'all';
    };

    OpTable.prototype.matches = function (row) {
        var tab = this.activeTab();
        if (tab && tab !== 'all' && row.getAttribute('data-status') !== tab) {
            return false;
        }

        for (var i = 0; i < this.filters.length; i++) {
            var select = this.filters[i];
            var value = select.value;
            if (!value || value === 'all') {
                continue;
            }
            var key = select.getAttribute('data-op-filter');
            if (norm(row.getAttribute('data-' + key)) !== norm(value)) {
                return false;
            }
        }

        if (this.search && this.search.value.trim()) {
            var needle = norm(this.search.value);
            var haystack = norm(row.textContent + ' ' + (row.getAttribute('data-search') || ''));
            if (haystack.indexOf(needle) === -1) {
                return false;
            }
        }

        return true;
    };

    OpTable.prototype.apply = function () {
        var self = this;
        this.visible = this.rows.filter(function (row) {
            return self.matches(row);
        });
        this.render();
    };

    OpTable.prototype.render = function () {
        var self = this;
        var total = this.visible.length;
        var pages = Math.max(1, Math.ceil(total / this.perPage));

        if (this.page > pages) {
            this.page = pages;
        }

        var start = (this.page - 1) * this.perPage;
        var end = start + this.perPage;

        this.rows.forEach(function (row) {
            row.style.display = 'none';
        });

        this.visible.slice(start, end).forEach(function (row) {
            row.style.display = '';
        });

        if (this.noResultRow) {
            this.noResultRow.classList.toggle('is-shown', total === 0);
        }

        var info = $('[data-op-page-info]', this.root);
        if (info) {
            info.textContent = total === 0
                ? 'Natija topilmadi'
                : (start + 1) + '-' + Math.min(end, total) + ' / jami ' + total + ' ta';
        }

        var pager = $('[data-op-pages]', this.root);
        if (pager) {
            pager.innerHTML = this.pagerHtml(pages);
        }

        this.tabs.forEach(function (tab) {
            var counter = $('i', tab);
            if (!counter) {
                return;
            }
            var status = tab.getAttribute('data-op-tab');
            counter.textContent = self.rows.filter(function (row) {
                return status === 'all' || row.getAttribute('data-status') === status;
            }).length;
        });
    };

    OpTable.prototype.pagerHtml = function (pages) {
        if (pages <= 1) {
            return '';
        }

        var html = '<button class="op-page" data-page="' + (this.page - 1) + '"'
            + (this.page === 1 ? ' disabled' : '') + ' aria-label="Oldingi">&lsaquo;</button>';

        for (var i = 1; i <= pages; i++) {
            var near = Math.abs(i - this.page) <= 1 || i === 1 || i === pages;
            if (!near) {
                if (i === 2 || i === pages - 1) {
                    html += '<button class="op-page" disabled>&hellip;</button>';
                }
                continue;
            }
            html += '<button class="op-page' + (i === this.page ? ' is-active' : '')
                + '" data-page="' + i + '">' + i + '</button>';
        }

        html += '<button class="op-page" data-page="' + (this.page + 1) + '"'
            + (this.page === pages ? ' disabled' : '') + ' aria-label="Keyingi">&rsaquo;</button>';

        return html;
    };

    OpTable.prototype.sort = function (th, index) {
        var type = th.getAttribute('data-sort');
        var asc = !th.classList.contains('sort-asc');

        $$('thead th', this.table).forEach(function (other) {
            other.classList.remove('sort-asc', 'sort-desc');
        });
        th.classList.add(asc ? 'sort-asc' : 'sort-desc');

        function cellValue(row) {
            var cell = row.cells[index];
            if (!cell) {
                return '';
            }
            var raw = cell.getAttribute('data-value');
            var text = raw !== null ? raw : cell.textContent.trim();

            if (type === 'num') {
                return toNumber(text);
            }
            if (type === 'date') {
                return raw !== null ? toNumber(raw) : toDateValue(text);
            }
            return norm(text);
        }

        this.rows.sort(function (a, b) {
            var va = cellValue(a);
            var vb = cellValue(b);
            if (va < vb) {
                return asc ? -1 : 1;
            }
            if (va > vb) {
                return asc ? 1 : -1;
            }
            return 0;
        });

        var tbody = this.tbody;
        this.rows.forEach(function (row) {
            tbody.appendChild(row);
        });
        if (this.noResultRow) {
            tbody.appendChild(this.noResultRow);
        }

        this.page = 1;
        this.apply();
    };

    Op.tables = [];

    function initTables() {
        $$('[data-op-table]').forEach(function (root) {
            Op.tables.push(new OpTable(root));
        });
    }

    Op.refreshTables = function () {
        Op.tables.forEach(function (table) {
            if (table && table.rows) {
                table.apply();
            }
        });
    };

    Op.dropRow = function (row) {
        Op.tables.forEach(function (table) {
            if (!table || !table.rows) {
                return;
            }
            var index = table.rows.indexOf(row);
            if (index !== -1) {
                table.rows.splice(index, 1);
            }
        });

        if (row.parentNode) {
            row.parentNode.removeChild(row);
        }
        Op.refreshTables();
    };

    /* ---------------------------------------------------------------------
       7. Miqdor tanlagich va narx hisobi (buyurtma sahifasi)
       --------------------------------------------------------------------- */

    function initQty() {
        var box = $('[data-op-qty]');
        if (!box) {
            return;
        }

        var input = $('input', box);
        var minus = $('[data-op-qty-minus]', box);
        var plus = $('[data-op-qty-plus]', box);
        var max = parseInt(input.getAttribute('max'), 10) || 99;

        function set(name, value) {
            var el = $('[data-op-price="' + name + '"]');
            if (el) {
                el.textContent = Op.formatSom(value);
            }
        }

        function recalc() {
            var qty = Math.min(max, Math.max(1, parseInt(input.value, 10) || 1));
            input.value = qty;

            var price = parseFloat(box.getAttribute('data-price')) || 0;
            var discount = parseFloat(box.getAttribute('data-discount')) || 0;
            var delivery = parseFloat(box.getAttribute('data-delivery')) || 0;
            var unit = price - discount;

            set('unit', unit);
            set('subtotal', price * qty);
            set('discount', discount * qty);
            set('delivery', delivery);
            set('total', unit * qty + delivery);

            var qtyOut = $('[data-op-price="qty"]');
            if (qtyOut) {
                qtyOut.textContent = qty + ' dona';
            }

            if (plus) {
                plus.disabled = qty >= max;
            }
            if (minus) {
                minus.disabled = qty <= 1;
            }
        }

        if (minus) {
            minus.addEventListener('click', function () {
                input.value = (parseInt(input.value, 10) || 1) - 1;
                recalc();
            });
        }

        if (plus) {
            plus.addEventListener('click', function () {
                input.value = (parseInt(input.value, 10) || 1) + 1;
                recalc();
            });
        }

        input.addEventListener('input', recalc);
        input.addEventListener('blur', recalc);
        recalc();
    }

    /* ---------------------------------------------------------------------
       8. Izoh maydoni: belgilar hisobi va tayyor iboralar
       --------------------------------------------------------------------- */

    function initComment() {
        var area = $('[data-op-comment]');
        if (!area) {
            return;
        }

        var counter = $('[data-op-comment-count]');
        var max = parseInt(area.getAttribute('maxlength'), 10) || 500;

        function update() {
            if (!counter) {
                return;
            }
            counter.textContent = area.value.length + ' / ' + max;
            counter.parentNode.classList.toggle('is-limit', area.value.length >= max);
        }

        area.addEventListener('input', update);
        update();

        $$('[data-op-chip]').forEach(function (chip) {
            chip.addEventListener('click', function () {
                var text = chip.getAttribute('data-op-chip');
                area.value = area.value.trim() ? area.value.trim() + ' ' + text : text;
                area.focus();
                update();
            });
        });
    }

    /* ---------------------------------------------------------------------
       9. Viloyat -> tuman bog'liqligi
       --------------------------------------------------------------------- */

    function initRegions() {
        var regionSelect = $('[data-op-region]');
        var districtSelect = $('[data-op-district]');
        var data = window.OP_REGIONS;

        if (!regionSelect || !districtSelect || !data) {
            return;
        }

        var preselected = districtSelect.getAttribute('data-selected');

        function fill() {
            var districts = data[regionSelect.value] || [];
            districtSelect.innerHTML = '<option value="">Tumanni tanlang</option>';

            districts.forEach(function (pair) {
                var opt = document.createElement('option');
                opt.value = pair[0];
                opt.textContent = pair[1];
                if (preselected && String(pair[0]) === String(preselected)) {
                    opt.selected = true;
                }
                districtSelect.appendChild(opt);
            });

            districtSelect.disabled = districts.length === 0;
        }

        regionSelect.addEventListener('change', function () {
            preselected = null;
            fill();
        });

        fill();
    }

    /* ---------------------------------------------------------------------
       10. Klaviatura yorliqlari
       --------------------------------------------------------------------- */

    function initShortcuts() {
        document.addEventListener('keydown', function (e) {
            var tag = (e.target.tagName || '').toLowerCase();
            var typing = tag === 'input' || tag === 'textarea' || tag === 'select';

            if (e.key === '/' && !typing) {
                var search = $('[data-op-search]');
                if (search) {
                    e.preventDefault();
                    search.focus();
                }
            }
        });
    }

    /* ---------------------------------------------------------------------
       11. Jadval qatoriga bosilganda buyurtmani ochish
       --------------------------------------------------------------------- */

    function initRowLinks() {
        $$('tr[data-href]').forEach(function (row) {
            row.style.cursor = 'pointer';
            row.addEventListener('click', function (e) {
                if (e.target.closest('button, a, input, select, label')) {
                    return;
                }
                window.location.href = row.getAttribute('data-href');
            });
        });
    }

    /* ---------------------------------------------------------------------
       12. Umumiy navbat: buyurtmani o'ziga olish (self-assign)
       Endi qatorni ro'yxatdan olib tashlashdan oldin backendga haqiqiy
       so'rov (order-take) yuboriladi. Serverdan muvaffaqiyatsiz javob
       kelsa (masalan, boshqa operator ulgurgan bo'lsa), qator baribir
       yangilanadi va operator xabardor qilinadi.
       --------------------------------------------------------------------- */

    function getCsrfToken() {
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    function initPool() {
        var pool = $('[data-op-pool]');
        if (!pool) {
            return;
        }

        function updateCount() {
            var left = $$('tr[data-order]', pool).filter(function (row) {
                return !row.classList.contains('is-taken');
            }).length;

            $$('[data-op-count]').forEach(function (el) {
                el.textContent = left;
            });
        }

        function bumpMyOrdersCount() {
            $$('[data-op-my-count]').forEach(function (el) {
                el.textContent = (parseInt(el.textContent, 10) || 0) + 1;
            });
        }

        /**
         * Buyurtmani o'ziga oladi: avval backendga POST yuboradi, so'ng
         * natijaga qarab qatorni ro'yxatdan chiqaradi yoki xatoni ko'rsatadi.
         */
        function take(btn, row) {
            if (!row || row.classList.contains('is-taken')) {
                return;
            }

            var url = btn.getAttribute('data-take-url');
            if (!url) {
                return;
            }

            btn.disabled = true;

            fetch(url, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                credentials: 'same-origin'
            })
                .then(function (response) {
                    return response.json().then(function (data) {
                        return {ok: response.ok, data: data};
                    });
                })
                .then(function (result) {
                    if (result.ok && result.data.success) {
                        row.classList.add('is-taken');
                        updateCount();
                        bumpMyOrdersCount();

                        Op.toast(
                            (row.getAttribute('data-order') || 'Buyurtma') + " sizga biriktirildi va "
                            + "\"Buyurtmalarim\" ro'yxatiga o'tdi. "
                            + (row.getAttribute('data-customer') || 'Mijoz') + "ga qo'ng'iroq qiling.",
                            {type: 'success', title: 'Buyurtma olindi'}
                        );

                        setTimeout(function () {
                            Op.dropRow(row);
                        }, 400);
                    } else {
                        btn.disabled = false;
                        Op.toast(
                            (result.data && result.data.message) || "Bu buyurtmani boshqa operator allaqachon oldi.",
                            {type: 'error', title: 'Amal bajarilmadi'}
                        );
                        // Boshqa operator olib ulgurgan bo'lsa, qatorni ro'yxatdan olib tashlaymiz
                        setTimeout(function () {
                            Op.dropRow(row);
                            updateCount();
                        }, 600);
                    }
                })
                .catch(function () {
                    btn.disabled = false;
                    Op.toast("Server bilan bog'lanishda xatolik yuz berdi.", {type: 'error'});
                });
        }

        pool.addEventListener('click', function (e) {
            var btn = e.target.closest('[data-op-take]');
            if (!btn) {
                return;
            }
            e.preventDefault();
            take(btn, btn.closest('tr'));
        });

        var nextBtn = $('[data-op-take-next]');
        if (nextBtn) {
            nextBtn.addEventListener('click', function () {
                var row = $$('tr[data-order]', pool).filter(function (item) {
                    return !item.classList.contains('is-taken') && item.style.display !== 'none';
                })[0];

                if (!row) {
                    Op.toast("Navbatda buyurtma qolmadi.", {type: 'info'});
                    return;
                }
                var btn = $('[data-op-take]', row);
                if (btn) {
                    take(btn, row);
                }
            });
        }

        updateCount();
    }

    /* ---------------------------------------------------------------------
       13. Pul va telefon raqamlarini formatlash (bazadan xom holda keladi)
       --------------------------------------------------------------------- */

    function initMoneyFormat() {
        $$('[data-op-money]').forEach(function (el) {
            var raw = el.getAttribute('data-value');
            el.textContent = Op.formatNumber(raw);
        });
    }

    function initPhoneFormat() {
        $$('[data-op-phone]').forEach(function (el) {
            var digits = (el.textContent || '').replace(/[^\d+]/g, '');
            var m = digits.match(/^(\+998)(\d{2})(\d{3})(\d{2})(\d{2})$/);
            if (m) {
                el.textContent = m[1] + ' ' + m[2] + ' ' + m[3] + ' ' + m[4] + ' ' + m[5];
            }
        });
    }

    /* ---------------------------------------------------------------------
       14. Ishga tushirish
       --------------------------------------------------------------------- */

    /* Django xabarlari (saqlandi, noto'g'ri holat va h.k.) toast sifatida chiqadi */
    function showFlashMessages() {
        var types = { success: 'success', error: 'error', danger: 'error', warning: 'warning' };
        document.querySelectorAll('template[data-flash]').forEach(function (node) {
            Op.toast(node.content.textContent, { type: types[node.getAttribute('data-flash')] || 'info' });
        });
    }

    function init() {
        showFlashMessages();
        initSidebar();
        initClock();
        initWorkSwitch();
        initModals();
        initTables();
        initQty();
        initComment();
        initRegions();
        initShortcuts();
        initRowLinks();
        initPool();
        initMoneyFormat();
        initPhoneFormat();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    window.Op = Op;

})(window, document);
