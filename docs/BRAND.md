# ZUNO — brend qo'llanmasi

## Logo fayllari (`apps/apps/brand/`)

| Fayl | Qayerda ishlatiladi |
|---|---|
| `zuno-logo-on-light.svg` | Sayt sarlavhasi (navbar), futer, kirish oynasi |
| `zuno-symbol.svg` | Faqat Z belgisi: operator paneli yon menyusi |
| `zuno-app-icon.svg` | Qorong'i plashkadagi Z: SVG favicon, juda tor ekranlarda navbar |
| `favicon.ico`, `favicon-32.png` | Brauzer yorlig'i |
| `apple-touch-icon.png` (180), `icon-192.png`, `icon-512.png` | iOS / PWA ikonkalari |
| `zuno-og.png` (1200×630), `zuno-og.svg` (manba) | Ijtimoiy tarmoqlarda ulashish rasmi |
| `site.webmanifest` | Veb-manifest (nomi, ikonkalar, theme-color) |
| `zuno.css` | Brend tokenlari (ranglar, radius, soya, fokus) |
| `operator.css`, `operator.js` | Operator panelining yagona uslubi va skripti |
| `fonts/` | Inter shrifti (tashqi CDN'siz ishlaydi) |

Shablonlarda logoni qo'lda yozmang — komponentdan foydalaning:

```django
{% include "components/logo.html" with on="light" height=30 %}
{% include "components/logo.html" with compact=True height=32 %} {# faqat belgi #}
```

Logo SVG'lari shriftga bog'liq emas (harflar path sifatida chizilgan), shuning
uchun har qanday kompyuterda bir xil ko'rinadi. Raster ikonkalar `zuno-app-icon.svg`
va `zuno-og.svg` dan yaratilgan; SVG o'zgarsa, PNG'larni qayta eksport qiling.

## Ranglar

| Token | Qiymat | Vazifasi |
|---|---|---|
| `--zuno-lime` | `#C6FF4D` | Asosiy CTA tugmalari, belgi |
| `--zuno-panel` | `#EEF8D8` | Sarlavha, futer, faol holat foni |
| `--zuno-panel-2` | `#E2F2BE` | Panel hover holati |
| `--zuno-page` | `#FBFCF8` | Sahifa foni |
| `--zuno-surface` | `#F4F7EC` | Ikkinchi darajali och sirt |
| `--zuno-ink` / `--zuno-text` | `#1A1F16` / `#151515` | Asosiy matn |
| `--zuno-accent-text` | `#3F6212` | Och fondagi aksent matn |
| `--zuno-muted` | `#6B7280` | Yordamchi matn |
| `--zuno-border` | `#E3E8D8` | Chegaralar |

Qoidalar:

- Lime fonda matn har doim qora (`--zuno-ink`), hech qachon oq emas.
- Dizayn faqat och rangda. Matn kontrasti kamida 4.5:1 bo'lishi kerak.
- Lime'ni oq fonda matn yoki ingichka chiziq sifatida ishlatmang — kontrast ~1.1:1.
- Muvaffaqiyat/ogohlantirish/xato ranglari va buyurtma statuslari ranglari semantik,
  ular brend rangiga almashtirilmagan.

## Domen ko'chirish ro'yxati (tasdiq talab qilinadi)

`ZUNO.uz` ning bo'shligi va egaligi tekshirilmagan. Kodda domen qattiq yozilmagan:
canonical, Open Graph va sotuv havolalari joriy so'rov hostidan
(`request.get_host`) olinadi, shuning uchun domen almashganda kodni o'zgartirish
shart emas. Ishlab chiqarishga o'tishdan oldin:

1. Domen egaligini tasdiqlash va ro'yxatdan o'tkazish.
2. DNS yozuvlari (A/AAAA/CNAME), TTL'ni oldindan kamaytirish.
3. TLS sertifikati (yangi domen uchun).
4. `ALLOWED_HOSTS` ga yangi domenni qo'shish (eski domenni olib tashlamaslik).
5. `CSRF_TRUSTED_ORIGINS` (HTTPS ortida ishlasa) — yangi domen.
6. Eski domendan yangisiga 301 yo'naltirish — faqat yangi domen ishlayotgani
   tasdiqlangandan keyin; mahsulot URL yo'llari o'zgarmaydi.
7. Cookie domeni (`SESSION_COOKIE_DOMAIN`) — hozir sozlanmagan, o'zgartirish shart emas.
8. OAuth / to'lov webhook'lari / CORS — hozircha loyihada yo'q; qo'shilsa, yangi domenni kiritish.
9. Email (SPF/DKIM/DMARC) — hozircha email yuborilmaydi.
10. `robots.txt` va `sitemap.xml` avtomatik: joriy domenni o'zi oladi.
11. Google Search Console / Yandex Webmaster'da yangi domenni tasdiqlash va manzil o'zgarishini bildirish.
