import React from "react";
import Status from "../components/Status";
import InfoCard from "../components/InfoCard";
import ReportFinding from "./ReportFinding";
import TechnicalDetails from "../components/TechnicalDetails";
import { formatLabel } from "../utils/reportHelpers";

export default function ConsistencyReport({ consistencyData }) {
  if (!consistencyData) return null;

  const report = consistencyData.consistency_report || {};
  const fieldValidation = consistencyData.field_validation_report || {};
  const extractedDoc =
    consistencyData.extracted_document ||
    consistencyData.extracted_ticket ||
    {};
  const fields = extractedDoc.fields || {};

  const docType =
    consistencyData.document_label ||
    formatLabel(consistencyData.document_type || "Document");
  const issuer = consistencyData.issuer || "Unspecified";
  const overallStatus = consistencyData.overall_status || report.status || "completed";

  function getStatusType(status) {
    if (status === "passed") return "success";
    if (status === "review_required" || status === "failed") return "warning";
    if (status === "incomplete") return "review";
    return "info";
  }

  function getStatusLabel(status) {
    if (status === "passed") return "Passed";
    if (status === "review_required" || status === "failed") return "Review Needed";
    if (status === "incomplete") return "Incomplete";
    return formatLabel(status || "Completed");
  }

  const checks = report.checks || [];
  const fieldChecks = fieldValidation.checks || [];

  return (
    <section className="analysis-section" id="consistency-report">
      {/* CARD HEADING */}
      <div className="card-heading">
        <div>
          <p className="eyebrow">AUTHENTICITY & SCHEMA PROTOCOL</p>
          <h3>Document consistency examination</h3>
          <p className="subtext small">
            Evaluation of structural fields, chronological validity, and domain rules.
          </p>
        </div>
        <span className="file-limit">
          {consistencyData.document_category
            ? `${consistencyData.document_category.toUpperCase()} · `
            : ""}
          {docType.toUpperCase()}
        </span>
      </div>

      {/* OVERALL RESULT */}
      <div className="summary-card">
        <p className="eyebrow">CONSISTENCY STATUS</p>

        <div className="finding-heading">
          <h3>
            {overallStatus === "passed"
              ? "All consistency checks verified"
              : overallStatus === "review_required"
              ? "Consistency discrepancies detected"
              : "Consistency examination incomplete"}
          </h3>
          <Status type={getStatusType(overallStatus)}>
            {getStatusLabel(overallStatus)}
          </Status>
        </div>

        <p className="subtext small">
          {overallStatus === "passed"
            ? `Extracted data matches the expected structural schema for ${docType}. No internal contradictions detected.`
            : overallStatus === "review_required"
            ? "Discrepancies or conflicting values were identified during rule evaluation. Manual inspection is recommended."
            : "Some fields could not be verified or were absent in the extracted document."}
        </p>

        <div className="result-grid">
          <InfoCard label="Document type" value={docType} />
          <InfoCard label="Identified issuer" value={issuer} />
          <InfoCard
            label="Total checks"
            value={report.summary?.total_checks ?? checks.length}
          />
          <InfoCard
            label="Passed checks"
            value={report.summary?.passed ?? 0}
          />
        </div>
      </div>

      {/* EXTRACTED FIELDS CARD */}
      {Object.keys(fields).length > 0 && (
        <div className="findings-card">
          <h3>Extracted document fields</h3>
          <p className="subtext small">
            Structured entities identified by the OCR and schema extractors.
          </p>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
              gap: "12px",
              marginTop: "16px",
            }}
          >
            {Object.entries(fields).map(([fieldName, fieldData]) => {
              const val =
                typeof fieldData === "object" && fieldData !== null
                  ? fieldData.value
                  : fieldData;
              const conf =
                typeof fieldData === "object" && fieldData !== null
                  ? fieldData.confidence
                  : null;

              if (!val) return null;

              return (
                <div
                  key={fieldName}
                  style={{
                    padding: "12px 14px",
                    background: "rgba(22, 38, 58, 0.7)",
                    border: "1px solid rgba(48, 68, 92, 0.8)",
                    borderRadius: "8px",
                  }}
                >
                  <span
                    style={{
                      display: "block",
                      fontSize: "11px",
                      color: "#7ecef5",
                      textTransform: "uppercase",
                      letterSpacing: "0.5px",
                      marginBottom: "4px",
                    }}
                  >
                    {formatLabel(fieldName)}
                  </span>
                  <strong
                    style={{
                      display: "block",
                      color: "#e6eef7",
                      fontSize: "14px",
                      wordBreak: "break-word",
                    }}
                  >
                    {String(val)}
                  </strong>
                  {conf !== null && conf !== undefined && (
                    <span
                      style={{
                        display: "inline-block",
                        marginTop: "6px",
                        fontSize: "11px",
                        color: "#7a97b2",
                      }}
                    >
                      Confidence: {(conf * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* CONSISTENCY CHECKS */}
      <div className="findings-card">
        <h3>Consistency & logic checks</h3>
        <p className="subtext small">
          Rule-based domain validation (dates, routes, amounts, and repetitions).
        </p>

        {checks.length > 0 ? (
          checks.map((check, idx) => (
            <ReportFinding
              key={idx}
              title={formatLabel(check.name || "Rule Check")}
              status={
                check.status === "passed"
                  ? "Passed"
                  : check.status === "failed"
                  ? "Discrepancy"
                  : "Attention Needed"
              }
              type={getStatusType(check.status)}
              description={check.message}
              severity={check.severity || (check.status === "failed" ? "high" : "info")}
            />
          ))
        ) : (
          <p className="subtext small">No specific rule checks executed.</p>
        )}
      </div>

      {/* FIELD FORMAT VALIDATIONS */}
      {fieldChecks.length > 0 && (
        <div className="findings-card">
          <h3>Field format validation</h3>
          <p className="subtext small">
            Syntactic validation of extracted date formats, numeric amounts, and identifiers.
          </p>

          {fieldChecks.map((fCheck, idx) => (
            <ReportFinding
              key={idx}
              title={formatLabel(fCheck.field || "Field format")}
              status={
                fCheck.status === "passed"
                  ? "Valid Format"
                  : fCheck.status === "failed"
                  ? "Invalid Format"
                  : "Inconclusive"
              }
              type={getStatusType(fCheck.status)}
              description={fCheck.message}
              severity={fCheck.status === "failed" ? "warning" : "info"}
            />
          ))}
        </div>
      )}

      {/* TECHNICAL DETAILS */}
      <div className="findings-card">
        <h3>Technical details</h3>
        <p className="subtext small">
          Raw structured schema outputs and observations.
        </p>
        <TechnicalDetails
          title="Extracted Document Data"
          data={extractedDoc}
        />
        <TechnicalDetails
          title="Consistency Report"
          data={report}
        />
        <TechnicalDetails
          title="Field Validation Report"
          data={fieldValidation}
        />
      </div>

      <p className="disclaimer">
        Consistency examination evaluates internal logic, date chronology,
        and field syntax. It does not independently prove document authenticity
        or disprove digital tampering.
      </p>
    </section>
  );
}
