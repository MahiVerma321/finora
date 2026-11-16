
import React, { useState } from "react";
import "./ManipulationReport.css";
import Status from "../components/Status";
import InfoCard from "../components/InfoCard";
import ReportFinding from "./ReportFinding";
import TechnicalDetails from "../components/TechnicalDetails";
import { formatLabel, severityType } from "../utils/reportHelpers";

const API_URL =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

// Map finding category to evidence category
function evidenceCategory(category) {
  if (!category) return "other";
  const c = category.toLowerCase();
  if (
    c.includes("content_stream") ||
    c.includes("revision") ||
    c.includes("pdf_structure") ||
    c.includes("generation")
  )
    return "structural";
  if (
    c.includes("ela") ||
    c.includes("visual") ||
    c.includes("font") ||
    c.includes("color") ||
    c.includes("overlap")
  )
    return "visual";
  if (
    c.includes("metadata") ||
    c.includes("timestamp") ||
    c.includes("producer") ||
    c.includes("author") ||
    c.includes("provenance")
  )
    return "metadata";
  return "other";
}

const CATEGORY_LABELS = {
  structural: "Structural Evidence",
  visual: "Visual Heuristics",
  metadata: "Metadata Observations",
  other: "Other Findings",
};

const CATEGORY_NOTES = {
  structural:
    "Structural findings come from PDF content stream analysis and revision markers. These are direct technical observations inside the file format.",
  visual:
    "Visual heuristics are based on image analysis and layout inspection. These are indicators, not proof of manipulation.",
  metadata:
    "Metadata observations flag unusual or missing document properties. Metadata is easy to alter and should not be treated as conclusive evidence alone.",
};

// Severity indicator text for visual_regions anomaly types
function anomalySeverityType(type) {
  if (!type) return "info";
  const t = type.toLowerCase();
  if (t.includes("color") || t.includes("overlap")) return "warning";
  if (t.includes("font")) return "review";
  return "info";
}

function anomalySeverityLabel(type) {
  if (!type) return "Indicator";
  const t = type.toLowerCase();
  if (t.includes("color") || t.includes("overlap")) return "Higher concern";
  if (t.includes("font")) return "Low concern";
  return "Indicator";
}

