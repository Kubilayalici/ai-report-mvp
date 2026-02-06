import json
import os
import uuid
from io import BytesIO

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from openai import OpenAI
from pydantic import BaseModel
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

# Kurulum:
# - pip install openai python-dotenv reportlab matplotlib requests
# - pip install -r requirements.txt
# - api/.env icine OPENAI_API_KEY ekle (opsiyonel: OPENAI_MODEL)
# - api/.env icine RESEND_API_KEY ekle
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))
matplotlib.use("Agg")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

REPORTS_DIR = os.path.join(os.path.dirname(__file__), "..", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)
app.mount("/reports", StaticFiles(directory=REPORTS_DIR), name="reports")

FONT_PATH = os.path.join(os.path.dirname(__file__), "assets", "fonts", "SegoeUI.ttf")
pdfmetrics.registerFont(TTFont("SegoeUI", FONT_PATH))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
client = OpenAI(api_key=OPENAI_API_KEY) if OPENAI_API_KEY else None
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev")
CRON_KEY = os.getenv("CRON_KEY", "")


class SendReportRequest(BaseModel):
    to: str
    pdf_url: str
    subject: str
    summary: str


class ScheduledReportRequest(BaseModel):
    to: str
    frequency: str


@app.on_event("startup")
def _startup_test_call() -> None:
    if not OPENAI_API_KEY:
        print("OPENAI_API_KEY bulunamadi; AI ozet devre disi.")
        return

    try:
        client.responses.create(
            model=OPENAI_MODEL,
            input="Sadece 'ok' yaz.",
            max_output_tokens=16,
            temperature=0,
        )
    except Exception as exc:
        print(f"OpenAI test cagrisinda hata: {exc}")


def _build_summary_payload(df: pd.DataFrame) -> dict:
    numeric_df = df.select_dtypes(include="number")
    numeric_summary: dict = {}
    if not numeric_df.empty:
        desc = numeric_df.describe().loc[["count", "mean", "std", "min", "max"]]
        numeric_summary = desc.round(4).to_dict()

    return {
        "satir_sayisi": int(df.shape[0]),
        "kolon_sayisi": int(df.shape[1]),
        "kolon_isimleri": df.columns.tolist(),
        "sayisal_kolon_ozeti": numeric_summary,
    }


def _generate_ai_summary(summary_payload: dict) -> str | None:
    if not OPENAI_API_KEY or client is None:
        return None

    prompt = (
        "Aşağıdaki özet istatistiklere dayanarak, Türkçe ve en fazla 3 cümlelik kısa bir özet yaz.\n"
        f"Özet: {json.dumps(summary_payload, ensure_ascii=False)}"
    )

    try:
        response = client.responses.create(
            model=OPENAI_MODEL,
            input=prompt,
            temperature=0.2,
            max_output_tokens=120,
        )
        return response.output_text.strip()
    except Exception:
        return None


def _create_pdf_report(
    filename: str,
    row_count: int,
    col_count: int,
    ozet: str,
    ai_ozet: str,
    metrics: dict,
    trend_data: list[dict],
    distribution_data: list[dict] | None,
) -> str:
    pdf_name = f"rapor_{uuid.uuid4().hex[:8]}.pdf"
    pdf_path = os.path.join(REPORTS_DIR, pdf_name)
    trend_png = os.path.join(REPORTS_DIR, f"trend_{uuid.uuid4().hex[:8]}.png")
    dist_png = os.path.join(REPORTS_DIR, f"dist_{uuid.uuid4().hex[:8]}.png")

    try:
        if trend_data:
            xs = [p["x"] for p in trend_data]
            ys = [p["y"] for p in trend_data]
            plt.figure(figsize=(6.5, 3.0))
            plt.plot(xs, ys)
            plt.title("Trend")
            plt.tight_layout()
            plt.savefig(trend_png, dpi=120)
            plt.close()

        if distribution_data:
            labels = [p["label"] for p in distribution_data]
            values = [p["value"] for p in distribution_data]
            plt.figure(figsize=(6.5, 3.0))
            plt.bar(labels, values)
            plt.title("Distribution")
            plt.xticks(rotation=45, ha="right")
            plt.tight_layout()
            plt.savefig(dist_png, dpi=120)
            plt.close()

        c = canvas.Canvas(pdf_path, pagesize=A4)
        width, height = A4
        y = height - 50

        c.setFont("SegoeUI", 16)
        c.drawString(50, y, "Rapor")
        y -= 30

        c.setFont("SegoeUI", 11)
        lines = [
            f"Dosya adi: {filename}",
            f"Satir sayisi: {row_count}",
            f"Kolon sayisi: {col_count}",
            f"Ozet: {ozet}",
            f"AI ozet: {ai_ozet}",
            "Metrics:",
            f"  row_count: {metrics.get('row_count')}",
            f"  col_count: {metrics.get('col_count')}",
            f"  missing_cells: {metrics.get('missing_cells')}",
            f"  numeric_cols: {metrics.get('numeric_cols')}",
        ]

        for line in lines:
            if y < 80:
                c.showPage()
                y = height - 50
                c.setFont("SegoeUI", 11)
            c.drawString(50, y, line)
            y -= 18

        if trend_data:
            if y < 300:
                c.showPage()
                y = height - 50
            c.drawImage(trend_png, 50, y - 220, width=500, height=220)
            y -= 240

        if distribution_data:
            if y < 300:
                c.showPage()
                y = height - 50
            c.drawImage(dist_png, 50, y - 220, width=500, height=220)
            y -= 240

        c.save()
        return pdf_name
    finally:
        for path in (trend_png, dist_png):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass


