
import React from "react";
import "./ProvenanceReport.css";
import Status from "../components/Status";
import InfoCard from "../components/InfoCard";
import ReportFinding from "./ReportFinding";
import TechnicalDetails from "../components/TechnicalDetails";
import { validationResult } from "../utils/reportHelpers";

export default function ProvenanceReport({ aiAnalysis }) {
  if (!aiAnalysis) return null;

  const pdfAnalysis = aiAnalysis.pdf_analysis || {};
  const aiChecks = pdfAnalysis.checks || {};

  const provenance = aiChecks.provenance || {};
  const provenanceDetails = provenance.provenance || {};
  const validation = provenance.validation || {};

  const identifiedPlatforms =
    provenance.platform_identification?.identified_platforms || [];

  const metadataAssessment =
    provenance.metadata_platform_assessment || {};

  const possiblePlatforms =
    metadataAssessment.possible_platforms || [];

  function getProvenanceResult() {
    if (provenance.status === "unavailable") {
      return {
        title: "Origin information could not be examined",
        type: "warning",
        explanation:
          provenance.assessment ||
          "The embedded origin information could not be read or verified."
      };
    }

    if (provenance.manifest_detected === true) {
      return {
        title: "Document origin record detected",
        type: "success",
        explanation:
          "An embedded origin record was found. Its declarations and verification results are presented below."
      };
    }

    if (provenance.manifest_detected === false) {
      return {
        title: "No embedded origin record found",
        type: "info",
        explanation:
          "No supported origin record was detected. This does not prove that the document was created by a human or rule out AI generation."
      };
    }

    return {
      title: "Origin examination completed",
      type: "info",
      explanation: "Review the available examination results below."
    };
  }

  const report = getProvenanceResult();

  const signature = validationResult(validation.signature_valid);
  const hash = validationResult(validation.data_hash_valid);

  const certificateUntrusted =
    validation.signing_certificate_untrusted;

  return (
    <section className="analysis-section provenance-section">

      {/* HEADER */}
      <div className="card-heading">
        <div>
          <p className="eyebrow">STEP 05</p>
          <h3>AI provenance report</h3>
          <p className="subtext small">
            Examination of declared document origin and integrity.
          </p>
        </div>

        <span className="file-limit">
          {aiAnalysis.status || "Unknown"}
        </span>
      </div>

      {/* MAIN RESULT */}
      <div className="summary-card provenance-summary">
        <p className="eyebrow">ORIGIN EXAMINATION RESULT</p>

        <div className="finding-heading">
          <h3>{report.title}</h3>

          <Status type={report.type}>
            {report.type === "success"
              ? "Record found"
              : report.type === "warning"
                ? "Unavailable"
                : "No record detected"}
          </Status>
        </div>

        <p className="subtext small">
          {report.explanation}
        </p>

        <div className="result-grid">
          <InfoCard
            label="Document format"
            value={(aiAnalysis.file_type || "PDF").toUpperCase()}
          />

          <InfoCard
            label="Examination status"
            value={aiAnalysis.status || "Unknown"}
          />
        </div>
      </div>

      {/* PLATFORM IDENTIFICATION */}
      <div className="findings-card provenance-card">
        <div className="provenance-card-heading">
          <div>
            <p className="eyebrow">PLATFORM EXAMINATION</p>
            <h3>AI tool identification</h3>
          </div>
        </div>

        {identifiedPlatforms.length > 0 ? (
          <>
            <p className="subtext small">
              These platform names were explicitly identified
              in the available provenance information.
            </p>

            {identifiedPlatforms.map((item, index) => (
              <ReportFinding
                key={index}
                title={item.platform}
                status="Identified"
                type="success"
                description="The platform name was found in declared provenance information."
              />
            ))}
          </>
        ) : (
          <div className="provenance-empty">
            <Status type="info">No platform identified</Status>
            <p className="subtext">
              No recognized AI platform was identified in the
              available provenance information. This does not
              establish that AI was not used.
            </p>
          </div>
        )}
      </div>

      {/* DECLARED ORIGIN */}
      {provenance.manifest_detected === true && (
        <div className="findings-card provenance-card">
          <p className="eyebrow">DECLARED INFORMATION</p>
          <h3>Document origin information</h3>

          <p className="subtext small">
            Information recorded by the document's embedded
            origin record. These are declarations, not independent
            proof of authorship.
          </p>

          <div className="result-grid">
            <InfoCard
              label="AI generation declared"
              value={
                provenanceDetails.ai_generation_declared === true
                  ? "Yes"
                  : provenanceDetails.ai_generation_declared === false
                    ? "No"
                    : "Not available"
              }
            />

            <InfoCard
              label="ChatGPT declared"
              value={
                provenanceDetails.chatgpt_declared === true
                  ? "Yes"
                  : provenanceDetails.chatgpt_declared === false
                    ? "No"
                    : "Not available"
              }
            />

            <InfoCard
              label="OpenAI association"
              value={
                provenanceDetails.openai_associated === true
                  ? "Yes"
                  : provenanceDetails.openai_associated === false
                    ? "No"
                    : "Not available"
              }
            />

            <InfoCard
              label="Declared generator"
              value={
                provenanceDetails.generator_names?.join(", ") ||
                "Not specified"
              }
            />

            <InfoCard
              label="Record issuer"
              value={provenanceDetails.issuer || "Not specified"}
            />
          </div>
        </div>
      )}

      {/* INTEGRITY VERIFICATION */}
      {provenance.manifest_detected === true && (
        <div className="findings-card provenance-card">
          <p className="eyebrow">VERIFICATION</p>
          <h3>Document integrity checks</h3>

          <p className="subtext small">
            These checks examine the embedded record's digital
            signature, the recorded document content, and the
            certificate's trust status.
          </p>

          <ReportFinding
            title="Digital signature"
            status={signature.status}
            type={signature.type}
            description={
              validation.signature_valid === true
                ? "The digital signature passed the verifier's check."
                : validation.signature_valid === false
                  ? "The digital signature did not pass the verifier's check."
                  : "A signature result is not available."
            }
          />

          <ReportFinding
            title="Document content integrity"
            status={hash.status}
            type={hash.type}
            description={
              validation.data_hash_valid === true
                ? "The checked document content matched its recorded hash."
                : validation.data_hash_valid === false
                  ? "The checked document content did not match its recorded hash."
                  : "A document content integrity result is not available."
            }
          />

          <ReportFinding
            title="Signing certificate trust"
            status={
              certificateUntrusted === true
                ? "Not trusted"
                : certificateUntrusted === false
                  ? "Not flagged as untrusted"
                  : "Unknown"
            }
            type={
              certificateUntrusted === true
                ? "warning"
                : certificateUntrusted === false
                  ? "success"
                  : "info"
            }
            description={
              certificateUntrusted === true
                ? "The verifier does not trust the signing certificate. This is separate from whether the signature itself is mathematically valid."
                : certificateUntrusted === false
                  ? "The verifier did not flag the certificate as untrusted. This does not independently establish the signer's identity."
                  : "The certificate trust result is not available."
            }
          />
        </div>
      )}

      {/* METADATA INDICATIONS */}
      <div className="findings-card provenance-card">
        <p className="eyebrow">SUPPLEMENTARY EVIDENCE</p>
        <h3>Other possible software indications</h3>

        <p className="subtext small">
          PDF properties may contain software names associated
          with document creation or editing. These indications
          are not verified proof of AI authorship.
        </p>

        {possiblePlatforms.length > 0 ? (
          possiblePlatforms.map((item, index) => (
            <ReportFinding
              key={index}
              title={item.platform}
              status="Possible indication"
              type="review"
              description={`This name was found in PDF metadata. Confidence: ${item.confidence || "Low"}.`}
            />
          ))
        ) : (
          <p className="subtext">
            No possible AI platform indications were found
            in the examined PDF metadata.
          </p>
        )}
      </div>

      {/* UNAVAILABLE PROVENANCE */}
      {provenance.status === "unavailable" && (
        <div className="findings-card provenance-card">
          <h3>Why could the origin record not be examined?</h3>
          <p className="subtext">
            {provenance.assessment ||
              "The available provenance information could not be read or verified."}
          </p>
        </div>
      )}

      {/* NO MANIFEST */}
      {provenance.manifest_detected === false && (
        <div className="findings-card provenance-card">
          <h3>What does no origin record mean?</h3>
          <p className="subtext">
            The document does not contain a supported embedded
            origin record detectable by the current examination.
            The record may never have been added, or it may have
            been removed or become unreadable during editing or
            conversion. This does not establish human authorship.
          </p>
        </div>
      )}

      {/* TECHNICAL DETAILS */}
      <div className="findings-card provenance-card">
        <p className="eyebrow">ADVANCED EXAMINATION</p>
        <h3>Technical details</h3>

        <p className="subtext small">
          Additional evidence for technical reviewers and investigators.
          Expand a section only when needed.
        </p>

        <TechnicalDetails
          title="PDF metadata"
          data={aiChecks.metadata || {}}
        />

        <TechnicalDetails
          title="PDF document structure"
          data={aiChecks.document_structure || {}}
        />

        <TechnicalDetails
          title="Font examination"
          data={aiChecks.fonts || {}}
        />

        <TechnicalDetails
          title="Image references"
          data={aiChecks.images || {}}
        />

        <TechnicalDetails
          title="Page-level examination"
          data={aiChecks.page_analysis || {}}
        />

        <TechnicalDetails
          title="Complete provenance information"
          data={provenance}
        />

        <TechnicalDetails
          title="Cryptographic validation details"
          data={validation}
        />

        <TechnicalDetails
          title="Additional PDF findings"
          data={pdfAnalysis.findings || []}
        />
      </div>

      <p className="disclaimer">
        The presence of an AI declaration or platform name
        indicates information recorded in the available
        provenance data. The absence of such information
        does not rule out AI generation. Signature validity
        and certificate trust are separate checks.
      </p>

    </section>
  );
}
