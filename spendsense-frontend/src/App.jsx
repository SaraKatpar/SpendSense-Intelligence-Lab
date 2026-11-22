import { useEffect, useMemo, useState } from "react";
import {
  Area, AreaChart, CartesianGrid, Cell, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis
} from "recharts";
import {
  Bell, ChevronDown, CircleHelp, Command, CreditCard,
  LayoutDashboard, Search, Settings, ShieldCheck,
  Sparkles, Target, TrendingUp, Wallet, Zap,
  ArrowUpRight, Plus, Send, BrainCircuit,
  FlaskConical, ScanLine, RotateCcw, AlertCircle,
  CheckCircle2, ChevronUp
} from "lucide-react";
import "./App.css";
import SpendingDNA from "./SpendingDNA";
import PatternDetective from "./PatternDetective";
import CaptureStudio from "./CaptureStudio";


import { API } from "./api";


const rupees = n =>
  `Rs. ${Number(n || 0).toLocaleString("en-PK")}`;

const menu = [
  { label: "Overview", icon: LayoutDashboard },
  { label: "Transactions", icon: CreditCard },
  { label: "Capture Studio", icon: ScanLine },
  { label: "Spending DNA", icon: BrainCircuit },
  { label: "Pattern Detective", icon: ShieldCheck },
  { label: "Model Arena", icon: FlaskConical }
];

const suggestions = [
  "Analyze my spending",
  "Suggest a budget",
  "Upcoming bills",
  "Saving balance"
];

const categories = [
  "Food", "Groceries", "Transport", "Shopping",
  "Bills", "Health", "Education", "Entertainment", "Other"
];

const palette = [
  "#a98aff", "#6d69ee", "#4bd9dc", "#ffc879",
  "#ff91b6", "#7fdca9", "#e0b5ff", "#82a4ff"
];

const categoryColors = {
  Food: "#a98aff",
  Transport: "#4bd9dc",
  Health: "#ff91b6",
  Education: "#ffc879",
  Groceries: "#7fdca9",
  Bills: "#82a4ff",
  Shopping: "#e0b5ff",
  Entertainment: "#ffab77"
};

function Robot() {
  return (
    <div className="robot-scene" aria-label="Decorative purple AI robot">
      <div className="robot-halo" />
      <div className="robot-beam" />
      <div className="robot-body">
        <div className="robot-antenna" />
        <div className="robot-face"><i /><i /></div>
        <div className="robot-mouth" />
        <span className="robot-ear left" />
        <span className="robot-ear right" />
      </div>
      <div className="robot-shadow" />
    </div>
  );
}

function ProgressRing({
  value, color = "#a98aff", size = 132, children
}) {
  return (
    <div
      className="ring"
      style={{
        "--ring-color": color,
        "--ring-value": `${value}%`,
        width: size,
        height: size
      }}
    >
      <div className="ring-center">{children}</div>
    </div>
  );
}

