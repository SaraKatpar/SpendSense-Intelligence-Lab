
import { useEffect, useState } from "react";
import {
  BrainCircuit,
  RefreshCw,
  Sparkles,
  AlertCircle,
  CheckCircle2,
  FlaskConical,
  Database,
  TrendingUp,
} from "lucide-react";
import {
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Tooltip,
} from "recharts";

const API = "http://127.0.0.1:8000";

const COLORS = {
  Food: "#a98aff",
  Groceries: "#7fdca9",
  Transport: "#4bd9dc",
  Shopping: "#e0b5ff",
  Bills: "#82a4ff",
  Health: "#ff91b6",
  Education: "#ffc879",
  Entertainment: "#ffab77",
};

const card = {
  padding: 24,
  borderRadius: 18,
};

const innerCard = {
  padding: 18,
  borderRadius: 14,
  background: "rgba(169,138,255,0.07)",
  border: "1px solid rgba(169,138,255,0.2)",
};

const muted = {
  color: "#aeb4ce",
};

const rupees = value =>
  `Rs. ${Number(value || 0).toLocaleString("en-PK", {
    maximumFractionDigits: 2,
  })}`;

function Metric({ label, value, subtitle }) {
  return (
    <div style={innerCard}>
      <small style={muted}>{label}</small>
      <h2 style={{ margin: "9px 0", fontSize: 26 }}>
        {value}
      </h2>
      {subtitle && (
        <small style={muted}>{subtitle}</small>
      )}
    </div>
  );
}

function ComparisonBar({ category, actual, average }) {
  const userValue = Number(actual || 0);
  const clusterValue = Number(average || 0);

  return (
    <div style={{ marginBottom: 20 }}>
      <div style={{
        display: "flex",
        justifyContent: "space-between",
        gap: 12,
        marginBottom: 10,
        flexWrap: "wrap",
      }}>
        <strong>{category}</strong>
        <span style={muted}>
          You: {userValue.toFixed(1)}% · Cluster:{" "}
          {clusterValue.toFixed(1)}%
        </span>
      </div>

      <div style={{
        height: 10,
        background: "#30344f",
        borderRadius: 20,
        overflow: "hidden",
        marginBottom: 6,
      }}>
        <div style={{
          width: `${Math.min(100, userValue)}%`,
          height: "100%",
          background: COLORS[category] || "#a98aff",
          borderRadius: 20,
        }} />
      </div>

      <div style={{
        height: 7,
        background: "#30344f",
        borderRadius: 20,
        overflow: "hidden",
      }}>
        <div style={{
          width: `${Math.min(100, clusterValue)}%`,
          height: "100%",
          background: "#858ba7",
          borderRadius: 20,
        }} />
      </div>
    </div>
  );
}

