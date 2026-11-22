import { useEffect, useState } from "react";
import { ScanLine, UploadCloud, AlertCircle, CheckCircle2, Sparkles } from "lucide-react";
import "./CaptureStudio.css";

const API = "http://127.0.0.1:8002";
const CATEGORIES = ["Food", "Groceries", "Transport", "Shopping", "Bills", "Health", "Education", "Entertainment", "Other"];
const MAX_BYTES = 8 * 1024 * 1024;
const today = () => new Date().toLocaleDateString("en-CA");

export default function CaptureStudio({ refresh, onSaved }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState("");
  const [scanning, setScanning] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [result, setResult] = useState(null);
  const [form, setForm] = useState(null);
  const [currencyConfirmed, setCurrencyConfirmed] = useState(false);
  const [categoryConfirmed, setCategoryConfirmed] = useState(false);

  useEffect(() => {
    if (!file) { setPreview(""); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);

  function selectFile(event) {
    const selected = event.target.files?.[0] || null;
    setError(""); setSuccess(""); setResult(null); setForm(null);
    setCategoryConfirmed(false); setCurrencyConfirmed(false);
    if (!selected) { setFile(null); return; }
    if (!["image/png", "image/jpeg"].includes(selected.type)) {
      setError("Choose a JPG or PNG receipt."); setFile(null); return;
    }
    if (selected.size > MAX_BYTES) {
      setError("Receipt must be 8 MB or smaller."); setFile(null); return;
    }
    setFile(selected);
  }

  async function scan() {
    if (!file || scanning || saving) return;
    setScanning(true); setError(""); setSuccess(""); setResult(null); setForm(null);
    setCategoryConfirmed(false); setCurrencyConfirmed(false);
    try {
      const body = new FormData();
      body.append("file", file);
      const response = await fetch(`${API}/api/ocr/scan`, { method: "POST", body });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Receipt scan failed.");
      setResult(data);
      setForm({
        date: /^\d{4}-\d{2}-\d{2}$/.test(data.date || "") ? data.date : today(),
        amount: data.amount == null ? "" : String(data.amount),
        description: data.description || "",
        category: ""
      });
    } catch (err) {
      setError(err.message || "Could not reach the OCR service.");
    } finally { setScanning(false); }
  }

  function update(field, value) {
    setForm(current => ({ ...current, [field]: value }));
    setSuccess("");
  }

  const detectedCurrency = (result?.currency || "").trim().toUpperCase();
  const foreignCurrency = Boolean(detectedCurrency && detectedCurrency !== "PKR");
  const currencyReady = !foreignCurrency && (detectedCurrency === "PKR" || currencyConfirmed);
  const validAmount = form && Number.isFinite(Number(form.amount)) && Number(form.amount) > 0;
  const ready = Boolean(form && validAmount && /^\d{4}-\d{2}-\d{2}$/.test(form.date) &&
    form.description.trim().length >= 1 && form.description.trim().length <= 300 &&
    CATEGORIES.includes(form.category) && categoryConfirmed && currencyReady);

  async function save(event) {
    event.preventDefault();
    if (!ready || saving) return;
    setSaving(true); setError(""); setSuccess("");
    try {
      const response = await fetch(`${API}/api/transactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          date: form.date, amount: Number(form.amount), kind: "Expense",
          category: form.category, description: form.description.trim()
        })
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Could not save transaction.");
      setSuccess("Expense saved successfully to your SpendSense account.");
      setResult(null); setForm(null); setFile(null);
      setCategoryConfirmed(false); setCurrencyConfirmed(false);
      if (refresh) {
        try { await refresh(); }
        catch { setError("Saved, but the dashboard could not refresh. Reload the page to see the transaction."); }
      }
      // Keep the user on Capture Studio so the success message is visible.
    } catch (err) {
      setError(err.message || "Could not save expense.");
    } finally { setSaving(false); }
  }

  return (
    <section className="capture-studio">
      <div className="capture-card">
        <div className="capture-eyebrow"><ScanLine size={17} /> CAPTURE STUDIO · RECEIPT INTELLIGENCE</div>
        <h2>Turn a receipt into an expense.</h2>
        <p>Scan a PKR receipt, review the details, choose your category, and save it to your transactions.</p>
        <label className="capture-drop">
          <UploadCloud size={30} />
          <strong>{file ? file.name : "Choose a receipt image"}</strong>
          <span>JPG or PNG · Maximum 8 MB</span>
          <input type="file" accept="image/png,image/jpeg" onChange={selectFile} disabled={scanning || saving} />
        </label>
        {preview && <img className="capture-preview" src={preview} alt="Selected receipt preview" />}
        <button className="capture-primary" type="button" disabled={!file || scanning || saving} onClick={scan}>
          {scanning ? "Scanning receipt…" : "Scan receipt"}
        </button>
        {error && <p className="capture-error" role="alert"><AlertCircle size={17} /> {error}</p>}
        {success && <p className="capture-success" role="status"><CheckCircle2 size={17} /> {success}</p>}
      </div>

      {result && form && (
        <form className="capture-card" onSubmit={save}>
          <div className="capture-eyebrow"><CheckCircle2 size={17} /> SCAN COMPLETE · REVIEW REQUIRED</div>
          <h2>Review your expense</h2>
          <p>OCR may misread receipt details. Correct the amount, date, and description before saving.</p>
          <div className="capture-fields">
            <label>Date<input required type="date" value={form.date} onChange={e => update("date", e.target.value)} /></label>
            <label>Amount (PKR)<input required type="number" min="0.01" step="0.01" value={form.amount} onChange={e => update("amount", e.target.value)} placeholder="0.00" /></label>
            <label className="capture-wide">Description<input required value={form.description} onChange={e => update("description", e.target.value)} placeholder="e.g. Groceries for hostel" maxLength={300} /></label>
          </div>
          <div className="capture-ai">
            <div className="capture-eyebrow"><Sparkles size={17} /> SPENDSENSE ML SUGGESTION</div>
            <p>Suggested category: <strong>{result.category_suggestion || "Unavailable"}</strong>
              {typeof result.category_confidence === "number" ? ` · ${(result.category_confidence * 100).toFixed(1)}% model probability` : ""}</p>
            {CATEGORIES.includes(result.category_suggestion) && (
              <button className="capture-secondary" type="button" onClick={() => { update("category", result.category_suggestion); setCategoryConfirmed(true); }}>
                Accept AI suggestion
              </button>
            )}
            <p className="capture-hint">The model only recommends. You make the final decision.</p>
          </div>
          <div className="capture-fields">
            <label className="capture-wide">Your final category
              <select required value={form.category} onChange={e => { update("category", e.target.value); setCategoryConfirmed(Boolean(e.target.value)); }}>
                <option value="">Select a category</option>
                {CATEGORIES.map(category => <option key={category} value={category}>{category}</option>)}
              </select>
            </label>
          </div>
          {foreignCurrency ? (
            <div className="capture-safe"><AlertCircle size={18} /><span>This receipt was detected as <strong>{detectedCurrency}</strong>. Only PKR receipts can be saved. Please upload a PKR receipt; changing the amount does not convert currencies.</span></div>
          ) : detectedCurrency !== "PKR" ? (
            <label className="capture-safe capture-confirm"><input type="checkbox" checked={currencyConfirmed} onChange={e => setCurrencyConfirmed(e.target.checked)} /><span>OCR could not confirm the currency. I checked the receipt and confirm the amount is in <strong>PKR</strong>.</span></label>
          ) : (
            <div className="capture-safe"><CheckCircle2 size={18} /><span>Receipt currency detected: <strong>PKR</strong>. Please verify this against the image.</span></div>
          )}
          <details className="capture-raw"><summary>View extracted receipt text</summary><pre>{result.raw_text || "No text extracted."}</pre></details>
          <button className="capture-primary" type="submit" disabled={!ready || saving}>{saving ? "Saving…" : "Confirm & Save"}</button>
          <p className="capture-hint">Only this button saves the transaction. Scanning never saves automatically.</p>
        </form>
      )}
    </section>
  );
}
