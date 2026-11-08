# ZUNO — brend qo'llanmasi

## Logo fayllari (`apps/apps/brand/`)

| Fayl | Qayerda ishlatiladi |
|---|---|
| `zuno-logo-on-dark.svg` | Sayt sarlavhasi va futer |
| `zuno-logo-on-light.svg` | Kirish oynasi |
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
{% include "components/logo.html" with on="dark" height=30 %}   {# qarag'ay fon #}
{% include "components/logo.html" with on="light" height=40 %}  {# och fon #}
{% include "components/logo.html" with compact=True height=32 %} {# faqat belgi #}
```

Logo SVG'lari shriftga bog'liq emas (harflar path sifatida chizilgan), shuning
uchun har qanday kompyuterda bir xil ko'rinadi. Raster ikonkalar `zuno-app-icon.svg`
va `zuno-og.svg` dan yaratilgan; SVG o'zgarsa, PNG'larni qayta eksport qiling.

## Ranglar

| Token | Qiymat | Vazifasi |
|---|---|---|
| `--zuno-page` | `#E9E7DF` | Sahifa foni (iliq qog'oz) |
| `--zuno-surface` | `#F1EFE8` | Ichki sirt, jadval sarlavhasi |
| `--zuno-card` | `#F8F7F2` | Karta |
| `--zuno-pine` | `#1C3A31` | Sarlavha, futer, operator menyusi |
| `--zuno-primary` | `#1F6B57` | Asosiy tugma, faol holat (yagona aksent) |
| `--zuno-panel` | `#DCE4D8` | Yumshoq yashil sirt |
| `--zuno-text` | `#24271F` | Asosiy matn |
| `--zuno-muted` | `#5B6158` | Yordamchi matn |
| `--zuno-border` | `#D8D5CA` | Chegaralar |

Yangi sahifa uchun `apps/brand/ui.css` komponentlaridan foydalaning (`ui-card`, `ui-stat`, `ui-table`, `ui-chip`, `ui-badge`) va kabinet sahifalarini `base/cabinet.html` dan meros oling. Sahifaga alohida rang yoki soya yozilmaydi.

Qoidalar:

- Oppoq fon va neon ranglar ishlatilmaydi. Matn kontrasti kamida 4.5:1 bo'lishi kerak.
- Holat ranglari semantik: har biri matn va yumshoq fon jufti.

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
