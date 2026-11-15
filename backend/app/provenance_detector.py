
import json
from pathlib import Path

import pymupdf
from c2pa import Reader


# Platform names explicitly declared in C2PA information.
PLATFORM_RULES = {
    "ChatGPT": ["chatgpt"],
    "OpenAI": ["openai", "dall-e", "dall·e"],
    "Google Gemini": ["gemini"],
    "Adobe Firefly": ["firefly"],
    "Microsoft Copilot": ["copilot"],
    "Microsoft Designer": ["designer"],
    "Midjourney": ["midjourney"],
    "Stability AI": ["stability ai", "stable diffusion"],
    "Canva Magic Studio": ["magic studio"]
}


def identify_platform(generator_names, action_details):
    """
    Identify platforms explicitly declared in C2PA
    generator and software-agent information.
    """

    evidence_values = []

    for name in generator_names:
        if name:
            evidence_values.append({
                "source": "claim_generator_info",
                "value": name
            })

    for action in action_details:
        software = action.get("software")

        if software:
            evidence_values.append({
                "source": "softwareAgent",
                "value": software
            })

    matches = []

    for platform, keywords in PLATFORM_RULES.items():
        matched_evidence = []

        for evidence in evidence_values:
            value = evidence["value"].lower()

            if any(keyword in value for keyword in keywords):
                matched_evidence.append(evidence)

        if matched_evidence:
            matches.append({
                "platform": platform,
                "evidence": matched_evidence
            })

    if not matches:
        return {
            "status": "not_identified",
            "identified_platforms": [],
            "message": (
                "No recognized AI platform was explicitly "
                "identified in the available C2PA information."
            )
        }

    return {
        "status": "identified",
        "identified_platforms": matches,
        "message": (
            "Platform names were declared in C2PA provenance."
        )
    }


def analyze_pdf_metadata_evidence(file_path):
    """
    Examine PDF metadata for possible software/platform
    indications.

    Metadata is not proof of AI authorship or platform identity.
    """

    try:
        with pymupdf.open(str(file_path)) as document:
            metadata = document.metadata or {}

        relevant_fields = [
            "title",
            "author",
            "creator",
            "producer",
            "subject",
            "keywords"
        ]

        metadata_evidence = []

        for field in relevant_fields:
            value = metadata.get(field)

            if value and str(value).strip():
                metadata_evidence.append({
                    "field": field,
                    "value": str(value).strip()
                })

        possible_matches = []

        for platform, keywords in PLATFORM_RULES.items():
            matched_evidence = []

            for evidence in metadata_evidence:
                value = evidence["value"].lower()

                if any(keyword in value for keyword in keywords):
                    matched_evidence.append(evidence)

            if matched_evidence:
                possible_matches.append({
                    "platform": platform,
                    "confidence": "low",
                    "evidence": matched_evidence
                })

        if possible_matches:
            return {
                "status": "possible_indication",
                "possible_platforms": possible_matches,
                "metadata": metadata_evidence,
                "message": (
                    "Possible platform-related metadata was found. "
                    "This is a weak software indication and does "
                    "not verify AI authorship or platform identity."
                )
            }

        return {
            "status": "insufficient_evidence",
            "possible_platforms": [],
            "metadata": metadata_evidence,
            "message": (
                "No recognizable AI platform identifier was found "
                "in the examined PDF metadata."
            )
        }

    except Exception as error:
        return {
            "status": "unavailable",
            "possible_platforms": [],
            "error": str(error),
            "message": "PDF metadata evidence could not be examined."
        }


