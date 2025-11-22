import { useState } from "react";

interface Hypothesis {
  id: string;
  cause: string;
  effect: string;
  mechanism: string;
  validated: boolean;
  confidence?: number;
  p_value?: number;
  effect_size?: number;
  causal_structure?: {
    direct_effect: number;
    indirect_effect: number;
    total_effect: number;
    mediators: string[];
    actionable_lever: string;
  };
}

interface HypothesisExplorerProps {
  hypotheses: Hypothesis[];
  onHypothesisSelect?: (hypothesis: Hypothesis) => void;
}

export function HypothesisExplorer({ hypotheses, onHypothesisSelect }: HypothesisExplorerProps) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [filter, setFilter] = useState<"all" | "validated" | "rejected">("all");

  const filteredHypotheses = hypotheses.filter((h) => {
    if (filter === "validated") return h.validated;
    if (filter === "rejected") return !h.validated;
    return true;
  });

  const handleSelect = (hypothesis: Hypothesis) => {
    setSelectedId(hypothesis.id);
    if (onHypothesisSelect) {
      onHypothesisSelect(hypothesis);
    }
  };

  const selectedHypothesis = hypotheses.find((h) => h.id === selectedId);

  return (
    <div style={{ display: "flex", gap: "16px", height: "100%" }}>
      {/* Hypothesis List */}
      <div style={{ flex: "0 0 300px", borderRight: "1px solid #e2e8f0", paddingRight: "16px" }}>
        <div style={{ marginBottom: "12px" }}>
          <label style={{ fontSize: "12px", fontWeight: 600, color: "#64748b", display: "block", marginBottom: "4px" }}>
            Filter
          </label>
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as any)}
            style={{
              width: "100%",
              padding: "8px",
              border: "1px solid #e2e8f0",
              borderRadius: "4px",
              fontSize: "14px",
            }}
          >
            <option value="all">All ({hypotheses.length})</option>
            <option value="validated">Validated ({hypotheses.filter((h) => h.validated).length})</option>
            <option value="rejected">Rejected ({hypotheses.filter((h) => !h.validated).length})</option>
          </select>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {filteredHypotheses.map((hypothesis) => (
            <div
              key={hypothesis.id}
              onClick={() => handleSelect(hypothesis)}
              style={{
                padding: "12px",
                border: `2px solid ${selectedId === hypothesis.id ? "#3b82f6" : "#e2e8f0"}`,
                borderRadius: "8px",
                cursor: "pointer",
                backgroundColor: selectedId === hypothesis.id ? "#eff6ff" : "white",
                transition: "all 0.2s",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                <span
                  style={{
                    display: "inline-block",
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    backgroundColor: hypothesis.validated ? "#10b981" : "#ef4444",
                  }}
                />
                <span style={{ fontSize: "14px", fontWeight: 600 }}>
                  {hypothesis.cause} → {hypothesis.effect}
                </span>
              </div>
              <div style={{ fontSize: "12px", color: "#64748b" }}>
                {hypothesis.validated ? "✓ Validated" : "✗ Not validated"}
                {hypothesis.confidence && (
                  <span style={{ marginLeft: "8px" }}>
                    ({(hypothesis.confidence * 100).toFixed(0)}% confidence)
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Hypothesis Details */}
      <div style={{ flex: 1, padding: "0 16px" }}>
        {selectedHypothesis ? (
          <div>
            <h3 style={{ fontSize: "18px", fontWeight: 600, marginBottom: "16px" }}>
              {selectedHypothesis.cause} → {selectedHypothesis.effect}
            </h3>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "24px" }}>
              <div style={{ padding: "12px", backgroundColor: "#f8fafc", borderRadius: "8px" }}>
                <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>Status</div>
                <div style={{ fontSize: "16px", fontWeight: 600, color: selectedHypothesis.validated ? "#10b981" : "#ef4444" }}>
                  {selectedHypothesis.validated ? "Validated ✓" : "Rejected ✗"}
                </div>
              </div>

              {selectedHypothesis.p_value !== undefined && (
                <div style={{ padding: "12px", backgroundColor: "#f8fafc", borderRadius: "8px" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>P-value</div>
                  <div style={{ fontSize: "16px", fontWeight: 600 }}>{selectedHypothesis.p_value.toFixed(4)}</div>
                </div>
              )}

              {selectedHypothesis.effect_size !== undefined && (
                <div style={{ padding: "12px", backgroundColor: "#f8fafc", borderRadius: "8px" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>Effect Size</div>
                  <div style={{ fontSize: "16px", fontWeight: 600 }}>{selectedHypothesis.effect_size.toFixed(3)}</div>
                </div>
              )}

              {selectedHypothesis.confidence !== undefined && (
                <div style={{ padding: "12px", backgroundColor: "#f8fafc", borderRadius: "8px" }}>
                  <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "4px" }}>Confidence</div>
                  <div style={{ fontSize: "16px", fontWeight: 600 }}>{(selectedHypothesis.confidence * 100).toFixed(0)}%</div>
                </div>
              )}
            </div>

            <div style={{ marginBottom: "24px" }}>
              <h4 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "8px" }}>Mechanism</h4>
              <p style={{ fontSize: "14px", color: "#475569", lineHeight: 1.6 }}>{selectedHypothesis.mechanism}</p>
            </div>

            {selectedHypothesis.causal_structure && (
              <div style={{ marginBottom: "24px" }}>
                <h4 style={{ fontSize: "14px", fontWeight: 600, marginBottom: "12px" }}>Causal Structure</h4>

                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px", marginBottom: "12px" }}>
                  <div style={{ padding: "12px", backgroundColor: "#f1f5f9", borderRadius: "6px" }}>
                    <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>Direct Effect</div>
                    <div style={{ fontSize: "18px", fontWeight: 600, color: "#3b82f6" }}>
                      {selectedHypothesis.causal_structure.direct_effect.toFixed(3)}
                    </div>
                  </div>

                  <div style={{ padding: "12px", backgroundColor: "#f1f5f9", borderRadius: "6px" }}>
                    <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>Indirect Effect</div>
                    <div style={{ fontSize: "18px", fontWeight: 600, color: "#94a3b8" }}>
                      {selectedHypothesis.causal_structure.indirect_effect.toFixed(3)}
                    </div>
                  </div>

                  <div style={{ padding: "12px", backgroundColor: "#f1f5f9", borderRadius: "6px" }}>
                    <div style={{ fontSize: "11px", color: "#64748b", marginBottom: "4px" }}>Total Effect</div>
                    <div style={{ fontSize: "18px", fontWeight: 600, color: "#10b981" }}>
                      {selectedHypothesis.causal_structure.total_effect.toFixed(3)}
                    </div>
                  </div>
                </div>

                {selectedHypothesis.causal_structure.mediators.length > 0 && (
                  <div style={{ marginTop: "12px" }}>
                    <div style={{ fontSize: "12px", color: "#64748b", marginBottom: "6px" }}>Mediators:</div>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                      {selectedHypothesis.causal_structure.mediators.map((mediator) => (
                        <span
                          key={mediator}
                          style={{
                            padding: "4px 8px",
                            backgroundColor: "#dbeafe",
                            color: "#1e40af",
                            borderRadius: "4px",
                            fontSize: "12px",
                          }}
                        >
                          {mediator}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {selectedHypothesis.causal_structure.actionable_lever && (
                  <div
                    style={{
                      marginTop: "16px",
                      padding: "12px",
                      backgroundColor: "#d1fae5",
                      border: "1px solid #10b981",
                      borderRadius: "8px",
                    }}
                  >
                    <div style={{ fontSize: "12px", fontWeight: 600, color: "#065f46", marginBottom: "4px" }}>
                      🎯 Actionable Lever
                    </div>
                    <div style={{ fontSize: "14px", color: "#047857" }}>
                      {selectedHypothesis.causal_structure.actionable_lever}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        ) : (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              height: "100%",
              color: "#94a3b8",
              fontSize: "14px",
            }}
          >
            Select a hypothesis to view details
          </div>
        )}
      </div>
    </div>
  );
}
