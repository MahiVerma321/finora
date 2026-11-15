import React from "react";
import "./Header.css";

export default function Header() {
  return (
    <header className="site-header">
      <a className="brand" href="#home">
        <div className="brand-icon">
          <svg
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M7 3.5h7l4 4V20a1 1 0 0 1-1 1H7a1 1 0 0 1-1-1V4.5a1 1 0 0 1 1-1Z" />
            <path d="M14 3.5V8h4" />
            <path d="M9 12h6M9 16h6" />
            <circle cx="17.5" cy="17.5" r="3.5" />
            <path d="m20 20 2 2" />
          </svg>
        </div>

        <div className="brand-copy">
          <span className="brand-name">
            FI<span>NORA</span>
          </span>
          <span className="brand-caption">
            DIGITAL DOCUMENT FORENSICS
          </span>
        </div>
      </a>

      <nav className="header-nav">
        <a href="#home" className="nav-link active">Overview</a>
        <a href="#upload" className="nav-link">PDF Examination</a>
        <a href="#capabilities" className="nav-link">Capabilities</a>
      </nav>

      <div className="system-status">
        <span className="status-dot" />
        <span>LOCAL ANALYSIS SYSTEM</span>
      </div>
    </header>
  );
}
