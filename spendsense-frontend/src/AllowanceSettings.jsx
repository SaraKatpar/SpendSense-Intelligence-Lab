import { useState } from "react";

const KEY = "spendsense.allowance.v1";

function loadSettings() {
  try {
    const saved = JSON.parse(localStorage.getItem(KEY) || "null");
    return {
      amount: saved?.amount > 0 ? String(saved.amount) : "",
      nextDate: /^\d{4}-\d{2}-\d{2}$/.test(saved?.nextDate || "") ? saved.nextDate : "",
    };
  } catch {
    return { amount: "", nextDate: "" };
  }
}

export default function AllowanceSettings() {
  const [values, setValues] = useState(loadSettings);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  function update(field, value) {
    setValues(previous => ({ ...previous, [field]: value }));
    setMessage("");
    setError("");
  }

  function save(event) {
    event.preventDefault();
    const amount = Number(values.amount);
    if (!Number.isFinite(amount) || amount <= 0 || !values.nextDate) {
      setError("Enter a monthly allowance above zero and your next allowance date.");
      return;
    }
    try {
      localStorage.setItem(KEY, JSON.stringify({ amount, nextDate: values.nextDate }));
      setMessage("Allowance settings saved.");
      setError("");
    } catch {
      setError("Your browser could not save these settings. Check that browser storage is enabled.");
    }
  }

  return (
    <section className="panel transaction-panel" style={{ maxWidth: 680 }}>
      <div className="section-kicker">YOUR ALLOWANCE</div>
      <h2>Allowance settings</h2>
      <p className="muted">Set your monthly allowance and when you expect the next payment.</p>
      <form className="transaction-form" onSubmit={save}>
        <label htmlFor="monthly-allowance">
          Monthly allowance (PKR)
          <input id="monthly-allowance" type="number" min="0.01" step="0.01"
            inputMode="decimal" placeholder="e.g. 15000" required
            value={values.amount} onChange={event => update("amount", event.target.value)} />
        </label>
        <label htmlFor="next-allowance-date">
          Next allowance date
          <input id="next-allowance-date" type="date" required
            value={values.nextDate} onChange={event => update("nextDate", event.target.value)} />
        </label>
        <button className="primary-button" type="submit">Save allowance settings</button>
        {message && <p className="form-success" role="status">{message}</p>}
        {error && <p className="form-error" role="alert">{error}</p>}
      </form>
      <p className="muted" style={{ marginTop: 24 }}>
        Saved in this browser on this device. This sets your allowance plan;
        record received payments as income in Transactions.
      </p>
    </section>
  );
}
