"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  Bar,
  BarChart,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

type TrendPoint = {
  x: number;
  y: number | null;
};

type DistributionPoint = {
  label: string;
  value: number;
};

type Dashboard = {
  metrics: {
    row_count: number;
    col_count: number;
    missing_cells: number;
    numeric_cols: number;
  };
  trend: TrendPoint[];
  distribution: DistributionPoint[] | null;
};

type UploadResponse = {
  dosya_adi: string;
  satir_sayisi: number;
  kolon_sayisi: number;
  ozet: string;
  ai_ozet: string;
  dashboard?: Dashboard;
  pdf_url?: string;
};

export default function Home() {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<UploadResponse | null>(null);
  const [blocked, setBlocked] = useState(false);
  const [showPremiumModal, setShowPremiumModal] = useState(false);
  const [premiumEmail, setPremiumEmail] = useState("");
  const [premiumSaved, setPremiumSaved] = useState(false);
  const [premiumChoice, setPremiumChoice] = useState<string | null>(null);
  const resultsRef = useRef<HTMLDivElement | null>(null);
  const checkoutUrl = (process.env.NEXT_PUBLIC_LEMON_CHECKOUT_URL ?? "").trim();

  const todayKey = () => new Date().toISOString().slice(0, 10);

  const readDailyCount = () => {
    if (typeof window === "undefined") return { date: "", count: 0 };
    const raw = localStorage.getItem("daily_report_count") ?? "";
    const [date, countStr] = raw.split(":");
    if (!date || !countStr) return { date: "", count: 0 };
    const count = Number.parseInt(countStr, 10);
    return { date, count: Number.isNaN(count) ? 0 : count };
  };

  const writeDailyCount = (date: string, count: number) => {
    if (typeof window === "undefined") return;
    localStorage.setItem("daily_report_count", `${date}:${count}`);
  };

  const handleSubmit = async () => {
    if (!file) return;

    const today = todayKey();
    const current = readDailyCount();
    if (current.date !== today) {
      writeDailyCount(today, 0);
    }
    const refreshed = readDailyCount();
    if (refreshed.count >= 1) {
      setBlocked(true);
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    const response = await fetch("http://127.0.0.1:8000/upload", {
      method: "POST",
      body: formData,
    });

    const data = (await response.json()) as UploadResponse;
    setResult(data);

    const after = readDailyCount();
    const baseCount = after.date === today ? after.count : 0;
    writeDailyCount(today, baseCount + 1);
    setBlocked(baseCount + 1 >= 1);
  };

  const metrics = result?.dashboard?.metrics ?? null;
  const trendData = useMemo(
    () => result?.dashboard?.trend ?? [],
    [result?.dashboard?.trend]
  );
  const distributionData = useMemo(
    () => result?.dashboard?.distribution ?? null,
    [result?.dashboard?.distribution]
  );

  useEffect(() => {
    if (result && resultsRef.current) {
      resultsRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, [result]);

  useEffect(() => {
    const today = todayKey();
    const current = readDailyCount();
    if (current.date !== today) {
      writeDailyCount(today, 0);
      setBlocked(false);
      return;
    }
    setBlocked(current.count >= 1);
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 p-6 text-slate-900">
      <div className="mx-auto flex max-w-5xl flex-col gap-6">
        <header className="flex flex-col gap-2">
          <h1 className="text-2xl font-semibold">
            Excel / CSV dosyalarınızı saniyeler içinde rapora dönüştürün
          </h1>
        </header>

        <div className="flex flex-wrap items-center gap-3">
          <input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
            className="rounded border border-slate-200 bg-white px-3 py-2 text-sm"
          />
          <button
            onClick={handleSubmit}
            className="rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:cursor-not-allowed disabled:bg-slate-400"
            disabled={blocked}
          >
            Gonder
          </button>
        </div>
        <p className="text-xs text-slate-500">
          Dosyanız kaydedilmez, sadece analiz edilir.
        </p>

        {blocked ? (
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-medium text-slate-800">
              Günlük ücretsiz rapor limitine ulaştınız.
            </p>
            <p className="mt-2 text-sm text-slate-600">
              Premium ile sınırsız rapor oluşturun.
            </p>
            {checkoutUrl ? (
              <a
                href={checkoutUrl}
                className="mt-3 inline-flex items-center justify-center rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white"
              >
                Premium’a geç
              </a>
            ) : (
              <button
                className="mt-3 rounded bg-slate-400 px-4 py-2 text-sm font-medium text-white"
                disabled
              >
                Ödeme yakında aktif
              </button>
            )}
          </section>
        ) : null}

        {showPremiumModal ? (
          <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
            <div className="w-full max-w-sm rounded-lg bg-white p-4">
              <p className="text-sm font-medium text-slate-800">
                Premium’a geçmek ister misiniz?
              </p>
              {premiumSaved ? (
                <p className="mt-3 text-sm text-slate-600">
                  Teşekkürler, yakında yazacağız.
                </p>
              ) : (
                <>
                  <p className="mt-3 text-sm text-slate-700">
                    Aylık hangi fiyat sana daha mantıklı?
                  </p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {["299 TL", "399 TL", "499 TL"].map((option) => (
                      <button
                        key={option}
                        onClick={() => {
                          setPremiumChoice(option);
                          localStorage.setItem("premium_price_choice", option);
                        }}
                        className={`rounded border px-3 py-1 text-sm ${
                          premiumChoice === option
                            ? "border-slate-900 bg-slate-900 text-white"
                            : "border-slate-200 text-slate-700"
                        }`}
                      >
                        {option}
                      </button>
                    ))}
                  </div>
                  <input
                    type="email"
                    placeholder="Email"
                    value={premiumEmail}
                    onChange={(e) => setPremiumEmail(e.target.value)}
                    className="mt-3 w-full rounded border border-slate-200 px-3 py-2 text-sm"
                  />
                  <button
                    onClick={() => {
                      if (!premiumEmail) return;
                      localStorage.setItem(
                        "premium_interest_email",
                        premiumEmail
                      );
                      setPremiumSaved(true);
                    }}
                    className="mt-3 w-full rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white"
                  >
                    Beni listeye ekle
                  </button>
                </>
              )}
              <button
                onClick={() => setShowPremiumModal(false)}
                className="mt-3 w-full rounded border border-slate-200 px-4 py-2 text-sm text-slate-700"
              >
                Kapat
              </button>
            </div>
          </div>
        ) : null}

        <div ref={resultsRef} />

        {metrics ? (
          <section className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase text-slate-500">Row Count</p>
              <p className="mt-2 text-2xl font-semibold">{metrics.row_count}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase text-slate-500">Col Count</p>
              <p className="mt-2 text-2xl font-semibold">{metrics.col_count}</p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase text-slate-500">Missing Cells</p>
              <p className="mt-2 text-2xl font-semibold">
                {metrics.missing_cells}
              </p>
            </div>
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <p className="text-xs uppercase text-slate-500">Numeric Cols</p>
              <p className="mt-2 text-2xl font-semibold">
                {metrics.numeric_cols}
              </p>
            </div>
          </section>
        ) : null}

        {result?.ozet ? (
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-medium text-slate-700">Ozet</p>
            <p className="mt-2 text-sm text-slate-600">{result.ozet}</p>
            <p className="mt-3 text-sm font-medium text-slate-700">AI Ozet</p>
            <p className="mt-2 text-sm text-slate-600">{result.ai_ozet}</p>
            {result.pdf_url ? (
              <a
                className="mt-4 inline-flex items-center justify-center rounded bg-slate-900 px-4 py-2 text-sm font-medium text-white"
                href={`http://127.0.0.1:8000${result.pdf_url}`}
                target="_blank"
                rel="noreferrer"
              >
                PDF indir
              </a>
            ) : null}
          </section>
        ) : null}

        {trendData.length ? (
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-medium text-slate-700">
              Trend (ilk 50 satir)
            </p>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <XAxis dataKey="x" />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="y" stroke="#0f172a" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </section>
        ) : null}

        {distributionData ? (
          <section className="rounded-lg border border-slate-200 bg-white p-4">
            <p className="text-sm font-medium text-slate-700">
              Dagilim (ilk 10 kategori)
            </p>
            <div className="mt-4 h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={distributionData}>
                  <XAxis dataKey="label" hide />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="value" fill="#0f172a" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </section>
        ) : null}
      </div>
    </main>
  );
}