export default function ManipulationReport({ analysis }) {
  const [selectedPage, setSelectedPage] = useState(1);
  if (!analysis) return null;

  const summary = analysis.summary || {};
  const checks = analysis.checks || {};

  function getManipulationResult() {
    const assessment = summary.overall_assessment;

    if (assessment === "no_significant_indicators_detected") {
      return {
        title: "No significant concerns detected",
        type: "success",
        explanation:
          "The examination did not identify significant indicators of PDF manipulation in the checks performed. This does not guarantee that the document is authentic.",
      };
    }

    if (assessment === "review_recommended") {
      return {
        title: "Further review recommended",
        type: "review",
        explanation:
          "The examination identified characteristics that need closer inspection. Review the findings below before drawing a conclusion.",
      };
    }

    return {
      title: "Assessment unavailable",
      type: "info",
      explanation:
        summary.interpretation ||
        "An overall assessment could not be generated.",
    };
  }

  const report = getManipulationResult();

  // Determine if any checks failed / returned null
  const checkKeys = Object.keys(checks);
  const hasFailedChecks = analysis.status === "completed_with_errors" || analysis.errors?.length > 0 || checkKeys.some(
    (k) => checks[k] === null || checks[k] === undefined
  );

  // Group findings by evidence category
  const findings = summary.findings || [];
  const findingsByCategory = {};
  findings.forEach((finding) => {
    const cat = evidenceCategory(finding.category);
    if (!findingsByCategory[cat]) findingsByCategory[cat] = [];
    findingsByCategory[cat].push(finding);
  });

  // Visual regions data
  const visualRegionsPages = checks.visual_regions?.pages || [];
  const pagesWithAnomalies = visualRegionsPages.filter(
    (p) => p.anomalies && p.anomalies.length > 0
  );

  // ELA pages
  const elaPages = checks.ela?.pages || [];

  return (
    <section className="analysis-section">
      <div className="card-heading">
        <div>
          <p className="eyebrow">STEP 04</p>
          <h3>PDF examination report</h3>
        </div>
        <span className="file-limit">
          {analysis.status || "Completed"}
        </span>
      </div>

      <div className="summary-card">
        <p className="eyebrow">OVERALL RESULT</p>

        <div className="finding-heading">
          <h3>{report.title}</h3>
          <Status type={report.type}>
            {report.type === "success"
              ? "No major indicators"
              : report.type === "review"
                ? "Review needed"
                : "Information"}
          </Status>
        </div>

        <p className="subtext small">{report.explanation}</p>

        {findings.length === 0 && (
          <p className="subtext small no-findings-note">
            No anomalies detected in this document. This does not confirm
            authenticity — some alterations cannot be detected without an
            original reference document.
          </p>
        )}

        {hasFailedChecks && (
          <p className="subtext small check-incomplete-note">
            ⚠ Some checks could not complete.
          </p>
        )}

        <div className="result-grid">
          <InfoCard
            label="Findings reported"
            value={
              summary.finding_count ??
              summary.findings?.length ??
              0
            }
          />
          <InfoCard
            label="Examination status"
            value={analysis.status || "Completed"}
          />
        </div>
      </div>

      {/* ── FINDINGS — grouped by evidence category ── */}
      <div className="findings-card">
        <h3>What did we find?</h3>

        {findings.length > 0 ? (
          ["structural", "visual", "metadata", "other"].map((cat) => {
            const group = findingsByCategory[cat];
            if (!group || group.length === 0) return null;
            return (
              <div key={cat} className="finding-category-group">
                <div className="category-header">
                  <span className="category-label">
                    {CATEGORY_LABELS[cat]}
                  </span>
                  {CATEGORY_NOTES[cat] && (
                    <span className="category-note">
                      {CATEGORY_NOTES[cat]}
                    </span>
                  )}
                </div>
                {group.map((finding, index) => (
                  <ReportFinding
                    key={index}
                    title={formatLabel(finding.category || "Finding")}
                    status={
                      finding.severity === "warning" ||
                      finding.severity === "high"
                        ? "Attention"
                        : finding.severity === "review"
                          ? "Review"
                          : "Information"
                    }
                    type={severityType(finding.severity)}
                    description={finding.message}
                    severity={finding.severity}
                  />
                ))}
              </div>
            );
          })
        ) : (
          <p className="subtext">
            No findings were reported by the examination modules.
          </p>
        )}
      </div>

      {/* ── CONTENT STREAM TEXT MODIFICATIONS ── */}
      {checks.content_stream_analysis?.findings?.length > 0 && (
        <div className="findings-card">
          <h3>Possible text modifications</h3>
          <p className="subtext small">
            The examination identified differences in PDF text
            content that may need manual review.
          </p>

          {checks.content_stream_analysis.findings.map(
            (finding, index) => (
              <div key={index}>
              <ReportFinding
                title={`Editing indicator ${index + 1}`}
                status="Review needed"
                type="review"
                description={`Page ${finding.page}. ${
                  finding.interpretation || finding.finding ||
                  "A text modification indicator was identified."
                }`}
                severity="review"
              />
              {finding.text_bbox && analysis.visual_evidence?.visualization_url && <a href="#visual-evidence" onClick={() => setSelectedPage(finding.page)}>View red rectangle on page {finding.page}</a>}
              {finding.original_text && <p>Earlier embedded text — {finding.original_text}</p>}
              {finding.replacement_text && <p>Text in this region — {finding.replacement_text}</p>}
              {finding.location_source === "earlier_revision" && <p>The outline marks the removed text's earlier location.</p>}
              </div>
            )
          )}

          <TechnicalDetails
            title="View detailed text modification evidence"
            data={checks.content_stream_analysis.findings}
          />
        </div>
      )}

      {/* ── VISUAL EVIDENCE (highlighted PDF) ── */}
      <div className="findings-card">
        <h3 id="visual-evidence">Visual Evidence</h3>
        <p className="subtext small">
          Red boxes mark retained editing evidence, including text covered by later shapes, matching empty text blocks, editing annotations, and differences in embedded revisions.
          Amber dashed boxes mark visual layout anomalies (e.g. text overlaps,
          font deviations, or positioning anomalies).
        </p>

        {analysis.visual_evidence?.visualization_url ? (
          <>
            <iframe
              key={selectedPage}
              src={`${API_URL}${analysis.visual_evidence.visualization_url}#page=${selectedPage}`}
              title="Highlighted forensic PDF"
              width="100%"
              height="600"
              style={{
                border: "1px solid #ddd",
                borderRadius: "10px",
                marginTop: "16px",
                background: "#fff",
              }}
            />

            <a
              href={`${API_URL}${analysis.visual_evidence.visualization_url}`}
              target="_blank"
              rel="noreferrer"
              className="primary-button"
              style={{
                display: "inline-block",
                textDecoration: "none",
                textAlign: "center",
                marginTop: "16px",
              }}
            >
              Open highlighted PDF
            </a>
          </>
        ) : (
          <p className="subtext small empty-state-note">
            {analysis.visual_evidence?.status === "unavailable" ? "Evidence rendering could not complete. Review the available findings and analysis errors." : "No supported editing regions could be located for an outline. Review the available screening results."}
          </p>
        )}
      </div>

      {/* ── ELA IMAGES ── */}
      {elaPages.length > 0 && (
        <div className="findings-card">
          <h3>Error Level Analysis</h3>
          <p className="subtext small">
            These images show differences after JPEG recompression of rendered pages. Bright areas also arise from ordinary text and edges. They cannot identify prior edits by themselves.
          </p>

          <div className="ela-gallery">
            {elaPages.map((page) => (
              <div className="ela-page" key={page.page_number}>
                <h4>Page {page.page_number} — Error Level Analysis</h4>

                {page.visualization_url && (
                  <img
                    className="ela-image"
                    src={`${API_URL}${page.visualization_url}`}
                    alt={`ELA page ${page.page_number}`}
                  />
                )}

                <p className="subtext small">{page.interpretation}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── LAYOUT ANOMALIES (visual_regions) ── */}
      {pagesWithAnomalies.length > 0 && (
        <div className="findings-card">
          <h3>Layout Anomalies</h3>
          <p className="subtext small">
            These are layout indicators only. Font and spacing
            variations occur in legitimate documents and do not
            indicate manipulation.
          </p>

          {pagesWithAnomalies.map((page) => (
            <div key={page.page_number} className="layout-anomaly-page">
              <p className="layout-page-label">
                Page {page.page_number}
              </p>
              {page.anomalies.map((anomaly, idx) => (
                <div key={idx} className="finding">
                  <div className="finding-heading">
                    <strong>
                      {formatLabel(anomaly.type || "Anomaly")}
                    </strong>
                    <Status type={anomalySeverityType(anomaly.type)}>
                      {anomalySeverityLabel(anomaly.type)}
                    </Status>
                  </div>
                  {anomaly.text && (
                    <p className="anomaly-excerpt">
                      <span className="anomaly-excerpt-label">Text: </span>
                      &ldquo;
                      {anomaly.text.length > 120
                        ? anomaly.text.slice(0, 120) + "…"
                        : anomaly.text}
                      &rdquo;
                    </p>
                  )}
                  {anomaly.reasons && anomaly.reasons.length > 0 && (
                    <p className="anomaly-reasons">
                      {anomaly.reasons.join(" · ")}
                    </p>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {/* ── TECHNICAL DETAILS ── */}
      <div className="findings-card">
        <h3>Technical details</h3>
        <p className="subtext small">
          Optional information for technical reviewers and investigators.
        </p>

        <TechnicalDetails
          title="PDF metadata"
          data={checks.metadata?.metadata || {}}
        />

        <TechnicalDetails
          title="PDF structure"
          data={checks.pdf_structure || {}}
        />

        <TechnicalDetails
          title="Visual region analysis"
          data={checks.visual_regions || {}}
        />

        <TechnicalDetails
          title="Content-stream examination"
          data={checks.content_stream_analysis || {}}
        />

        <TechnicalDetails
          title="Revision history"
          data={{
            revision_markers: checks.revision_markers,
            revision_chain: checks.revision_chain,
          }}
        />

        <TechnicalDetails
          title="Error Level Analysis measurements"
          data={checks.ela || {}}
        />
      </div>

      <p className="disclaimer">
        Automated screening identifies technical indicators
        for further examination. It cannot independently
        establish whether a document is genuine or forged.
      </p>
    </section>
  );
}
