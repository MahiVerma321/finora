

import React from "react";
import "./Hero.css";

export default function Hero() {
  return (
    <section className="hero-section futuristic-hero" id="home">
      <div className="hero-glow hero-glow-blue" />
      <div className="hero-glow hero-glow-purple" />

      <div className="hero-content">
        <div className="hero-label">
          <span className="hero-label-dot" />
          NEXT-GENERATION DOCUMENT INTELLIGENCE
        </div>

        <h1>
          Every document
          <br />
          leaves a <span>trace.</span>
          <br />
          <span className="hero-heading-light">
            We uncover it.
          </span>
        </h1>

        <p className="hero-description">
          Go beyond what the eye can see. Investigate PDF
          manipulation, examine hidden document structures
          and verify available AI provenance evidence —
          all in one forensic workspace.
        </p>

        <div className="hero-actions">
          <a href="#upload" className="hero-cta">
            Begin examination
            <span aria-hidden="true">↗</span>
          </a>
        </div>

        <div className="hero-note">
          <span>PDF FORENSICS</span>
          <span className="hero-note-divider" />
          <span>MANIPULATION DETECTION</span>
          <span className="hero-note-divider" />
          <span>AI PROVENANCE</span>
        </div>
      </div>

      <div className="hero-visual futuristic-visual" aria-hidden="true">
        <div className="hologram-ring ring-one" />
        <div className="hologram-ring ring-two" />
        <div className="hologram-ring ring-three" />
        <div className="scan-orbit">
          <div className="scan-orbit-dot" />
        </div>

        <div className="futuristic-document">
          <div className="futuristic-document-top">
            <span className="pdf-chip">PDF</span>
            <span>FORENSIC REPORT / 001</span>
          </div>

          <div className="pdf-document-title">
            <span>DOCUMENT EXAMINATION</span>
            <strong>Digital Evidence Report</strong>
            <small>REFERENCE · DT-2026-001</small>
          </div>

          <div className="pdf-document-preview">
            <div className="pdf-preview-sidebar">
              <span />
              <span />
              <span />
              <span />
            </div>
            <div className="pdf-preview-content">
              <div className="preview-heading" />
              <div className="preview-line wide" />
              <div className="preview-line" />
              <div className="preview-line medium" />
              <div className="preview-highlight">
                <span>EXAMINATION REGION</span>
                <div />
                <div />
              </div>
              <div className="preview-line wide" />
              <div className="preview-line medium" />
            </div>
          </div>

          <div className="pdf-scan-label">
            <span className="pdf-scan-symbol">⌕</span>
            <div>
              <strong>FORENSIC SCANNING</strong>
              <span>Structural integrity inspection</span>
            </div>
            <span className="scan-status-dot" />
          </div>

          <div className="pdf-document-footer">
            <span>FINORA FORENSICS</span>
            <span>PAGE 01 / 01</span>
          </div>

          <div className="document-scan-beam" />
        </div>

        <div className="floating-data-card data-card-top">
          <span className="floating-card-icon">⌘</span>
          <div>
            <strong>STRUCTURAL ANALYSIS</strong>
            <span>PDF integrity screening</span>
          </div>
        </div>

        <div className="floating-data-card data-card-bottom">
          <span className="floating-card-icon purple-icon">◈</span>
          <div>
            <strong>AI PROVENANCE</strong>
            <span>Origin verification</span>
          </div>
        </div>

        <div className="visual-coordinate">
          SYSTEM / FINORA
          <br />
          SCAN ENGINE · ACTIVE
        </div>
      </div>
    </section>
  );
}