@app.post("/send-report")
async def send_report(payload: SendReportRequest):
    return _send_report_email(
        to=payload.to,
        pdf_url=payload.pdf_url,
        subject=payload.subject,
        summary=payload.summary,
    )


def _send_report_email(to: str, pdf_url: str, subject: str, summary: str):
    if not RESEND_API_KEY:
        return JSONResponse(status_code=400, content={"error": "RESEND_API_KEY bulunamadi."})

    full_pdf_url = (
        f"http://127.0.0.1:8000{pdf_url}" if pdf_url.startswith("/") else pdf_url
    )

    email_html = f"<p>{summary}</p><p><a href=\"{full_pdf_url}\">PDF indir</a></p>"

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": RESEND_FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": email_html,
            },
            timeout=20,
        )
        if not response.ok:
            return JSONResponse(
                status_code=400,
                content={"error": "Resend API hatasi", "details": response.text},
            )

        data = response.json()
        return {"status": "ok", "id": data.get("id")}
    except Exception as exc:
        return JSONResponse(
            status_code=400,
            content={"error": f"E-posta gonderilemedi: {exc}"},
        )


@app.post("/scheduled-report")
async def scheduled_report(payload: ScheduledReportRequest, request: Request):
    if not CRON_KEY:
        return JSONResponse(status_code=400, content={"error": "CRON_KEY bulunamadi."})
    if request.headers.get("X-CRON-KEY") != CRON_KEY:
        return JSONResponse(status_code=401, content={"error": "Yetkisiz istek."})

    print(f"scheduled-report frequency: {payload.frequency}")

    try:
        pdf_files = [
            f
            for f in os.listdir(REPORTS_DIR)
            if f.lower().endswith(".pdf") and os.path.isfile(os.path.join(REPORTS_DIR, f))
        ]
        if not pdf_files:
            return JSONResponse(status_code=400, content={"error": "PDF bulunamadi."})

        latest = max(
            pdf_files, key=lambda f: os.path.getmtime(os.path.join(REPORTS_DIR, f))
        )
        pdf_url = f"/reports/{latest}"

        return _send_report_email(
            to=payload.to,
            pdf_url=pdf_url,
            subject="Planli Rapor",
            summary="Planli raporunuz hazir.",
        )
    except Exception as exc:
        return JSONResponse(
            status_code=400,
            content={"error": f"Planli rapor gonderilemedi: {exc}"},
        )


@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    filename = file.filename or ""
    ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if ext not in {"csv", "xlsx", "xls"}:
        raise HTTPException(status_code=400, detail="Sadece CSV veya Excel dosyasi desteklenir.")

    try:
        content = await file.read()
        buffer = BytesIO(content)

        if ext == "csv":
            df = pd.read_csv(buffer)
        else:
            df = pd.read_excel(buffer)

        summary_payload = _build_summary_payload(df)
        ai_ozet = _generate_ai_summary(summary_payload) or "AI özet şu an üretilemedi."

        missing_cells = int(df.isna().sum().sum())
        numeric_df = df.select_dtypes(include="number")
        numeric_cols = int(numeric_df.shape[1])

        trend_col = None
        lower_cols = {str(c).lower(): c for c in df.columns}
        for candidate in ("sales", "amount"):
            if candidate in lower_cols:
                trend_col = lower_cols[candidate]
                break
        if trend_col is None and numeric_cols > 0:
            trend_col = numeric_df.columns[0]

        trend_data = []
        if trend_col is not None:
            series = df[trend_col].head(50)
            trend_data = [
                {"x": int(i), "y": (None if pd.isna(v) else float(v))}
                for i, v in series.items()
            ]

        distribution_data = None
        categorical_cols = df.select_dtypes(include="object").columns.tolist()
        if categorical_cols:
            cat_col = categorical_cols[0]
            counts = df[cat_col].astype(str).value_counts().head(10)
            distribution_data = [
                {"label": str(label), "value": int(value)}
                for label, value in counts.items()
            ]

        metrics = {
            "row_count": int(df.shape[0]),
            "col_count": int(df.shape[1]),
            "missing_cells": missing_cells,
            "numeric_cols": numeric_cols,
        }

        pdf_name = _create_pdf_report(
            filename=filename,
            row_count=int(df.shape[0]),
            col_count=int(df.shape[1]),
            ozet=f"Bu dosyada {int(df.shape[0])} satır, {int(df.shape[1])} kolon var.",
            ai_ozet=ai_ozet,
            metrics=metrics,
            trend_data=trend_data,
            distribution_data=distribution_data,
        )

        return {
            "dosya_adi": filename,
            "satir_sayisi": int(df.shape[0]),
            "kolon_sayisi": int(df.shape[1]),
            "ozet": f"Bu dosyada {int(df.shape[0])} satır, {int(df.shape[1])} kolon var.",
            "ai_ozet": ai_ozet,
            "dashboard": {
                "metrics": metrics,
                "trend": trend_data,
                "distribution": distribution_data,
            },
            "pdf_url": f"/reports/{pdf_name}",
        }
    except Exception as exc:
        print(f"/upload hata: {exc}")
        raise HTTPException(status_code=400, detail=f"Dosya okunamadi: {exc}")
