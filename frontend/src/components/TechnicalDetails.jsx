
import React from "react";
import { formatLabel } from "../utils/reportHelpers";

const explanations = {
  page_count: "Total number of pages in the PDF.",
  indirect_object_count: "Number of individual objects stored in the PDF structure.",
  has_previous_revision: "Indicates whether an earlier PDF revision is referenced.",
  previous_revision_offset: "Location of the previous revision in the PDF file.",
  has_xref_stream: "Indicates whether the PDF uses a cross-reference stream.",
  annotation_count: "Number of annotations found on this page.",
  link_count: "Number of clickable links found on this page.",
  embedded_font_count: "Number of embedded fonts used on this page.",
  image_reference_count: "Number of image references found on this page.",
  signature_object_count: "Number of digital signature objects found.",
  overlap_count: "Number of text regions whose bounding areas overlap. This can also occur in normal document layouts.",
  font_anomaly_count: "Number of unusual font characteristics flagged.",
  color_anomaly_count: "Number of unusual text colour characteristics flagged.",
  positioning_anomaly_count: "Number of unusual text positioning characteristics flagged.",
  text_span_count: "Number of individual text sections identified.",
  image_count: "Number of images identified in the document.",
  is_encrypted: "Indicates whether the PDF is password-protected or encrypted.",
  format: "PDF file format version.",
  creationDate: "Date and time recorded when the PDF was created.",
  modDate: "Date and time recorded for the latest modification."
};

function readableValue(value) {
  if (value === null || value === undefined || value === "") {
    return "Not available";
  }

  if (typeof value === "boolean") {
    return value ? "Yes" : "No";
  }

  if (typeof value === "string") {
    return value;
  }

  return String(value);
}

function HumanReadableData({ data, depth = 0 }) {
  if (data === null || data === undefined) {
    return <span className="technical-value">Not available</span>;
  }

  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <span className="technical-value">None recorded</span>;
    }

    return (
      <div className="technical-list">
        {data.map((item, index) => (
          <div className="technical-list-item" key={index}>
            {typeof item === "object" && item !== null ? (
              <details className="technical-nested">
                <summary>
                  {`Evidence item ${index + 1}`}
                </summary>
                <HumanReadableData data={item} depth={depth + 1} />
              </details>
            ) : (
              <span>{readableValue(item)}</span>
            )}
          </div>
        ))}
      </div>
    );
  }

  if (typeof data === "object") {
    const entries = Object.entries(data);

    if (entries.length === 0) {
      return <span className="technical-value">No information recorded</span>;
    }

    return (
      <div className="technical-fields">
        {entries.map(([key, value]) => {
          const nested =
            typeof value === "object" && value !== null;

          return (
            <div className="technical-field" key={key}>
              <div className="technical-field-heading">
                <strong>{formatLabel(key)}</strong>
                {explanations[key] && (
                  <span>{explanations[key]}</span>
                )}
              </div>

              <div className="technical-field-value">
                {nested ? (
                  <details className="technical-nested">
                    <summary>
                      {Array.isArray(value)
                        ? `${value.length} recorded item(s)`
                        : "View details"}
                    </summary>
                    <HumanReadableData
                      data={value}
                      depth={depth + 1}
                    />
                  </details>
                ) : (
                  readableValue(value)
                )}
              </div>
            </div>
          );
        })}
      </div>
    );
  }

  return <span className="technical-value">{readableValue(data)}</span>;
}

export default function TechnicalDetails({ title, data }) {
  const hasData =
    data &&
    typeof data === "object" &&
    Object.keys(data).length > 0;

  return (
    <details className="technical-details">
      <summary>{title}</summary>

      <div className="technical-details-content">
        {hasData ? (
          <HumanReadableData data={data} />
        ) : (
          <p className="subtext small">
            No additional information is available for this section.
          </p>
        )}
      </div>
    </details>
  );
}
