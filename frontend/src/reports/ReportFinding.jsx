import React from "react";
import Status from "../components/Status";

function severityNote(severity) {
  if (!severity) return null;
  const s = severity.toLowerCase();
  if (s === "high" || s === "critical" || s === "warning") {
    return "This finding warrants close review.";
  }
  if (s === "medium" || s === "review") {
    return "This is an indicator that may appear in legitimate documents.";
  }
  if (s === "info" || s === "low") {
    return "Informational observation.";
  }
  return null;
}

export default function ReportFinding({
  title,
  status,
  type = "info",
  description,
  severity,
}) {
  const note = severityNote(severity);

  return (
    <div className="finding">
      <div className="finding-heading">
        <strong>{title}</strong>
        <Status type={type}>{status}</Status>
      </div>

      {description && <p>{description}</p>}

      {note && (
        <p className="finding-severity-note">{note}</p>
      )}
    </div>
  );
}
