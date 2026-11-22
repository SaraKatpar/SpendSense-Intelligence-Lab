import { useState } from "react";

const KEY = "spendsense.savings-goals.v1";
const empty = { name: "", target: "", saved: "0", due: "" };
const money = n => `PKR ${Number(n).toLocaleString("en-PK", { maximumFractionDigits: 2 })}`;

function load() {
  try {
    const data = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(data) ? data.filter(g => typeof g.id === "string" && typeof g.name === "string" && Number.isFinite(g.target) && g.target > 0 && Number.isFinite(g.saved) && g.saved >= 0) : [];
  } catch { return []; }
}

export default function SavingsGoals() {
  const [goals, setGoals] = useState(load);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [deleted, setDeleted] = useState(null);

  function persist(next, message) {
    try {
      localStorage.setItem(KEY, JSON.stringify(next));
      setGoals(next); setNotice(message); setError("");
      return true;
    } catch { setError("Could not save goals. Check that browser storage is enabled."); return false; }
  }

  function submit(event) {
    event.preventDefault();
    const target = Number(form.target), saved = Number(form.saved);
    if (!form.name.trim() || !Number.isFinite(target) || target <= 0 || !Number.isFinite(saved) || saved < 0) {
      setError("Enter a goal name, a target above zero, and a saved amount of zero or more."); return;
    }
    const goal = { id: editing || crypto.randomUUID(), name: form.name.trim(), target, saved, due: form.due };
    const next = editing ? goals.map(g => g.id === editing ? goal : g) : [...goals, goal];
    if (persist(next, editing ? "Goal updated." : "Goal added.")) {
      setForm(empty); setEditing(null); setOpen(false);
    }
  }

  function edit(goal) {
    setForm({ name: goal.name, target: String(goal.target), saved: String(goal.saved), due: goal.due || "" });
    setEditing(goal.id); setOpen(true); setError(""); setNotice("");
  }

  return (
    <section className="panel transaction-panel" aria-label="Savings goals">
      <div className="section-header">
        <div><div className="section-kicker">YOUR SAVINGS PLAN</div><h2>Savings Goals</h2></div>
        <button className="primary-button" onClick={() => { setForm(empty); setEditing(null); setOpen(true); setError(""); }}>Add goal</button>
      </div>
      <p className="muted">Track money you have set aside. Goals are saved in this browser on this device and do not change your transaction balance.</p>
      {open && <form className="transaction-form" onSubmit={submit}>
        <label>Goal name<input required maxLength={80} value={form.name} placeholder="e.g. New laptop" onChange={e => setForm({ ...form, name: e.target.value })} /></label>
        <label>Target amount (PKR)<input required type="number" min="0.01" step="0.01" value={form.target} onChange={e => setForm({ ...form, target: e.target.value })} /></label>
        <label>Amount saved (PKR)<input required type="number" min="0" step="0.01" value={form.saved} onChange={e => setForm({ ...form, saved: e.target.value })} /></label>
        <label>Target date (optional)<input type="date" value={form.due} onChange={e => setForm({ ...form, due: e.target.value })} /></label>
        <div style={{ display: "flex", gap: 12 }}><button className="primary-button" type="submit">{editing ? "Save changes" : "Save goal"}</button><button className="subtle-button" type="button" onClick={() => { setOpen(false); setError(""); }}>Cancel</button></div>
      </form>}
      {error && <p role="alert" className="form-error">{error}</p>}
      {notice && <p role="status" className="form-success">{notice}</p>}
      {deleted && <button className="subtle-button" onClick={() => { if (persist([...goals, deleted], "Goal restored.")) setDeleted(null); }}>Undo delete</button>}
      {!goals.length && <p className="empty-transactions">No goals yet. Add your first savings goal.</p>}
      {goals.map(goal => {
        const percent = Math.min(100, Math.round(goal.saved / goal.target * 100));
        return <article key={goal.id} style={{ padding: "18px 0", borderBottom: "1px solid #29334d" }}>
          <h3 style={{ overflowWrap: "anywhere" }}>{goal.name}</h3>
          <p>{money(goal.saved)} saved of {money(goal.target)}</p>
          <progress aria-label={`${goal.name} progress`} max={goal.target} value={Math.min(goal.saved, goal.target)} style={{ width: "100%", accentColor: "#a98aff" }} />
          <p className="muted">{percent}% · {goal.saved >= goal.target ? "Goal reached!" : `${money(goal.target - goal.saved)} to go`}{goal.due ? ` · Target: ${goal.due}` : ""}</p>
          <div style={{ display: "flex", gap: 12 }}>
            <button className="subtle-button" onClick={() => edit(goal)}>Edit {goal.name}</button>
            <button className="subtle-button" onClick={() => { if (persist(goals.filter(g => g.id !== goal.id), "Goal deleted. You can undo this.")) setDeleted(goal); }}>Delete {goal.name}</button>
          </div>
        </article>;
      })}
    </section>
  );
}
