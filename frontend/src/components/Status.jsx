import React from "react";

export default function Status({ type = "info", children }) {
  return (
    <span className={`severity severity-${type}`}>
      {children}
    </span>
  );
}