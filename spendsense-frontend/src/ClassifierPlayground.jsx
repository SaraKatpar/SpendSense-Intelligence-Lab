
import { useState } from "react";
import {
  BrainCircuit,
  Sparkles,
  Loader2,
  AlertCircle,
  CheckCircle2,
  RotateCcw,
  ChevronDown,
  ChevronUp
} from "lucide-react";

const API = "http://127.0.0.1:8000";

const EXAMPLES = [
  "Bought biryani for lunch at university",
  "Paid 500 rupees for a rickshaw ride",
  "Bought medicine from the pharmacy",
  "Paid my university semester fee",
  "Bought groceries for the hostel"
];

const COLORS = {
  Food: "#a98aff",
  Transport: "#4bd9dc",
  Health: "#ff91b6",
  Education: "#ffc879",
  Groceries: "#7fdca9",
  Bills: "#82a4ff",
  Shopping: "#e0b5ff",
  Entertainment: "#ffab77"
};

const panelStyle = {
  padding: 24,
  borderRadius: 18,
  background: "rgba(169,138,255,0.045)",
  border: "1px solid rgba(169,138,255,0.18)"
};

export default function ClassifierPlayground() {
  const [description, setDescription] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [showEmbedding, setShowEmbedding] = useState(false);

  const predict = async () => {
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
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            description: text
          })
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
  };

  const reset = () => {
    setDescription("");
    setResult(null);
    setError("");
    setShowEmbedding(false);
  };

  const probabilities = result
    ? Object.entries(result.probabilities).sort(
        (a, b) => b[1] - a[1]
      )
    : [];

  const formatPercent = value =>
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
          <h2 style={{ marginBottom: 6 }}>
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
            Test your expense classification model with
            descriptions it has never seen before.
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
          {EXAMPLES.map((example, index) => (
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
            <Loader2 size={19} />
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
          <div style={panelStyle}>
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
              color: COLORS[result.predicted_category] ||
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
                {formatPercent(result.confidence)}
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
              This is the model's estimated probability,
              not a guarantee that the prediction is correct.
            </p>
          </div>

          <div style={panelStyle}>
            <h3 style={{ marginTop: 0 }}>
              Category Probabilities
            </h3>

            <p className="muted">
              How the classifier distributes its predictions
              across the eight expense categories.
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
                      {formatPercent(probability)}
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
                      background: COLORS[category] || "#a98aff",
                      transition: "width 0.35s ease"
                    }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div style={panelStyle}>
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
                [
                  "3. Classifier",
                  result.model.classifier
                ],
                [
                  "4. Predicted Category",
                  result.predicted_category
                ]
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
