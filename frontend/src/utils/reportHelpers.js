export function formatLabel(value) {
  if (!value) return "Not available";

  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());
}

export function severityType(value) {
  if (["success", "warning", "review", "info"].includes(value)) {
    return value;
  }

  if (value === "high" || value === "critical") return "warning";
  if (value === "medium") return "review";

  return "info";
}

export function validationResult(value) {
  if (value === true) {
    return {
      status: "Passed",
      type: "success",
      explanation: "The check passed."
    };
  }

  if (value === false) {
    return {
      status: "Not passed",
      type: "warning",
      explanation: "The check did not pass."
    };
  }

  return {
    status: "Not available",
    type: "info",
    explanation: "The check could not be evaluated."
  };
}