export default function SpendingDNA({
  transactions = [],
  onSelect,
}) {
  const [result, setResult] = useState(null);
  const [evaluation, setEvaluation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  useEffect(() => {
    const controller = new AbortController();

    async function load() {
      setLoading(true);
      setError("");

      try {
        const [profileResponse, evaluationResponse] =
          await Promise.all([
            fetch(`${API}/api/ml/spending-dna`, {
              signal: controller.signal,
            }),
            fetch(`${API}/api/ml/spending-dna/evaluation`, {
              signal: controller.signal,
            }),
          ]);

        if (!profileResponse.ok) {
          const body = await profileResponse
            .json()
            .catch(() => ({}));

          throw new Error(
            typeof body.detail === "string"
              ? body.detail
              : `Spending DNA API error (${profileResponse.status})`
          );
        }

        if (!evaluationResponse.ok) {
          throw new Error(
            "Could not load K-Means evaluation metadata."
          );
        }

        const profile = await profileResponse.json();
        const metadata = await evaluationResponse.json();

        if (!controller.signal.aborted) {
          setResult(profile);
          setEvaluation(metadata);
        }
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(
            err.message || "Could not load Spending DNA."
          );
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

  const categories = result?.category_percentages
    ? Object.entries(result.category_percentages)
        .map(([name, value]) => ({
          name,
          value: Number(value),
        }))
        .filter(item => item.value > 0)
    : [];

  const clusterProfiles = evaluation?.cluster_profiles
    ? Object.entries(evaluation.cluster_profiles)
    : [];

  return (
    <div style={{ display: "grid", gap: 20 }}>
      <section className="panel" style={card}>
        <div style={{
          display: "flex",
          alignItems: "flex-start",
          justifyContent: "space-between",
          gap: 14,
          flexWrap: "wrap",
        }}>
          <div>
            <div className="section-kicker">
              UNSUPERVISED MACHINE LEARNING
            </div>

            <h2 style={{
              display: "flex",
              alignItems: "center",
              gap: 10,
              marginTop: 10,
            }}>
              <BrainCircuit
                color="#a98aff"
                size={26}
              />
              Spending DNA
            </h2>

            <p style={muted}>
              Discover which learned spending pattern
              is closest to your expenses.
            </p>
          </div>

          <button
            type="button"
            onClick={() => setRefreshKey(n => n + 1)}
            disabled={loading}
            className="subtle-button"
            style={{
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
        <section className="panel" style={card}>
          <p style={muted}>
            Analyzing transactions with K-Means...
          </p>
        </section>
      )}

      {error && (
        <section className="panel" style={card}>
          <div style={{
            display: "flex",
            gap: 12,
            alignItems: "center",
            color: "#ff9b9b",
          }}>
            <AlertCircle size={21} />
            <strong>{error}</strong>
          </div>

          <p style={muted}>
            Check that FastAPI is running on port 8000
            and your Spending DNA model files exist.
          </p>
        </section>
      )}

      {!loading &&
        !error &&
        result?.status === "insufficient_data" && (
          <section className="panel" style={card}>
            <div style={{
              ...innerCard,
              textAlign: "center",
              padding: 32,
            }}>
              <BrainCircuit
                size={44}
                color="#a98aff"
              />

              <h2>Your DNA is waiting to be discovered</h2>

              <p style={muted}>{result.message}</p>

              <button
                className="primary-button"
                onClick={() => onSelect?.("Transactions")}
              >
                Add expenses
              </button>
            </div>
          </section>
        )}

      {!loading && !error && result?.status === "ok" && (
        <>
          <section className="panel" style={card}>
            <div className="section-kicker">
              YOUR DISCOVERED SPENDING PROFILE
            </div>

            <div style={{
              ...innerCard,
              marginTop: 18,
              background:
                "linear-gradient(135deg, rgba(169,138,255,0.18), rgba(75,217,220,0.06))",
            }}>
              <div style={{
                display: "flex",
                alignItems: "center",
                gap: 10,
                color: "#c8b6ff",
              }}>
                <Sparkles size={22} />
                <strong>Closest learned cluster</strong>
              </div>

              <h1 style={{
                fontSize: "clamp(30px,5vw,46px)",
                margin: "18px 0 8px",
                color: "#d6c7ff",
              }}>
                {result.profile_name}
              </h1>

              <p style={muted}>
                Your largest supported spending category is{" "}
                <strong>
                  {Object.entries(
                    result.category_percentages
                  ).sort((a, b) => b[1] - a[1])[0]?.[0]}
                </strong>.
                Your closest cluster is characterized by{" "}
                <strong>{result.dominant_category}</strong>.
              </p>

              <div style={{
                display: "flex",
                gap: 8,
                alignItems: "center",
                flexWrap: "wrap",
                fontSize: 12,
                color: "#b8a2ff",
              }}>
                <CheckCircle2 size={16} />
                Calculated using your saved expenses
              </div>
            </div>

            <div style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit,minmax(160px,1fr))",
              gap: 12,
              marginTop: 18,
            }}>
              <Metric
                label="Analyzed expenses"
                value={result.valid_transactions}
              />

              <Metric
                label="Supported spending"
                value={rupees(result.total_spending)}
              />

              <Metric
                label="Assigned cluster"
                value={`#${result.cluster_id}`}
              />

              <Metric
                label="Distance to centroid"
                value={Number(
                  result.distance_to_centroid
                ).toFixed(2)}
                subtitle="Not a confidence percentage"
              />
            </div>

            {result.excluded_transactions > 0 && (
              <p style={{
                ...muted,
                marginTop: 18,
                fontSize: 13,
              }}>
                {result.excluded_transactions} expense
                transaction(s) excluded because their
                categories or amounts are unsupported.
                Excluded amount:{" "}
                {rupees(result.excluded_amount)}.
              </p>
            )}
          </section>

          <section className="panel" style={card}>
            <div className="section-kicker">
              YOUR CATEGORY DISTRIBUTION
            </div>
            <h2>Where your money goes</h2>

            <div style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit,minmax(260px,1fr))",
              gap: 20,
              alignItems: "center",
              marginTop: 20,
            }}>
              <div style={{ height: 280 }}>
                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >
                  <PieChart>
                    <Pie
                      data={categories}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={75}
                      outerRadius={110}
                      paddingAngle={3}
                      stroke="none"
                    >
                      {categories.map(item => (
                        <Cell
                          key={item.name}
                          fill={
                            COLORS[item.name] ||
                            "#a98aff"
                          }
                        />
                      ))}
                    </Pie>
                    <Tooltip
                      formatter={value =>
                        `${Number(value).toFixed(2)}%`
                      }
                      contentStyle={{
                        background: "#19223c",
                        border: "1px solid #39415e",
                        borderRadius: 12,
                        color: "#fff",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>

              <div style={{
                display: "grid",
                gap: 12,
              }}>
                {categories
                  .sort((a, b) => b.value - a.value)
                  .map(item => (
                    <div
                      key={item.name}
                      style={{
                        display: "flex",
                        justifyContent: "space-between",
                        gap: 14,
                      }}
                    >
                      <span style={{
                        display: "flex",
                        alignItems: "center",
                        gap: 9,
                      }}>
                        <span style={{
                          width: 10,
                          height: 10,
                          borderRadius: "50%",
                          background:
                            COLORS[item.name] ||
                            "#a98aff",
                        }} />
                        {item.name}
                      </span>

                      <strong>
                        {item.value.toFixed(2)}%
                      </strong>
                    </div>
                  ))}
              </div>
            </div>
          </section>

          <section className="panel" style={card}>
            <div className="section-kicker">
              BEHAVIOR COMPARISON
            </div>

            <h2>You vs. your cluster</h2>

            <p style={muted}>
              Colored bars represent your spending.
              Gray bars represent the average profile
              of your assigned synthetic-data cluster.
            </p>

            <div style={{ marginTop: 24 }}>
              {Object.entries(
                result.category_percentages
              ).map(([category, value]) => (
                <ComparisonBar
                  key={category}
                  category={category}
                  actual={value}
                  average={
                    result.cluster_average_percentages?.[
                      category
                    ]
                  }
                />
              ))}
            </div>
          </section>
        </>
      )}

      {!loading && !error && evaluation && (
        <>
          <section className="panel" style={card}>
            <div className="section-kicker">
              MODEL TRANSPARENCY
            </div>

            <h2>
              <FlaskConical
                size={21}
                style={{
                  display: "inline",
                  verticalAlign: "middle",
                  marginRight: 8,
                  color: "#a98aff",
                }}
              />
              Inside the K-Means model
            </h2>

            <div style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit,minmax(160px,1fr))",
              gap: 12,
              marginTop: 20,
            }}>
              <Metric
                label="Algorithm"
                value="K-Means"
              />

              <Metric
                label="Discovered clusters"
                value={evaluation.selected_k}
              />

              <Metric
                label="Silhouette score"
                value={Number(
                  evaluation.silhouette_score
                ).toFixed(4)}
              />

              <Metric
                label="Training profiles"
                value={evaluation.students}
                subtitle="Synthetic students"
              />
            </div>

            <p style={{
              ...muted,
              marginTop: 18,
              fontSize: 13,
            }}>
              <Database
                size={15}
                style={{
                  display: "inline",
                  verticalAlign: "middle",
                  marginRight: 6,
                }}
              />
              Trained on synthetic spending profiles.
              The silhouette score describes training
              cluster separation, not prediction accuracy.
            </p>
          </section>

          <section className="panel" style={card}>
            <div className="section-kicker">
              DISCOVERED GROUPS
            </div>

            <h2>Explore all spending clusters</h2>

            <p style={muted}>
              These names describe cluster averages.
              They are not predetermined K-Means labels.
            </p>

            <div style={{
              display: "grid",
              gridTemplateColumns:
                "repeat(auto-fit,minmax(230px,1fr))",
              gap: 14,
              marginTop: 20,
            }}>
              {clusterProfiles.map(([id, profile]) => {
                const selected =
                  result?.status === "ok" &&
                  String(result.cluster_id) === id;

                return (
                  <div
                    key={id}
                    style={{
                      ...innerCard,
                      border: selected
                        ? "1px solid #a98aff"
                        : innerCard.border,
                    }}
                  >
                    <div style={{
                      display: "flex",
                      justifyContent: "space-between",
                      gap: 10,
                    }}>
                      <small style={muted}>
                        Cluster {id}
                      </small>
                      {selected && (
                        <CheckCircle2
                          size={17}
                          color="#a98aff"
                        />
                      )}
                    </div>

                    <h3 style={{
                      margin: "12px 0",
                      color: "#d6c7ff",
                    }}>
                      {profile.name}
                    </h3>

                    <p style={muted}>
                      Dominant category:{" "}
                      <strong>
                        {profile.dominant_category}
                      </strong>
                    </p>

                    <p style={muted}>
                      Synthetic students:{" "}
                      {profile.student_count}
                    </p>

                    <p style={muted}>
                      Average simulated expenses:{" "}
                      {rupees(
                        profile.average_monthly_expenses
                      )}
                    </p>
                  </div>
                );
              })}
            </div>
          </section>

          <section className="panel" style={card}>
            <div style={{
              display: "flex",
              alignItems: "center",
              gap: 9,
              color: "#c8b6ff",
            }}>
              <TrendingUp size={18} />
              <strong>How to interpret this result</strong>
            </div>

            <p style={{
              ...muted,
              lineHeight: 1.7,
              marginBottom: 0,
            }}>
              Spending DNA finds the nearest cluster
              using category spending proportions.
              It does not diagnose financial health,
              predict future spending, or determine
              whether a purchase is affordable.
              Results may change as you add expenses.
              The model was trained on synthetic data,
              so real-world validity is not established.
            </p>
          </section>
        </>
      )}
    </div>
  );
}
