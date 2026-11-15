import React from "react";

export default function InfoCard({ label, value }) {
  return (
    <div className="info-card">
      <span>{label}</span>
      <strong>{value ?? "Not available"}</strong>
    </div>
  );
}