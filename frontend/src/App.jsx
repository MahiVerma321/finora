

import React, { useState } from "react";

import Header from "./components/Header";
import Hero from "./components/Hero";
import UploadSection from "./components/UploadSection";

import ManipulationReport from "./reports/ManipulationReport";
import ProvenanceReport from "./reports/ProvenanceReport";

const API_URL = "http://127.0.0.1:8000";

export default function App() {
  const [file, setFile] = useState(null);
  const [result, setResult] = useState(null);

  const [analysis, setAnalysis] = useState(null);
  const [aiAnalysis, setAiAnalysis] = useState(null);

  const [error, setError] = useState("");
  const [analysisError, setAnalysisError] = useState("");
  const [aiAnalysisError, setAiAnalysisError] = useState("");

  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [aiAnalyzing, setAiAnalyzing] = useState(false);

  const isPdf =
    result?.type?.toLowerCase() === "pdf" ||
    result?.file_type?.toLowerCase() === "pdf" ||
    file?.type === "application/pdf" ||
    file?.name?.toLowerCase().endsWith(".pdf");

  function resetAnalyses() {
    setAnalysis(null);
    setAiAnalysis(null);
    setAnalysisError("");
    setAiAnalysisError("");
  }

  async function handleUpload(event) {
    event.preventDefault();

    if (!file) {
      setError("Please select a PDF file first.");
      return;
    }

    const isValidPdf =
      file.type === "application/pdf" ||
      file.name.toLowerCase().endsWith(".pdf");

    if (!isValidPdf) {
      setError("Only PDF files are supported.");
      return;
    }

    if (file.size > 15 * 1024 * 1024) {
      setError("File size must not exceed 15 MB.");
      return;
    }

    setLoading(true);
    setError("");
    setResult(null);
    resetAnalyses();

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/api/upload`, {
        method: "POST",
        body: formData
      });

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(
          payload.detail || "Unable to upload the PDF."
        );
      }

      setResult(payload);
    } catch (err) {
      setError(
        err.message || "Upload failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleManipulationAnalysis() {
    if (!result?.file_id) {
      setAnalysisError("Please upload a PDF first.");
      return;
    }

    setAnalyzing(true);
    setAnalysisError("");
    setAnalysis(null);

    try {
      const response = await fetch(
        `${API_URL}/api/manipulation/${result.file_id}`
      );

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(
          payload.detail || "Manipulation analysis failed."
        );
      }

      setAnalysis(payload.manipulation_analysis ?? payload);
    } catch (err) {
      setAnalysisError(
        err.message || "Unable to complete manipulation analysis."
      );
    } finally {
      setAnalyzing(false);
    }
  }

  async function handleAIContentAnalysis() {
    if (!result?.file_id) {
      setAiAnalysisError("Please upload a PDF first.");
      return;
    }

    setAiAnalyzing(true);
    setAiAnalysisError("");
    setAiAnalysis(null);

    try {
      const response = await fetch(
        `${API_URL}/api/ai-content/${result.file_id}`
      );

      const payload = await response.json();

      if (!response.ok) {
        throw new Error(
          payload.detail || "AI provenance analysis failed."
        );
      }

      setAiAnalysis(payload.ai_content_analysis ?? payload);
    } catch (err) {
      setAiAnalysisError(
        err.message || "Unable to complete AI provenance analysis."
      );
    } finally {
      setAiAnalyzing(false);
    }
  }

  return (
    <main className="page">
      <Header />

      <Hero />

      <UploadSection
        file={file}
        setFile={setFile}
        setResult={setResult}
        result={result}
        isPdf={isPdf}
        loading={loading}
        analyzing={analyzing}
        aiAnalyzing={aiAnalyzing}
        error={error}
        analysisError={analysisError}
        aiAnalysisError={aiAnalysisError}
        handleUpload={handleUpload}
        handleManipulationAnalysis={handleManipulationAnalysis}
        handleAIContentAnalysis={handleAIContentAnalysis}
        resetAnalyses={resetAnalyses}
        setError={setError}
      />

      <ManipulationReport analysis={analysis} />

      <ProvenanceReport aiAnalysis={aiAnalysis} />

      <footer>
        DIGITAL DOCUMENT FORENSICS · PDF FORENSIC SCREENING · PROTOTYPE
      </footer>
    </main>
  );
}
