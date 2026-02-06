# AI Report MVP

Kısa açıklama

Bu proje CSV/XLSX yükleyip otomatik olarak PDF raporlar oluşturan ve e-posta ile gönderebilen basit bir MVP'dir. Arka uç FastAPI ile `api/` altında, ön uç ise `web/` içinde Next.js ile yer almaktadır.

Özellikler

- Dosya yükleme (`/upload`) — CSV veya Excel dosyalarını alır, özet istatistik üretir ve PDF rapor oluşturur.
- Manuel rapor gönderme (`/send-report`).
- Zamanlı gönderim için basit `scheduled-report` endpoint'i.
- AI özetleme (OpenAI) opsiyonel olarak desteklenir.

Başlarken
---------

Gereksinimler

- Python 3.10+ (veya projenizin kullandığı sürüm)
- Node.js 18+ ve npm/yarn (ön uç için)

Sunucu (API) kurulumu

1. Sanal ortam oluşturun ve bağımlılıkları yükleyin:

```bash
python -m venv .venv
.\.venv\Scripts\activate    # Windows
pip install -r requirements.txt
```

2. Ortam değişkenlerini ayarlayın:
- `api/.env.example` dosyasında hangi anahtarların gerektiğini görebilirsiniz.
- Gerçek anahtarları `api/.env` içine koymayın; üretimde GitHub Secrets veya benzeri kullanın.

Geliştirme sunucusunu başlatma

```bash
# API dizinindeyken
uvicorn api.main:app --reload --host 127.0.0.1 --port 8000
```

Ön uç (web) çalıştırma

```bash
cd web
npm install
npm run dev
# veya yarn
```

Örnek istek

```bash
curl -X POST http://127.0.0.1:8000/send-report \
  -H "Content-Type: application/json" \
  -d '{"to":"mail@ornek.com","pdf_url":"/reports/rapor_12345678.pdf","subject":"Rapor","summary":"Kisa ozet"}'
```

Ortam değişkenleri ve güvenlik

- `OPENAI_API_KEY` (opsiyonel): AI özetleme için. `api/.env.example` içinde listelenmiştir.
- `RESEND_API_KEY`: E-posta göndermek için gereklidir.
- `CRON_KEY`: Zamanlı rapor endpoint'i için gereklidir.

Uyarı: Gizli anahtarları asla açık repoya commit etmeyin. Mevcut repoda `api/.env` kaldırılmış ve `api/.env.example` eklendi.

Yapılandırma ve dağıtım önerileri

- Prod ortamı için `OPENAI_API_KEY` ve diğer gizli anahtarları GitHub Secrets veya platformunuzun secret yönetimine ekleyin.
- Rapor dosyaları büyükse `reports/` klasörünü harici bir depolamaya taşıyın (S3, Blob vs.).

Katkıda bulunma

- PR gönderin veya issue açın.

Lisans

Proje açık kaynak lisansı belirtilmemiştir; kullanmadan önce lisans ekleyin.
