# AI Report MVP

## cURL Ornegi

```bash
curl -X POST http://127.0.0.1:8000/send-report \
  -H "Content-Type: application/json" \
  -d '{"to":"mail@ornek.com","pdf_url":"/reports/rapor_12345678.pdf","subject":"Rapor","summary":"Kisa ozet"}'
```
