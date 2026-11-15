import React from "react";
import Status from "../components/Status";

export default function ReportFinding({
  title,
  status,
  type = "info",
  description
}) {
  return (
    <div className="finding">
      <div className="finding-heading">
        <strong>{title}</strong>
        <Status type={type}>{status}</Status>
      </div>

      {description && <p>{description}</p>}
    </div>
  );
}