function Sidebar({ active, onSelect }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <span className="brand-symbol"><Command size={20} /></span>
        <span>
          spend<span className="brand-accent">sense</span>
          <span className="brand-dot">.</span>
        </span>
      </div>

      <div className="workspace">
        <div className="workspace-icon">S</div>
        <div>
          <strong>My Workspace</strong>
          <small>Student account</small>
        </div>
        <ChevronDown size={15} />
      </div>

      <div className="side-label">GENERAL</div>
      <nav>
        {menu.slice(0, 3).map(({ label, icon: Icon }) => (
          <button
            key={label}
            className={`nav-link ${active === label ? "active" : ""}`}
            onClick={() => onSelect(label)}
          >
            <Icon size={18} />
            {label}
            {active === label && <span className="active-dot" />}
          </button>
        ))}
      </nav>

      <div className="side-label second">AI & INSIGHTS</div>
      <nav>
        {menu.slice(3).map(({ label, icon: Icon }) => (
          <button
            key={label}
            className={`nav-link ${active === label ? "active" : ""}`}
            onClick={() => onSelect(label)}
          >
            <Icon size={18} />
            {label}
            {active === label && <span className="active-dot" />}
          </button>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <div className="side-label">USER</div>
        <button
          className="nav-link"
          onClick={() => onSelect("Settings")}
        >
          <Settings size={18} />Settings
        </button>
        <button
          className="nav-link"
          onClick={() => onSelect("Help & Support")}
        >
          <CircleHelp size={18} />Help & Support
        </button>
        <div className="sidebar-profile">
          <div className="avatar">S</div>
          <div>
            <strong>Student</strong>
            <small>Free workspace</small>
          </div>
          <ChevronDown size={15} />
        </div>
      </div>
    </aside>
  );
}

function Header({ active, onSearch }) {
  return (
    <header className="topbar">
      <div className="breadcrumbs">
        Workspace <span>/</span> <strong>{active}</strong>
      </div>
      <div className="header-actions">
        <button className="search" onClick={onSearch}>
          <Search size={16} />
          <span>Search anything...</span>
          <kbd>⌘ K</kbd>
        </button>
        <button
          className="icon-button"
          aria-label="Notifications"
          onClick={() => window.alert("No notifications yet.")}
        >
          <Bell size={19} />
          <i />
        </button>
        <div className="top-avatar">S</div>
      </div>
    </header>
  );
}

function Overview({ onSelect, transactions, connected }) {
  const month = new Date().toLocaleDateString("en-CA").slice(0, 7);

  const monthly = transactions.filter(
    t => t.date?.slice(0, 7) === month
  );

  const expenses = monthly.filter(t => t.kind === "Expense");

  const income = monthly
    .filter(t => t.kind === "Income")
    .reduce((sum, t) => sum + Number(t.amount), 0);

  const categoryData = useMemo(() => {
    const totals = {};
    expenses.forEach(t => {
      totals[t.category] =
        (totals[t.category] || 0) + Number(t.amount);
    });

    return Object.entries(totals).map(([name, value], i) => ({
      name,
      value,
      color: palette[i % palette.length]
    }));
  }, [transactions]);

  const trend = useMemo(() => {
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date();
      d.setDate(d.getDate() - (6 - i));
      const date = d.toLocaleDateString("en-CA");

      return {
        day: d.toLocaleDateString("en-US", { weekday: "short" }),
        value: transactions
          .filter(t => t.kind === "Expense" && t.date === date)
          .reduce((sum, t) => sum + Number(t.amount), 0)
      };
    });
  }, [transactions]);

  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");

  const total = categoryData.reduce((s, c) => s + c.value, 0);

  function ask(text) {
    const query = (text || message).trim();
    if (!query) return;

    setMessage("");
    setAnswer(
      `You asked: "${query}". The chat assistant is not connected ` +
      "to an AI model yet. The spending charts use your saved transactions."
    );
  }

  return (
    <div className="overview-grid">
      <div className="main-column">
        <section className="hero panel">
          <div className="hero-content">
            <div className="eyebrow">
              <Sparkles size={13} />
              AI FINANCIAL ASSISTANT
              <span className="demo-pill">
                {connected ? "LIVE TRANSACTIONS" : "API OFFLINE"}
              </span>
            </div>
            <h1>
              Hey there! <span className="wave">✦</span>
              <br />
              How can I help you with
              <br />
              your finances today?
            </h1>
            <p>
              Smarter spending starts with better questions.
              <br />
              Your personal money companion is here.
            </p>
          </div>
          <Robot />
          <div className="hero-actions">
            {suggestions.map(s => (
              <button key={s} onClick={() => ask(s)}>
                {s} <ArrowUpRight size={13} />
              </button>
            ))}
          </div>
        </section>

        <section className="assistant-input panel">
          <div className="assistant-icon"><Sparkles size={17} /></div>
          <input
            aria-label="Ask SpendSense"
            placeholder="Ask SpendSense anything about your money..."
            value={message}
            onChange={e => setMessage(e.target.value)}
            onKeyDown={e => e.key === "Enter" && ask()}
          />
          <button onClick={() => ask()} aria-label="Send message">
            <Send size={17} />
          </button>
        </section>

        {answer && (
          <div className="demo-answer">
            <Sparkles size={16} />{answer}
          </div>
        )}

        <section className="panel breakdown">
          <div className="section-header">
            <div>
              <div className="section-kicker">YOUR EXPENSES</div>
              <h2>Spending Breakdown</h2>
            </div>
            <button
              className="subtle-button"
              onClick={() => onSelect("Transactions")}
            >
              This month <ChevronDown size={15} />
            </button>
          </div>

          <div className="breakdown-body">
            <div className="pie-wrap">
              {categoryData.length === 0 && (
                <div className="empty-chart">
                  No expenses this month yet
                </div>
              )}

              <ResponsiveContainer width="100%" height={218}>
                <PieChart>
                  <Pie
                    data={categoryData}
                    dataKey="value"
                    innerRadius={77}
                    outerRadius={100}
                    paddingAngle={4}
                    stroke="none"
                  >
                    {categoryData.map(c => (
                      <Cell key={c.name} fill={c.color} />
                    ))}
                  </Pie>
                  <Tooltip
                    formatter={v => rupees(v)}
                    contentStyle={{
                      background: "#19223c",
                      border: "1px solid #39415e",
                      borderRadius: 12,
                      color: "#fff"
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>

              <div className="pie-center">
                <span>Total spent</span>
                <strong>{rupees(total)}</strong>
                <small>This month</small>
              </div>
            </div>

            <div className="legend">
              {categoryData.length === 0 && (
                <span className="muted">
                  Add an expense to see your breakdown.
                </span>
              )}
              {categoryData.map(c => (
                <div className="legend-item" key={c.name}>
                  <span
                    className="legend-dot"
                    style={{ background: c.color }}
                  />
                  <span>{c.name}</span>
                  <strong>{rupees(c.value)}</strong>
                </div>
              ))}
            </div>
          </div>
        </section>

        <section className="panel trend">
          <div className="section-header">
            <div>
              <div className="section-kicker">THE BIG PICTURE</div>
              <h2>Spending Activity</h2>
            </div>
            <span className="positive">
              <TrendingUp size={14} /> Weekly view
            </span>
          </div>

          <ResponsiveContainer width="100%" height={155}>
            <AreaChart data={trend}>
              <defs>
                <linearGradient
                  id="purpleFill"
                  x1="0" y1="0" x2="0" y2="1"
                >
                  <stop
                    offset="0%"
                    stopColor="#9f7bff"
                    stopOpacity={0.35}
                  />
                  <stop
                    offset="100%"
                    stopColor="#9f7bff"
                    stopOpacity={0}
                  />
                </linearGradient>
              </defs>
              <CartesianGrid
                vertical={false}
                stroke="#252d47"
                strokeDasharray="3 5"
              />
              <XAxis
                dataKey="day"
                tickLine={false}
                axisLine={false}
                tick={{ fill: "#8992b1", fontSize: 11 }}
              />
              <Tooltip
                formatter={v => rupees(v)}
                contentStyle={{
                  background: "#19223c",
                  border: "1px solid #39415e",
                  color: "#fff"
                }}
              />
              <Area
                dataKey="value"
                type="monotone"
                stroke="#a98aff"
                strokeWidth={3}
                fill="url(#purpleFill)"
              />
            </AreaChart>
          </ResponsiveContainer>
        </section>
      </div>

      <div className="right-column">
        <section className="panel health">
          <div className="section-header">
            <div>
              <div className="section-kicker">
                YOUR FINANCIAL PULSE
              </div>
              <h2>Financial Health</h2>
            </div>
            <button
              className="dots-button"
              title="Illustrative score, not an ML prediction"
            >
              <CircleHelp size={17} />
            </button>
          </div>

          <div className="health-ring">
            <ProgressRing value={76} size={168}>
              <strong>76<span>/100</span></strong>
              <small>Illustrative</small>
            </ProgressRing>
          </div>

          <div className="health-foot">
            <span className="health-indicator" />
            Looking good!
            <span className="muted"> Illustrative only</span>
          </div>
        </section>

        <section className="panel overview-card">
          <div className="section-header">
            <div>
              <div className="section-kicker">AT A GLANCE</div>
              <h2>Quick Overview</h2>
            </div>
            <Wallet size={18} className="muted" />
          </div>

          <div className="overview-total">
            <span>Total balance</span>
            <strong>{rupees(income - total)}</strong>
          </div>

          <div className="segment-bar"><i /><i /><i /></div>

          <div className="balance-row">
            <div>
              <span className="mini-dot cyan" />
              Income <strong>{rupees(income)}</strong>
            </div>
            <div>
              <span className="mini-dot purple" />
              Expenses <strong>{rupees(total)}</strong>
            </div>
          </div>

          <div className="balance-row second-row">
            <div>
              <span className="mini-dot yellow" />
              Savings <strong>Not tracked</strong>
            </div>
            <div>
              <span className="mini-dot gray" />
              Bills{" "}
              <strong>
                {rupees(
                  categoryData.find(c => c.name === "Bills")?.value || 0
                )}
              </strong>
            </div>
          </div>
        </section>

        <section className="panel goals">
          <div className="section-header">
            <div>
              <div className="section-kicker">
                ILLUSTRATIVE GOALS · DEMO
              </div>
              <h2>Savings Goals</h2>
            </div>
            <button
              className="add-button"
              onClick={() => onSelect("Savings Goals")}
            >
              <Plus size={18} />
            </button>
          </div>

          <div className="goals-rings">
            <div>
              <ProgressRing value={68} color="#b291ff" size={118}>
                <Target size={18} />
                <strong>68%</strong>
              </ProgressRing>
              <strong>New Laptop</strong>
              <small>Rs. 34k / 50k</small>
            </div>
            <div>
              <ProgressRing value={42} color="#4bd9dc" size={118}>
                <Zap size={18} />
                <strong>42%</strong>
              </ProgressRing>
              <strong>Emergency Fund</strong>
              <small>Rs. 12.6k / 30k</small>
            </div>
          </div>
        </section>

        <div className="tip">
          <Sparkles size={16} />
          <span>Small steps today, smarter money tomorrow.</span>
        </div>
      </div>
    </div>
  );
}

function Transactions({ transactions, refresh, connected }) {
  const [form, setForm] = useState({
    date: new Date().toLocaleDateString("en-CA"),
    amount: "",
    kind: "Expense",
    category: "Food",
    description: ""
  });

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [prediction, setPrediction] = useState(null);
  const [predicting, setPredicting] = useState(false);
  const [predictionError, setPredictionError] = useState("");
  const [manualCategory, setManualCategory] = useState(false);

  const update = (key, value) =>
    setForm(f => ({ ...f, [key]: value }));

  useEffect(() => {
    const description = form.description.trim();

    setPrediction(null);
    setPredictionError("");

    if (
      !connected ||
      form.kind !== "Expense" ||
      description.length < 5
    ) {
      setPredicting(false);
      return;
    }

    const controller = new AbortController();
    setPredicting(true);

    const timer = setTimeout(async () => {
      try {
        const response = await fetch(
          `${API}/api/ml/predict-category`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ description }),
            signal: controller.signal
          }
        );

        if (!response.ok) {
          throw new Error("AI category suggestion unavailable.");
        }

        const result = await response.json();

        if (!controller.signal.aborted) {
          setPrediction(result);
          setPredicting(false);

          if (!manualCategory) {
            setForm(current => ({
              ...current,
              category: result.predicted_category
            }));
          }
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setPredictionError(err.message);
          setPredicting(false);
        }
      }
    }, 700);

    return () => {
      clearTimeout(timer);
      controller.abort();
    };
  }, [form.description, form.kind, connected, manualCategory]);

  async function submit(e) {
    e.preventDefault();
    setError("");
    setSuccess("");
    setBusy(true);

    try {
      const res = await fetch(`${API}/api/transactions`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          amount: Number(form.amount)
        })
      });

      const body = await res.json();

      if (!res.ok) {
        throw new Error(
          typeof body.detail === "string"
            ? body.detail
            : "Could not save transaction"
        );
      }

      setForm(f => ({
        ...f,
        amount: "",
        description: ""
      }));

      setPrediction(null);
      setPredictionError("");
      setManualCategory(false);
      setSuccess("Transaction saved to your SpendSense database.");

      await refresh();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id) {
    if (!window.confirm("Delete this transaction?")) return;

    setError("");

    try {
      const res = await fetch(
        `${API}/api/transactions/${id}`,
        { method: "DELETE" }
      );

      if (!res.ok) throw new Error("Delete failed");

      await refresh();
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="transaction-layout">
      <section className="panel transaction-panel">
        <div className="section-kicker">
          REAL EXPENSE TRACKING
        </div>
        <h2>Add a transaction</h2>

        {!connected && (
          <p className="form-error">
            Python API offline. Start FastAPI on port 8000.
          </p>
        )}

        <form onSubmit={submit} className="transaction-form">
          <label>
            Description
            <input
              required
              maxLength={300}
              value={form.description}
              onChange={e => {
                update("description", e.target.value);
                setManualCategory(false);
              }}
              placeholder="e.g. Bought biryani at university"
            />
          </label>

          {form.kind === "Expense" &&
            form.description.trim().length >= 5 && (
              <div style={{
                padding: 14,
                marginTop: 8,
                marginBottom: 12,
                background: "rgba(169,138,255,0.09)",
                border: "1px solid rgba(169,138,255,0.35)",
                borderRadius: 12
              }}>
                <div style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  color: "#c5b1ff",
                  marginBottom: 8
                }}>
                  <BrainCircuit size={19} />
                  <strong>SpendSense AI Prediction</strong>
                </div>

                {predicting && (
                  <p className="muted">
                    Analyzing your expense description...
                  </p>
                )}

                {!predicting && prediction && (
                  <>
                    <p>
                      Suggested category:{" "}
                      <strong>{prediction.predicted_category}</strong>
                    </p>
                    <p className="muted">
                      Model probability:{" "}
                      {(prediction.confidence * 100).toFixed(2)}%
                    </p>

                    <div style={{
                      height: 7,
                      borderRadius: 8,
                      background: "#30344f",
                      overflow: "hidden"
                    }}>
                      <div style={{
                        height: "100%",
                        width: `${prediction.confidence * 100}%`,
                        background: "#a98aff"
                      }} />
                    </div>

                    {manualCategory && (
                      <p className="muted">
                        Manual category selected. Your choice will be saved.
                      </p>
                    )}
                  </>
                )}

                {predictionError && (
                  <p className="muted">{predictionError}</p>
                )}
              </div>
            )}

          <div className="form-row">
            <label>
              Amount (PKR)
              <input
                required
                type="number"
                min="0.01"
                step="0.01"
                value={form.amount}
                onChange={e => update("amount", e.target.value)}
              />
            </label>
            <label>
              Date
              <input
                required
                type="date"
                value={form.date}
                onChange={e => update("date", e.target.value)}
              />
            </label>
          </div>

          <div className="form-row">
            <label>
              Type
              <select
                value={form.kind}
                onChange={e => {
                  update("kind", e.target.value);
                  setManualCategory(false);
                }}
              >
                <option>Expense</option>
                <option>Income</option>
              </select>
            </label>

            <label>
              Category
              <select
                value={form.category}
                onChange={e => {
                  update("category", e.target.value);
                  setManualCategory(true);
                }}
              >
                {categories.map(c => (
                  <option key={c}>{c}</option>
                ))}
              </select>
            </label>
          </div>

          {error && <p className="form-error">{error}</p>}
          {success && <p className="form-success">{success}</p>}

          <button
            className="primary-button"
            disabled={busy || !connected}
          >
            {busy ? "Saving..." : "Save transaction"}
          </button>
        </form>
      </section>

      <section className="panel transaction-panel">
        <div className="section-kicker">YOUR DATABASE</div>
        <h2>
          Recent transactions{" "}
          <span className="muted">({transactions.length})</span>
        </h2>

        {transactions.length === 0 ? (
          <p className="empty-transactions">
            No transactions yet. Add your first one!
          </p>
        ) : (
          <div className="transaction-list">
            {transactions.map(t => (
              <div className="transaction-item" key={t.id}>
                <div>
                  <strong>{t.description}</strong>
                  <small>
                    {t.date} · {t.category} · {t.kind}
                  </small>
                </div>
                <span className={
                  t.kind === "Income" ? "positive" : ""
                }>
                  {t.kind === "Income" ? "+" : "−"}
                  {rupees(t.amount)}
                </span>
                <button
                  onClick={() => remove(t.id)}
                  aria-label={`Delete ${t.description}`}
                >
                  Delete
                </button>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function ClassifierPlayground() {
  const examples = [
    "Bought biryani for lunch at university",
    "Paid 500 rupees for a rickshaw ride",
    "Bought medicine from the pharmacy",
    "Paid my university semester fee",
    "Bought groceries for the hostel"
  ];

  const [description, setDescription] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showEmbedding, setShowEmbedding] = useState(false);

  const cardStyle = {
    padding: 22,
    borderRadius: 16,
    background: "rgba(169,138,255,0.045)",
    border: "1px solid rgba(169,138,255,0.18)"
  };

  async function predict() {
    const text = description.trim();

    if (!text) {
      setError("Enter an expense description first.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);

    try {
      const response = await fetch(
        `${API}/api/ml/predict-category`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ description: text })
        }
      );

      if (!response.ok) {
        const body = await response.json().catch(() => ({}));
        throw new Error(
          typeof body.detail === "string"
            ? body.detail
            : `Prediction failed (${response.status})`
        );
      }

      const data = await response.json();
      setResult(data);
    } catch (err) {
      setError(
        err.message || "Could not connect to the ML model."
      );
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setDescription("");
    setResult(null);
    setError("");
    setShowEmbedding(false);
  }

  const probabilities = result
    ? Object.entries(result.probabilities).sort(
        (a, b) => b[1] - a[1]
      )
    : [];

  const pct = value =>
    `${(Number(value) * 100).toFixed(2)}%`;

  return (
    <section className="panel" style={{ padding: 24 }}>
      <div className="section-kicker">
        EXPERIMENT WITH YOUR TRAINED MODEL
      </div>

      <div style={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        gap: 12,
        flexWrap: "wrap"
      }}>
        <div>
          <h2>
            <BrainCircuit
              size={22}
              style={{
                display: "inline",
                verticalAlign: "middle",
                marginRight: 8,
                color: "#a98aff"
              }}
            />
            Live Classifier Playground
          </h2>

          <p className="muted">
            Test your expense classifier using new descriptions.
          </p>
        </div>

        <button
          type="button"
          onClick={reset}
          style={{
            display: "flex",
            alignItems: "center",
            gap: 7,
            padding: "9px 14px",
            borderRadius: 10,
            border: "1px solid #41425d",
            background: "transparent",
            color: "inherit",
            cursor: "pointer"
          }}
        >
          <RotateCcw size={15} />
          Reset
        </button>
      </div>

      <div style={{ marginTop: 24 }}>
        <label
          htmlFor="classifier-description"
          style={{
            display: "block",
            fontWeight: 600,
            marginBottom: 10
          }}
        >
          Expense description
        </label>

        <textarea
          id="classifier-description"
          value={description}
          onChange={e => {
            setDescription(e.target.value);
            setResult(null);
            setError("");
          }}
          placeholder="e.g. I bought medicine for 300 rupees"
          maxLength={300}
          rows={3}
          style={{
            width: "100%",
            boxSizing: "border-box",
            padding: 16,
            borderRadius: 12,
            background: "#151c31",
            color: "#fff",
            border: "1px solid #3b4262",
            fontSize: 14,
            resize: "vertical",
            fontFamily: "inherit"
          }}
        />

        <div style={{
          display: "flex",
          justifyContent: "space-between",
          marginTop: 6
        }}>
          <small className="muted">
            Describe a purchase in natural language.
          </small>
          <small className="muted">
            {description.length}/300
          </small>
        </div>
      </div>

      <div style={{ marginTop: 18 }}>
        <p className="muted" style={{ marginBottom: 10 }}>
          Or try an example:
        </p>

        <div style={{
          display: "flex",
          flexWrap: "wrap",
          gap: 8
        }}>
          {examples.map((example, index) => (
            <button
              key={example}
              type="button"
              onClick={() => {
                setDescription(example);
                setResult(null);
                setError("");
              }}
              style={{
                padding: "9px 12px",
                borderRadius: 20,
                border: "1px solid rgba(169,138,255,0.3)",
                background: "rgba(169,138,255,0.08)",
                color: "#d6c7ff",
                fontSize: 12,
                cursor: "pointer"
              }}
            >
              Example {index + 1}
            </button>
          ))}
        </div>
      </div>

      <button
        type="button"
        onClick={predict}
        disabled={loading || !description.trim()}
        style={{
          marginTop: 24,
          width: "100%",
          padding: "15px 18px",
          borderRadius: 12,
          border: "none",
          background: "#9876f5",
          color: "#fff",
          fontWeight: 700,
          fontSize: 15,
          cursor: loading ? "wait" : "pointer",
          opacity: loading || !description.trim() ? 0.6 : 1,
          display: "flex",
          justifyContent: "center",
          alignItems: "center",
          gap: 10
        }}
      >
        {loading ? (
          <>
            <BrainCircuit size={19} />
            Running your ML model...
          </>
        ) : (
          <>
            <Sparkles size={19} />
            Predict Category
          </>
        )}
      </button>

      {error && (
        <div style={{
          marginTop: 18,
          padding: 14,
          borderRadius: 12,
          background: "rgba(255,100,100,0.08)",
          border: "1px solid rgba(255,100,100,0.3)",
          display: "flex",
          gap: 10,
          alignItems: "center"
        }}>
          <AlertCircle size={18} color="#ff8888" />
          <span>{error}</span>
        </div>
      )}

      {result && (
        <div style={{
          display: "grid",
          gap: 20,
          marginTop: 28
        }}>
          <div style={cardStyle}>
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              color: "#b8a2ff"
            }}>
              <CheckCircle2 size={19} />
              <strong>Prediction complete</strong>
            </div>

            <p className="muted" style={{ marginTop: 14 }}>
              Your model predicts:
            </p>

            <h1 style={{
              margin: "8px 0",
              fontSize: 34,
              color:
                categoryColors[result.predicted_category] ||
                "#a98aff"
            }}>
              {result.predicted_category}
            </h1>

            <div style={{
              display: "flex",
              justifyContent: "space-between",
              gap: 12,
              flexWrap: "wrap"
            }}>
              <span className="muted">
                Highest model probability
              </span>
              <strong style={{ fontSize: 22 }}>
                {pct(result.confidence)}
              </strong>
            </div>

            <div style={{
              marginTop: 12,
              height: 11,
              borderRadius: 20,
              background: "#30344f",
              overflow: "hidden"
            }}>
              <div style={{
                width: `${result.confidence * 100}%`,
                height: "100%",
                background: "#a98aff",
                borderRadius: 20
              }} />
            </div>

            <p className="muted" style={{
              fontSize: 12,
              marginTop: 12
            }}>
              Model probability is not a guarantee of correctness.
            </p>
          </div>

          <div style={cardStyle}>
            <h3 style={{ marginTop: 0 }}>
              Category Probabilities
            </h3>

            <p className="muted">
              Probability distribution across expense categories.
            </p>

            <div style={{
              display: "grid",
              gap: 17,
              marginTop: 20
            }}>
              {probabilities.map(([category, probability]) => (
                <div key={category}>
                  <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: 7
                  }}>
                    <strong style={{ fontSize: 13 }}>
                      {category}
                    </strong>
                    <span style={{ fontSize: 13 }}>
                      {pct(probability)}
                    </span>
                  </div>

                  <div style={{
                    height: 9,
                    background: "#30344f",
                    borderRadius: 20,
                    overflow: "hidden"
                  }}>
                    <div style={{
                      width: `${Math.max(
                        0,
                        Math.min(100, probability * 100)
                      )}%`,
                      height: "100%",
                      borderRadius: 20,
                      background:
                        categoryColors[category] || "#a98aff",
                      transition: "width 0.35s ease"
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={cardStyle}>
            <div className="section-kicker">
              UNDER THE HOOD
            </div>

            <h3>How your model made this prediction</h3>

            <div style={{
              display: "grid",
              gap: 10,
              marginTop: 18,
              textAlign: "center"
            }}>
              {[
                ["1. Input Text", result.description],
                [
                  "2. SentenceTransformer",
                  `${result.embedding_dimensions}-dimensional embedding`
                ],
                ["3. Classifier", result.model.classifier],
                ["4. Predicted Category", result.predicted_category]
              ].map(([title, detail], index) => (
                <div key={title}>
                  {index > 0 && (
                    <div style={{
                      color: "#a98aff",
                      marginBottom: 10
                    }}>
                      ↓
                    </div>
                  )}

                  <div style={{
                    padding: 15,
                    background: "rgba(169,138,255,0.1)",
                    border: "1px solid rgba(169,138,255,0.2)",
                    borderRadius: 12
                  }}>
                    <strong>{title}</strong>
                    <p className="muted" style={{
                      marginBottom: 0,
                      overflowWrap: "anywhere"
                    }}>
                      {detail}
                    </p>
                  </div>
                </div>
              ))}
            </div>

            <button
              type="button"
              onClick={() => setShowEmbedding(v => !v)}
              style={{
                marginTop: 20,
                padding: "10px 0",
                background: "transparent",
                border: "none",
                color: "#b8a2ff",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: 8
              }}
            >
              {showEmbedding ? (
                <ChevronUp size={17} />
              ) : (
                <ChevronDown size={17} />
              )}
              {showEmbedding
                ? "Hide embedding preview"
                : "View embedding preview"}
            </button>

            {showEmbedding && (
              <div style={{
                marginTop: 12,
                padding: 16,
                background: "#11182a",
                borderRadius: 12
              }}>
                <p className="muted">
                  First {result.embedding_preview.length} of{" "}
                  {result.embedding_dimensions} embedding values:
                </p>

                <div style={{
                  display: "grid",
                  gridTemplateColumns:
                    "repeat(auto-fit,minmax(95px,1fr))",
                  gap: 8
                }}>
                  {result.embedding_preview.map((value, i) => (
                    <div key={i} style={{
                      padding: 10,
                      background: "#202a43",
                      borderRadius: 8,
                      textAlign: "center"
                    }}>
                      <small className="muted">
                        Dimension {i + 1}
                      </small>
                      <div style={{
                        fontFamily: "monospace",
                        marginTop: 5,
                        fontSize: 12
                      }}>
                        {Number(value).toFixed(4)}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </section>
  );
}

function ModelArena() {
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();

    fetch(`${API}/api/ml/evaluation`, {
      signal: controller.signal
    })
      .then(async response => {
        if (!response.ok) {
          throw new Error(
            `Evaluation API returned ${response.status}`
          );
        }
        return response.json();
      })
      .then(data => setEvaluation(data))
      .catch(err => {
        if (!controller.signal.aborted) setError(err.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });

    return () => controller.abort();
  }, []);

  if (loading) {
    return (
      <section className="panel" style={{ padding: 24 }}>
        Loading real ML evaluation results...
      </section>
    );
  }

  if (error) {
    return (
      <section className="panel" style={{ padding: 24 }}>
        <p className="form-error">{error}</p>
      </section>
    );
  }

  if (!evaluation) return null;

  const { model, report, confusion_matrix: cm } = evaluation;
  const labels = cm.labels;
  const matrix = cm.matrix;

  const pct = value => `${(value * 100).toFixed(2)}%`;

  const metrics = [
    ["Accuracy", report.accuracy],
    ["Macro Precision", report["macro avg"].precision],
    ["Macro Recall", report["macro avg"].recall],
    ["Macro F1", report["macro avg"]["f1-score"]]
  ];

  const categoryScores = labels.map(label => ({
    category: label,
    f1: Number(
      (report[label]["f1-score"] * 100).toFixed(2)
    )
  }));

  const maxValue = Math.max(1, ...matrix.flat());

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section className="panel" style={{ padding: 24 }}>
        <div className="section-kicker">
          REAL MACHINE LEARNING RESULTS
        </div>
        <h2>Model Arena 🧪</h2>
        <p className="muted">
          Evaluation loaded from your saved classifier report.
        </p>

        <div style={{
          display: "grid",
          gridTemplateColumns:
            "repeat(auto-fit,minmax(150px,1fr))",
          gap: 12,
          marginTop: 20
        }}>
          {metrics.map(([name, value]) => (
            <div key={name} style={{
              padding: 18,
              borderRadius: 14,
              background: "rgba(169,138,255,0.1)",
              border: "1px solid rgba(169,138,255,0.2)"
            }}>
              <small className="muted">{name}</small>
              <h2 style={{ margin: "8px 0" }}>
                {pct(value)}
              </h2>
            </div>
          ))}
        </div>
      </section>

      <section className="panel" style={{ padding: 24 }}>
        <div className="section-kicker">
          PERFORMANCE ANALYSIS
        </div>
        <h2>F1-score by category</h2>

        <div style={{
          width: "100%",
          height: 310,
          marginTop: 20
        }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={categoryScores}
              margin={{
                top: 10, right: 15, left: 0, bottom: 20
              }}
            >
              <CartesianGrid
                stroke="#30344f"
                strokeDasharray="3 3"
              />
              <XAxis
                dataKey="category"
                interval={0}
                angle={-30}
                textAnchor="end"
                height={85}
                tick={{
                  fill: "#aeb4ce",
                  fontSize: 10
                }}
              />
              <Tooltip
                formatter={value => `${value}%`}
                contentStyle={{
                  background: "#19223c",
                  border: "1px solid #39415e",
                  color: "#fff"
                }}
              />
              <Area
                type="monotone"
                dataKey="f1"
                stroke="#a98aff"
                fill="#a98aff"
                fillOpacity={0.2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </section>

      <section className="panel" style={{ padding: 24 }}>
        <div className="section-kicker">
          CLASSIFICATION ERRORS
        </div>
        <h2>Confusion Matrix</h2>
        <p className="muted">
          Rows = actual category. Columns = predicted category.
          Orange cells show mistakes.
        </p>

        <div style={{
          overflowX: "auto",
          marginTop: 20
        }}>
          <table style={{
            borderCollapse: "separate",
            borderSpacing: 4,
            minWidth: 760,
            width: "100%",
            textAlign: "center"
          }}>
            <thead>
              <tr>
                <th>Actual / Predicted</th>
                {labels.map(label => (
                  <th
                    key={label}
                    style={{ fontSize: 11 }}
                  >
                    {label}
                  </th>
                ))}
              </tr>
            </thead>

            <tbody>
              {matrix.map((row, i) => (
                <tr key={labels[i]}>
                  <th style={{
                    fontSize: 12,
                    textAlign: "left"
                  }}>
                    {labels[i]}
                  </th>

                  {row.map((value, j) => (
                    <td
                      key={j}
                      title={
                        `${labels[i]} predicted as ` +
                        `${labels[j]}: ${value}`
                      }
                      style={{
                        padding: "12px 6px",
                        borderRadius: 7,
                        color: "#fff",
                        background:
                          i === j
                            ? `rgba(134,99,245,${
                                0.25 + 0.75 * value / maxValue
                              })`
                            : value > 0
                              ? `rgba(245,158,70,${
                                  0.25 + 0.75 * value / maxValue
                                })`
                              : "rgba(255,255,255,0.04)"
                      }}
                    >
                      {value}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel" style={{ padding: 24 }}>
        <div className="section-kicker">
          MODEL ARCHITECTURE
        </div>
        <h2>What's powering SpendSense?</h2>

        <p>
          Text encoder: <strong>{model.encoder}</strong>
        </p>
        <p>
          Classifier: <strong>{model.classifier}</strong>
        </p>
        <p>
          Embedding dimensions:{" "}
          <strong>{model.embedding_dimensions}</strong>
        </p>
        <p>
          Evaluation examples:{" "}
          <strong>{cm.total_samples.toLocaleString()}</strong>
        </p>
        <p className="muted">
          Results are based on synthetic evaluation data.
          Real-world generalization has not yet been established.
        </p>
      </section>

      <ClassifierPlayground />
    </div>
  );
}

function Placeholder({ page, onBack }) {
  const descriptions = {
    "Capture Studio":
      "Receipt OCR and text-based expense capture are planned.",
    "Spending DNA":
      "K-Means spending persona analysis is planned.",
    "Pattern Detective":
      "Anomaly detection results are planned.",
    "Savings Goals":
      "Savings goal management is not implemented yet.",
    "Settings":
      "Settings are not yet implemented.",
    "Help & Support":
      "Help content will be added later."
  };

  return (
    <div className="placeholder panel">
      <div className="placeholder-icon">
        <Sparkles size={29} />
      </div>
      <div className="section-kicker">
        SPENDSENSE INTELLIGENCE LAB
      </div>
      <h1>{page}</h1>
      <p>
        {descriptions[page] ||
          "This module is being prepared."}
      </p>
      <div className="placeholder-note">
        <ShieldCheck size={18} />
        No fake predictions. This module will use real
        outputs when its backend is integrated.
      </div>
      <button
        className="primary-button"
        onClick={onBack}
      >
        Back to Overview
      </button>
    </div>
  );
}

export default function App() {
  const [active, setActive] = useState("Overview");
  const [searchOpen, setSearchOpen] = useState(false);
  const [transactions, setTransactions] = useState([]);
  const [connected, setConnected] = useState(false);

  async function refresh() {
    try {
      const res = await fetch(`${API}/api/transactions`);

      if (!res.ok) {
        throw new Error("API unavailable");
      }

      const rows = await res.json();
      setTransactions(rows);
      setConnected(true);
    } catch {
      setConnected(false);
    }
  }

  useEffect(() => {
    refresh();
  }, []);

  return (
    <div className="page-shell">
      <div className="dashboard">
        <Sidebar active={active} onSelect={setActive} />

        <div className="app-main">
          <Header
            active={active}
            onSearch={() => setSearchOpen(true)}
          />

          <main className="content">
            <div className="page-heading">
              <div>
                <div className="greeting-line">
                  {new Date()
                    .toLocaleDateString("en-US", {
                      weekday: "long",
                      month: "long",
                      day: "numeric"
                    })
                    .toUpperCase()}
                  {" "}
                  <span className="tiny-sparkle">✦</span>
                  {" "}YOUR MONEY SPACE
                </div>

                <h1>
                  {active}
                  <span className="heading-star"> ✳</span>
                </h1>

                <p>
                  {active === "Overview"
                    ? "Here's what's happening with your money."
                    : "Your personal financial intelligence workspace."}
                </p>
              </div>

              <div className="mode-tag">
                <span />
                STUDENT MODE
                <ChevronDown size={14} />
              </div>
            </div>

            {active === "Overview" ? (
              <Overview
                onSelect={setActive}
                transactions={transactions}
                connected={connected}
              />
            ) : active === "Transactions" ? (
              <Transactions
                transactions={transactions}
                refresh={refresh}
                connected={connected}
              />
            ) : active === "Capture Studio" ? (
              <CaptureStudio refresh={refresh} />
            ) : active === "Model Arena" ? (
              <ModelArena />
            ) : active === "Spending DNA" ? (
              <SpendingDNA transactions={transactions} onSelect={setActive} />
            ) : active === "Pattern Detective" ? (
              <PatternDetective transactions={transactions} />
            ) : (
              <Placeholder
                page={active}
                onBack={() => setActive("Overview")}
              />
            )}

            <footer>
              SpendSense Intelligence Lab
              <span> • </span>
              Connected transaction tracking
              <span> • </span>
              Financial health and savings goals are illustrative
            </footer>
          </main>
        </div>
      </div>

      {searchOpen && (
        <div
          className="modal-backdrop"
          onClick={() => setSearchOpen(false)}
        >
          <div
            className="search-modal"
            onClick={e => e.stopPropagation()}
          >
            <div>
              <Search size={20} />
              <input
                autoFocus
                placeholder="Search modules..."
                onKeyDown={e => {
                  if (e.key === "Escape") {
                    setSearchOpen(false);
                  }
                }}
              />
              <button onClick={() => setSearchOpen(false)}>
                Esc
              </button>
            </div>

            {menu.map(({ label, icon: Icon }) => (
              <button
                key={label}
                onClick={() => {
                  setActive(label);
                  setSearchOpen(false);
                }}
              >
                <Icon size={17} />
                {label}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
