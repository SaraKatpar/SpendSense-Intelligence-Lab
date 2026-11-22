
import { useEffect, useState } from "react";
import {
  ShieldCheck,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  FlaskConical,
} from "lucide-react";

const API = "http://127.0.0.1:8000";

const money = n =>
  `Rs. ${Number(n || 0).toLocaleString("en-PK")}`;

const panelStyle = {
  padding: 24,
  borderRadius: 18,
};

const tileStyle = {
  padding: 18,
  borderRadius: 14,
  background: "rgba(169,138,255,0.07)",
  border: "1px solid rgba(169,138,255,0.2)",
};

const muted = { color: "#aeb4ce" };

function Metric({ label, value, note }) {
  return (
    <div style={tileStyle}>
      <div style={{ ...muted, fontSize: 13 }}>{label}</div>
      <h2 style={{ margin: "9px 0" }}>{value}</h2>
      {note && (
        <div style={{ ...muted, fontSize: 12 }}>{note}</div>
      )}
    </div>
  );
}

export default function PatternDetective({ transactions = [] }) {
  const [data, setData] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setError("");

      try {
        const [predictionResponse, evaluationResponse] =
          await Promise.all([
            fetch(`${API}/api/ml/pattern-detective`, {
              signal: controller.signal,
            }),
            fetch(`${API}/api/ml/pattern-detective/evaluation`, {
              signal: controller.signal,
            }),
          ]);

        if (!predictionResponse.ok || !evaluationResponse.ok) {
          const failed = !predictionResponse.ok
            ? predictionResponse
            : evaluationResponse;

          const body = await failed.json().catch(() => ({}));

          throw new Error(
            body.detail || `API error ${failed.status}`
          );
        }

        const predictionData = await predictionResponse.json();
        const evaluationData = await evaluationResponse.json();

        if (!controller.signal.aborted) {
          setData(predictionData);
          setEvaluation(evaluationData);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err.message || "Could not load Pattern Detective.");
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false);
        }
      }
    }

    load();
    return () => controller.abort();
  }, [refreshKey, transactions]);

  const rows = data?.transactions || [];

  const visibleRows = rows.filter(item => {
    if (filter === "flagged") return item.is_anomaly;
    if (filter === "typical") return !item.is_anomaly;
    return true;
  });

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section className="panel" style={panelStyle}>
        <div style={{
          display: "flex",
          justifyContent: "space-between",
          gap: 16,
          flexWrap: "wrap",
          alignItems: "flex-start",
        }}>
          <div>
            <div className="section-kicker">
              UNSUPERVISED ANOMALY DETECTION
            </div>

            <h2 style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
            }}>
              <ShieldCheck color="#a98aff" />
              Pattern Detective
            </h2>

            <p style={muted}>
              Review unusual expenses using your trained
              Isolation Forest model.
            </p>
          </div>

          <button
            type="button"
            disabled={loading}
            onClick={() => setRefreshKey(n => n + 1)}
            style={{
              ...tileStyle,
              color: "inherit",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              gap: 8,
            }}
          >
            <RefreshCw size={16} />
            Refresh
          </button>
        </div>
      </section>

      {loading && (
        <section className="panel" style={panelStyle}>
          <p style={muted}>Analyzing saved transactions...</p>
        </section>
      )}

      {error && (
        <section className="panel" style={panelStyle}>
          <p style={{ color: "#ff9b9b" }}>
            <AlertTriangle size={18} style={{
              display: "inline",
              verticalAlign: "middle",
              marginRight: 8,
            }} />
            {error}
          </p>
          <p style={muted}>
            Confirm that FastAPI is running on port 8000.
          </p>
        </section>
      )}

      {!loading && !error && data && (
        <>
          <section className="panel" style={panelStyle}>
            <div className="section-kicker">
              LIVE TRANSACTION ANALYSIS
            </div>

            <h2>Expense anomaly overview</h2>

            <div style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit, minmax(160px, 1fr))",
              gap: 12,
              marginTop: 18,
            }}>
              <Metric
                label="Analyzed"
                value={data.total_analyzed}
                note="Supported saved expenses"
              />
              <Metric
                label="Needs review"
                value={data.anomaly_count}
                note="Flagged by Isolation Forest"
              />
              <Metric
                label="Typical"
                value={data.typical_count}
                note="Not flagged by the model"
              />
              <Metric
                label="Excluded"
                value={data.excluded_transactions}
                note="Invalid or unsupported expenses"
              />
            </div>

            {data.status === "insufficient_data" ? (
              <div style={{ ...tileStyle, marginTop: 18 }}>
                <p>{data.message}</p>
              </div>
            ) : data.anomaly_count === 0 ? (
              <div style={{
                ...tileStyle,
                marginTop: 18,
                display: "flex",
                gap: 12,
                alignItems: "flex-start",
              }}>
                <CheckCircle2 color="#7fdca9" />
                <div>
                  <strong>No expenses flagged</strong>
                  <p style={{ ...muted, marginBottom: 0 }}>
                    None of the analyzed transactions crossed
                    the model's anomaly threshold. This does
                    not guarantee that every expense is normal
                    or financially appropriate.
                  </p>
                </div>
              </div>
            ) : (
              <div style={{
                ...tileStyle,
                marginTop: 18,
                display: "flex",
                gap: 12,
                alignItems: "flex-start",
              }}>
                <AlertTriangle color="#ffc879" />
                <div>
                  <strong>
                    {data.anomaly_count} expense(s) need review
                  </strong>
                  <p style={{ ...muted, marginBottom: 0 }}>
                    These expenses differ from the synthetic
                    training distribution. Review them for
                    context; they are not necessarily mistakes.
                  </p>
                </div>
              </div>
            )}
          </section>

          <section className="panel" style={panelStyle}>
            <div className="section-kicker">
              TRANSACTION EXPLORER
            </div>

            <h2>Expenses ranked by anomaly score</h2>

            <p style={muted}>
              Higher scores indicate greater anomaly according
              to the model. Scores above zero are flagged.
              They are not percentages or probabilities.
            </p>

            <div style={{
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
              margin: "18px 0",
            }}>
              {[
                ["all", "All"],
                ["flagged", "Needs review"],
                ["typical", "Typical"],
              ].map(([value, label]) => (
                <button
                  key={value}
                  type="button"
                  onClick={() => setFilter(value)}
                  style={{
                    ...tileStyle,
                    padding: "9px 15px",
                    cursor: "pointer",
                    color: "inherit",
                    background: filter === value
                      ? "rgba(169,138,255,0.28)"
                      : tileStyle.background,
                    borderColor: filter === value
                      ? "#a98aff"
                      : "rgba(169,138,255,0.2)",
                  }}
                >
                  {label}
                </button>
              ))}
            </div>

            <div style={{ display: "grid", gap: 12 }}>
              {visibleRows.length === 0 ? (
                <div style={tileStyle}>
                  <p style={muted}>
                    No transactions match this filter.
                  </p>
                </div>
              ) : visibleRows.map((item, index) => (
                <div
                  key={`${item.id ?? index}-${item.date}`}
                  style={{
                    ...tileStyle,
                    borderColor: item.is_anomaly
                      ? "rgba(255,180,100,0.65)"
                      : "rgba(169,138,255,0.2)",
                  }}
                >
                  <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 16,
                    flexWrap: "wrap",
                  }}>
                    <div style={{ flex: 1, minWidth: 170 }}>
                      <strong>
                        {item.description || item.category}
                      </strong>
                      <p style={{
                        ...muted,
                        fontSize: 13,
                        margin: "7px 0",
                      }}>
                        {item.category} · {item.date}
                      </p>
                    </div>

                    <div style={{ textAlign: "right" }}>
                      <strong>{money(item.amount)}</strong>
                      <div style={{
                        marginTop: 8,
                        fontSize: 12,
                        color: item.is_anomaly
                          ? "#ffc879"
                          : "#7fdca9",
                      }}>
                        {item.is_anomaly
                          ? "Needs review"
                          : "Typical"}
                      </div>
                    </div>
                  </div>

                  <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    gap: 12,
                    flexWrap: "wrap",
                    marginTop: 12,
                    fontSize: 13,
                  }}>
                    <span style={muted}>
                      Anomaly score
                    </span>
                    <strong style={{
                      color: item.is_anomaly
                        ? "#ffc879"
                        : "#c8b6ff",
                    }}>
                      {Number(item.anomaly_score).toFixed(6)}
                    </strong>
                  </div>

                  <p style={{
                    ...muted,
                    fontSize: 12,
                    marginBottom: 0,
                    marginTop: 12,
                  }}>
                    {item.reason}
                  </p>
                </div>
              ))}
            </div>
          </section>
        </>
      )}

      {!loading && !error && evaluation && (
        <section className="panel" style={panelStyle}>
          <div className="section-kicker">
            REAL MODEL EVALUATION
          </div>

          <h2 style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
          }}>
            <FlaskConical color="#a98aff" />
            Inside Isolation Forest
          </h2>

          <div style={{
            display: "grid",
            gridTemplateColumns:
              "repeat(auto-fit, minmax(150px, 1fr))",
            gap: 12,
            marginTop: 18,
          }}>
            <Metric
              label="Precision"
              value={`${(evaluation.precision * 100).toFixed(2)}%`}
            />
            <Metric
              label="Recall"
              value={`${(evaluation.recall * 100).toFixed(2)}%`}
            />
            <Metric
              label="F1 Score"
              value={`${(evaluation.f1_score * 100).toFixed(2)}%`}
            />
            <Metric
              label="ROC AUC"
              value={Number(evaluation.roc_auc).toFixed(4)}
            />
            <Metric
              label="Average Precision"
              value={Number(
                evaluation.average_precision
              ).toFixed(4)}
            />
            <Metric
              label="Training samples"
              value={evaluation.training_samples}
            />
          </div>

          <div style={{ ...tileStyle, marginTop: 20 }}>
            <strong>Confusion matrix</strong>

            <div style={{ overflowX: "auto", marginTop: 12 }}>
              <table style={{
                width: "100%",
                borderCollapse: "collapse",
                textAlign: "center",
              }}>
                <thead>
                  <tr>
                    <th></th>
                    <th>Predicted typical</th>
                    <th>Predicted anomaly</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <th>Actually typical</th>
                    <td>{evaluation.confusion_matrix?.[0]?.[0]}</td>
                    <td>{evaluation.confusion_matrix?.[0]?.[1]}</td>
                  </tr>
                  <tr>
                    <th>Injected anomaly</th>
                    <td>{evaluation.confusion_matrix?.[1]?.[0]}</td>
                    <td>{evaluation.confusion_matrix?.[1]?.[1]}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <p style={{
            ...muted,
            fontSize: 13,
            lineHeight: 1.7,
            marginTop: 18,
          }}>
            Evaluation uses a separate synthetic test set
            with deliberately injected large expenses.
            These metrics do not establish real-world
            detection performance. The model is not
            personalized to an individual student, and
            an anomaly flag is not evidence of fraud.
          </p>
        </section>
      )}
    </div>
  );
}
