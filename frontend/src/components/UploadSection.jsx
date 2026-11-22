

import React, { useState } from "react";
import InfoCard from "./InfoCard";
import "./UploadSection.css";

export default function UploadSection({
  file,
  setFile,
  setResult,
  result,
  isPdf,
  loading,
  analyzing,
  aiAnalyzing,
  consistencyAnalyzing,
  error,
  analysisError,
  aiAnalysisError,
  consistencyError,
  handleUpload,
  handleManipulationAnalysis,
  handleAIContentAnalysis,
  handleConsistencyAnalysis,
  resetAnalyses,
  setError
}) {
    const [activeStage, setActiveStage] = useState("intake");
  const handleFileChange = (e) => {
    setFile(e.target.files?.[0] || null);
    setResult(null);
    setError("");
    resetAnalyses();
  };

  const removeFile = () => {
    setFile(null);
    setResult(null);
    setError("");
    resetAnalyses();
  };

  return (
    <section className="upload-card dribbble-upload" id="upload">

      {/* SECTION INTRODUCTION */}
      <div className="upload-intro">
        <div className="upload-intro-copy">
          <div className="upload-overline">
            <span className="upload-live-dot" />
            DOCUMENT FORENSICS WORKSPACE
          </div>

          <h2>
            Your document.
            <br />
            <span>Under investigation.</span>
          </h2>

          <p>
            Upload a PDF to uncover hidden modifications,
            inspect its structure and examine available
            AI provenance evidence.
          </p>
        </div>

        <div className="upload-index">
          <span>WORKSPACE</span>
          <strong>01</strong>
          <span>PDF EXAMINATION</span>
        </div>
      </div>

      {/* MAIN UPLOAD PANEL */}
      <div className="upload-main-panel">

        <div className="upload-panel-heading">
          <div>
            <span className="upload-step-label">01 / DOCUMENT INTAKE</span>
            <h3>Upload evidence</h3>
            <p>Select the PDF you want to examine.</p>
          </div>

          <div className="upload-format">
            <span className="format-dot" />
            PDF ONLY
          </div>
        </div>

        <div className="upload-workspace">

          {/* LEFT: UPLOAD INTERACTION */}
          <div className="upload-drop-area">
            <input
              id="forensic-pdf-input"
              type="file"
              accept=".pdf,application/pdf"
              onChange={handleFileChange}
            />

            <label
              htmlFor="forensic-pdf-input"
              className="upload-drop-label"
            >
              <div className="upload-artwork">
                <div className="upload-artwork-glow" />

                <div className="upload-pdf-sheet">
                  <div className="upload-pdf-fold" />
                  <span className="upload-pdf-mark">PDF</span>
                  <div className="upload-pdf-line line-long" />
                  <div className="upload-pdf-line" />
                  <div className="upload-pdf-line line-short" />
                  <div className="upload-pdf-mini-box" />
                </div>

                <div className="upload-artwork-symbol">
                  <span>↑</span>
                </div>
              </div>

              <strong>
  {file ? "PDF successfully selected" : "Drop your PDF here"}
</strong>

              <span className="upload-browse-text">
  {file ? (
    <span>Choose a different file</span>
  ) : (
    <>or <span>browse files</span></>
  )}
</span>

              <span className="upload-file-restriction">
                PDF DOCUMENTS · MAXIMUM SIZE 15 MB
              </span>
            </label>
          </div>

          {/* RIGHT: DOCUMENT INFORMATION */}
          <div className="upload-side-panel">
            <div className="upload-side-top">
              <span className="side-panel-label">EXAMINATION PROTOCOL</span>
              <span className="side-panel-number">01 — 04</span>
            </div>

            <button
  type="button"
  className={`protocol-item ${activeStage === "intake" ? "active" : ""}`}
  onClick={() => setActiveStage("intake")}
>
  <div className="protocol-icon">01</div>
  <div>
    <strong>Document intake</strong>
    <span>Secure PDF upload</span>
  </div>
  <span className={`protocol-indicator ${activeStage === "intake" ? "active" : "inactive"}`} />
</button>

<button
  type="button"
  className={`protocol-item ${activeStage === "structural" ? "active" : ""}`}
  onClick={() => setActiveStage("structural")}
>
  <div className="protocol-icon">02</div>
  <div>
    <strong>Structural analysis</strong>
    <span>Inspect possible modifications</span>
  </div>
  <span className={`protocol-indicator ${activeStage === "structural" ? "active" : "inactive"}`} />
</button>

<button
  type="button"
  className={`protocol-item ${activeStage === "provenance" ? "active" : ""}`}
  onClick={() => setActiveStage("provenance")}
>
  <div className="protocol-icon">03</div>
  <div>
    <strong>AI provenance</strong>
    <span>Examine origin evidence</span>
  </div>
  <span className={`protocol-indicator ${activeStage === "provenance" ? "active" : "inactive"}`} />
</button>

<button
  type="button"
  className={`protocol-item ${activeStage === "consistency" ? "active" : ""}`}
  onClick={() => setActiveStage("consistency")}
>
  <div className="protocol-icon">04</div>
  <div>
    <strong>Consistency & Schema</strong>
    <span>Verify domain & schema rules</span>
  </div>
  <span className={`protocol-indicator ${activeStage === "consistency" ? "active" : "inactive"}`} />
</button>

            <div className="upload-security-note">
              <span className="security-symbol">◈</span>
              <span> FORENSIC SCREENING</span>
            </div>
          </div>
        </div>

        {/* SELECTED FILE */}
        {file && (
          <div className="dribbble-selected-file">
            <div className="selected-file-icon">PDF</div>

            <div className="selected-file-info">
              <strong>{file.name}</strong>
              <span>
                {(file.size / 1024 / 1024).toFixed(2)} MB · Selected document
              </span>
            </div>

            <button
              className="selected-file-remove"
              type="button"
              onClick={removeFile}
            >
              Remove
            </button>
          </div>
        )}

        {/* UPLOAD ACTION */}
        <div className="upload-footer">
          <div className="upload-footer-note">
            <span className="footer-check">✓</span>
            <span>PDF format supported</span>
          </div>

          <button
            className="dribbble-upload-button"
            type="button"
            onClick={handleUpload}
            disabled={loading || !file}
          >
            {loading ? "Uploading document..." : "Upload document"}
            <span>↗</span>
          </button>
        </div>

        {error && <p className="message error">{error}</p>}
      </div>

      {/* UPLOAD RESULT */}
      {result && (
        <div className="dribbble-result">

          <div className="dribbble-result-heading">
            <div>
              <span className="upload-step-label">UPLOAD COMPLETE</span>
              <h3>Document received</h3>
            </div>
            <span className="result-ready-badge">
              <span /> SUCCESS
            </span>
          </div>

          <div className="result-grid">
            <InfoCard
              label="File type"
              value={result.type || result.file_type || "PDF"}
            />

            <InfoCard
              label="File size"
              value={`${((result.size_bytes ?? result.size ?? 0) / 1024).toFixed(1)} KB`}
            />

            <InfoCard
              label="Status"
              value={result.status || "Uploaded"}
            />
          </div>

          {isPdf && (
            <div className="dribbble-analysis-grid">

              <div className="dribbble-analysis-card">
                <span className="analysis-card-number">02</span>
                <div className="analysis-card-icon">⌕</div>
                <span className="upload-step-label">
                  FORENSIC MODULE
                </span>
                <h3>Manipulation analysis</h3>
                <p>
                  Examine possible text replacements,
                  structural changes and visual anomalies.
                </p>

                <button
                  className="dribbble-analysis-button"
                  type="button"
                  onClick={() => {
  setActiveStage("structural");
  handleManipulationAnalysis();
}}
                  disabled={analyzing}
                >
                  {analyzing ? "Examining..." : "Start examination"}
                  <span>↗</span>
                </button>

                {analysisError && (
                  <p className="message error">{analysisError}</p>
                )}
              </div>

              <div className="dribbble-analysis-card provenance-card">
                <span className="analysis-card-number">03</span>
                <div className="analysis-card-icon">◈</div>
                <span className="upload-step-label">
                  PROVENANCE MODULE
                </span>
                <h3>AI provenance analysis</h3>
                <p>
                  Examine available origin records,
                  AI platform declarations and signatures.
                </p>

                <button
                  className="dribbble-analysis-button"
                  type="button"
                  onClick={() => {
  setActiveStage("provenance");
  handleAIContentAnalysis();
}}
                  disabled={aiAnalyzing}
                >
                  {aiAnalyzing ? "Examining..." : "Verify provenance"}
                  <span>↗</span>
                </button>

                {aiAnalysisError && (
                  <p className="message error">{aiAnalysisError}</p>
                )}
              </div>

              <div className="dribbble-analysis-card consistency-card">
                <span className="analysis-card-number">04</span>
                <div className="analysis-card-icon">✓</div>
                <span className="upload-step-label">
                  AUTHENTICITY MODULE
                </span>
                <h3>Document consistency</h3>
                <p>
                  Validate extracted fields, schema compliance,
                  and domain logic across all document types.
                </p>

                <button
                  className="dribbble-analysis-button"
                  type="button"
                  onClick={() => {
                    setActiveStage("consistency");
                    handleConsistencyAnalysis();
                  }}
                  disabled={consistencyAnalyzing}
                >
                  {consistencyAnalyzing ? "Verifying..." : "Check consistency"}
                  <span>↗</span>
                </button>

                {consistencyError && (
                  <p className="message error">{consistencyError}</p>
                )}
              </div>

            </div>
          )}
        </div>
      )}
    </section>
  );
}
