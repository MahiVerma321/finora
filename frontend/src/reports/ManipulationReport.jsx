
import React from "react";
import "./ManipulationReport.css";
import Status from "../components/Status";
import InfoCard from "../components/InfoCard";
import ReportFinding from "./ReportFinding";
import TechnicalDetails from "../components/TechnicalDetails";
import { formatLabel, severityType } from "../utils/reportHelpers";

const API_URL = "http://127.0.0.1:8000";

export default function ManipulationReport({ analysis }) {
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
          "The examination did not identify significant indicators of PDF manipulation in the checks performed. This does not guarantee that the document is authentic."
      };
    }

    if (assessment === "review_recommended") {
      return {
        title: "Further review recommended",
        type: "review",
        explanation:
          "The examination identified characteristics that need closer inspection. Review the findings below before drawing a conclusion."
      };
    }

    return {
      title: "Assessment unavailable",
      type: "info",
      explanation:
        summary.interpretation ||
        "An overall assessment could not be generated."
    };
  }

  const report = getManipulationResult();

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

      <div className="findings-card">
        <h3>What did we find?</h3>

        {summary.findings?.length > 0 ? (
          summary.findings.map((finding, index) => (
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
            />
          ))
        ) : (
          <p className="subtext">
            No findings were reported by the examination modules.
          </p>
        )}
      </div>

      {checks.content_stream_analysis?.findings?.length > 0 && (
        <div className="findings-card">
          <h3>Possible text modifications</h3>
          <p className="subtext small">
            The examination identified differences in PDF text
            content that may need manual review.
          </p>

          {checks.content_stream_analysis.findings.map(
            (finding, index) => (
              <ReportFinding
                key={index}
                title={`Possible modification ${index + 1}`}
                status="Review needed"
                type="review"
                description={`Page ${finding.page}. ${
                  finding.finding ||
                  "A text modification indicator was identified."
                }`}
              />
            )
          )}

          <TechnicalDetails
            title="View detailed text modification evidence"
            data={checks.content_stream_analysis.findings}
          />
        </div>
      )}

      {analysis.visual_evidence?.visualization_url && (
        <div className="findings-card">
          <h3>Highlighted document</h3>
          <p className="subtext small">
            The following document highlights regions selected
            by the forensic examination for closer inspection.
            Highlighting does not prove manipulation.
          </p>

          <iframe
            src={`${API_URL}${analysis.visual_evidence.visualization_url}`}
            title="Highlighted forensic PDF"
            width="100%"
            height="600"
            style={{
              border: "1px solid #ddd",
              borderRadius: "10px",
              marginTop: "16px",
              background: "#fff"
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
              marginTop: "16px"
            }}
          >
            Open highlighted PDF
          </a>
        </div>
      )}

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
            revision_chain: checks.revision_chain
          }}
        />

        <TechnicalDetails
          title="Error Level Analysis measurements"
          data={checks.ela || {}}
        />

        {checks.ela?.pages?.length > 0 && (
          <details>
            <summary>View ELA images</summary>

            {checks.ela.pages.map((page) => (
              <div className="ela-page" key={page.page_number}>
                <h4>Page {page.page_number}</h4>

                {page.visualization_url && (
                  <img
                    className="ela-image"
                    src={`${API_URL}${page.visualization_url}`}
                    alt={`ELA page ${page.page_number}`}
                  />
                )}

                <p className="subtext small">
                  {page.interpretation}
                </p>
              </div>
            ))}
          </details>
        )}
      </div>

      <p className="disclaimer">
        Automated screening identifies technical indicators
        for further examination. It cannot independently
        establish whether a document is genuine or forged.
      </p>
    </section>
  );
}