def analyze_provenance(file_path):
    """
    Inspect embedded C2PA provenance and PDF metadata.

    Missing provenance does not establish human authorship.
    Metadata indications are not proof of AI generation.
    """

    file_path = Path(file_path)

    if not file_path.exists():
        return {
            "status": "failed",
            "error": "File not found."
        }

    # ---------------------------------------------
    # ADDITIONAL PDF METADATA ANALYSIS
    # ---------------------------------------------

    metadata_analysis = analyze_pdf_metadata_evidence(file_path)

    try:
        with Reader(str(file_path)) as reader:
            embedded = reader.is_embedded()

            if not embedded:
                return {
                    "status": "completed",
                    "manifest_detected": False,
                    "provenance": None,
                    "validation": None,

                    "platform_identification": {
                        "status": "not_identified",
                        "identified_platforms": []
                    },

                    "metadata_platform_assessment": metadata_analysis,

                    "assessment": (
                        "No embedded C2PA manifest detected. "
                        "PDF metadata was examined separately, "
                        "but metadata alone cannot establish "
                        "AI authorship or platform identity."
                    )
                }

            manifest = json.loads(reader.json())

        active_id = manifest.get("active_manifest")
        manifests = manifest.get("manifests", {})
        active = manifests.get(active_id, {})

        generators = active.get("claim_generator_info", [])

        generator_names = [
            item.get("name", "")
            for item in generators
        ]

        signature_info = active.get("signature_info", {})

        assertions = active.get("assertions", [])

        actions = []

        for assertion in assertions:
            if assertion.get("label", "").startswith(
                "c2pa.actions"
            ):
                actions.extend(
                    assertion.get("data", {}).get("actions", [])
                )

        action_details = []

        for action in actions:
            software = action.get("softwareAgent", {})

            if isinstance(software, dict):
                software_name = software.get("name")
                software_version = software.get("version")
            else:
                software_name = software
                software_version = None

            action_details.append({
                "action": action.get("action"),
                "software": software_name,
                "software_version": software_version,
                "digital_source_type": action.get(
                    "digitalSourceType"
                ),
                "when": action.get("when")
            })

        # ---------------------------------------------
        # C2PA PLATFORM IDENTIFICATION
        # ---------------------------------------------

        platform_identification = identify_platform(
            generator_names,
            action_details
        )

        declared_platforms = [
            item["platform"]
            for item in platform_identification.get(
                "identified_platforms", []
            )
        ]

        # ---------------------------------------------
        # VALIDATION INFORMATION
        # ---------------------------------------------

        validation_status = manifest.get(
            "validation_status", []
        )

        validation_results = manifest.get(
            "validation_results", {}
        )

        active_results = validation_results.get(
            "activeManifest", {}
        )

        success_codes = [
            item.get("code")
            for item in active_results.get("success", [])
        ]

        failure_codes = [
            item.get("code")
            for item in active_results.get("failure", [])
        ]

        untrusted_signing = any(
            item.get("code") == "signingCredential.untrusted"
            for item in validation_status
        )

        signature_valid = (
            "claimSignature.validated" in success_codes
        )

        data_hash_valid = (
            "assertion.dataHash.match" in success_codes
        )

        issuer = signature_info.get("issuer", "")
        common_name = signature_info.get("common_name", "")

        # ---------------------------------------------
        # AI GENERATION DECLARATION
        # ---------------------------------------------

        declared_ai_generation = any(
            "trainedAlgorithmicMedia" in (
                action.get("digital_source_type") or ""
            )
            for action in action_details
        )

        openai_associated = any(
            "openai" in value.lower()
            for value in (generator_names + [issuer, common_name])
            if value
        )

        chatgpt_declared = "ChatGPT" in declared_platforms

        # ---------------------------------------------
        # FINAL RESULT
        # ---------------------------------------------

        return {
            "status": "completed",
            "manifest_detected": True,

            "platform_identification": platform_identification,

            "metadata_platform_assessment": metadata_analysis,

            "provenance": {
                "generator_names": generator_names,
                "issuer": issuer,
                "signing_certificate_name": common_name,
                "chatgpt_declared": chatgpt_declared,
                "openai_associated": openai_associated,
                "ai_generation_declared": declared_ai_generation,
                "identified_platforms": declared_platforms,
                "actions": action_details
            },

            "validation": {
                "validation_state": manifest.get(
                    "validation_state"
                ),
                "signature_valid": signature_valid,
                "data_hash_valid": data_hash_valid,
                "signing_certificate_untrusted": untrusted_signing,
                "failure_codes": failure_codes,
                "success_codes": success_codes
            },

            "assessment": (
                "AI-related provenance declaration detected."
                if declared_ai_generation
                else
                "C2PA provenance detected, but an AI "
                "generation declaration was not established."
            )
        }

    except Exception as error:
        error_message = str(error)

        if (
            "ManifestNotFound" in error_message
            or "no JUMBF data found" in error_message
        ):
            return {
                "status": "completed",
                "manifest_detected": False,
                "provenance": None,
                "validation": None,

                "platform_identification": {
                    "status": "not_identified",
                    "identified_platforms": []
                },

                "metadata_platform_assessment": metadata_analysis,

                "assessment": (
                    "No embedded C2PA manifest detected. "
                    "Metadata evidence is supplementary and "
                    "does not prove AI authorship."
                )
            }

        return {
            "status": "unavailable",
            "manifest_detected": None,
            "metadata_platform_assessment": metadata_analysis,
            "error": error_message,
            "assessment": (
                "C2PA provenance could not be read or verified."
            )
        }
