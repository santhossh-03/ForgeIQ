
const API_BASE = "http://127.0.0.1:8000";

const form = document.getElementById("investigationForm");
const submitButton = document.getElementById("submitButton");
const formMessage = document.getElementById("formMessage");
const reportContent = document.getElementById("reportContent");
const reportStatus = document.getElementById("reportStatus");
const connectionStatus = document.getElementById("connectionStatus");
const historyContent = document.getElementById("historyContent");
const refreshHistoryButton = document.getElementById("refreshHistory");

let currentReport = null;
let currentMetadata = {};
let historyItems = [];
let hiddenHistoryIds = new Set();
let historyExpanded = false;

function createElement(tag, className = "", text = undefined) {
    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (text !== undefined) {
        element.textContent = text;
    }

    return element;
}

function setBadge(element, text, kind = "") {
    if (!element) return;

    element.textContent = text;
    element.className = `status-badge ${kind}`.trim();
}

// Decode HTML entities safely without interpreting report HTML.
function decodeEntities(value) {
    const textarea = document.createElement("textarea");
    textarea.innerHTML = value;
    return textarea.value;
}

// Normalize escaped Markdown and formatting artifacts from generated reports.
function normalizeReport(report) {
    if (typeof report !== "string") return "";

    let text = decodeEntities(report)
        .replace(/\r\n?/g, "\n")
        .replace(/\\([*_\-#.`])/g, "$1")
        .replace(/^[ \t]*&nbsp;[ \t]*/g, "")
        .replace(/[ \t]+\n/g, "\n");

    // Remove leftover Markdown horizontal rules from the report text.
    text = text.replace(/^[ \t]*([-*_])(?:[ \t]*\1){2,}[ \t]*$/gm, "");

    return text.trim();
}

// Render inline Markdown using DOM text nodes, never raw HTML.
function renderInlineMarkdown(container, text) {
    const pattern = /(\*\*[^*]+?\*\*|__[^_]+?__|\*[^*\n]+?\*|_[^_\n]+?_)/g;
    let lastIndex = 0;
    let match;

    while ((match = pattern.exec(text)) !== null) {
        if (match.index > lastIndex) {
            container.appendChild(
                document.createTextNode(text.slice(lastIndex, match.index))
            );
        }

        const token = match[0];
        const isBold = token.startsWith("**") || token.startsWith("__");
        const markerLength = isBold ? 2 : 1;
        const content = token.slice(markerLength, -markerLength);
        const element = document.createElement(isBold ? "strong" : "em");

        element.textContent = content;
        container.appendChild(element);

        lastIndex = pattern.lastIndex;
    }

    if (lastIndex < text.length) {
        container.appendChild(
            document.createTextNode(text.slice(lastIndex))
        );
    }
}

// Convert report headings, bullets, numbered lists, and paragraphs into HTML.
function renderMarkdownReport(report) {
    const container = document.createElement("div");
    container.className = "formatted-report";

    const text = normalizeReport(report);
    const lines = text.split("\n");

    let paragraphLines = [];
    let activeList = null;
    let previousWasHeading = false;

    function flushParagraph() {
        if (!paragraphLines.length) return;

        const paragraph = document.createElement("p");
        renderInlineMarkdown(paragraph, paragraphLines.join(" "));
        container.appendChild(paragraph);
        paragraphLines = [];
        previousWasHeading = false;
    }

    function closeList() {
        activeList = null;
    }

    function addListItem(listType, content) {
        flushParagraph();

        if (!activeList || activeList.tagName.toLowerCase() !== listType) {
            closeList();
            activeList = document.createElement(listType);
            container.appendChild(activeList);
        }

        const item = document.createElement("li");
        renderInlineMarkdown(item, content);
        activeList.appendChild(item);
        previousWasHeading = false;
    }

    for (const rawLine of lines) {
        const line = rawLine.trim();

        if (!line) {
            flushParagraph();
            closeList();
            continue;
        }

        // Markdown headings, including headings with bold markers.
        const headingMatch = line.match(/^#{1,6}\s+(.+)$/);

        // All-caps section titles are also displayed as headings.
        const cleanHeading = line.replace(/^\*\*(.*?)\*\*$/, "$1");
        const isSectionHeading =
            /^[A-Z][A-Z0-9 /&()_-]{2,}$/.test(cleanHeading) &&
            cleanHeading.length < 100;

        if (headingMatch || isSectionHeading) {
            flushParagraph();
            closeList();

            const headingText = headingMatch
                ? headingMatch[1]
                : cleanHeading;

            const heading = document.createElement("h3");
            renderInlineMarkdown(heading, headingText);
            container.appendChild(heading);
            previousWasHeading = true;
            continue;
        }

        // Support Markdown numbered lists such as 1. and 1\.
        const numberedMatch = line.match(/^\d+[.)]\s+(.+)$/);

        if (numberedMatch) {
            addListItem("ol", numberedMatch[1]);
            continue;
        }

        // Support Markdown bullets.
        const bulletMatch = line.match(/^[-*+]\s+(.+)$/);

        if (bulletMatch) {
            addListItem("ul", bulletMatch[1]);
            continue;
        }

        // Avoid merging text immediately after a heading into its heading.
        closeList();
        paragraphLines.push(line);
        previousWasHeading = false;
    }

    flushParagraph();

    return container;
}

function convertReportToPlainText(report) {
    return normalizeReport(report)
        .replace(/^#{1,6}\s+/gm, "")
        .replace(/\*\*(.*?)\*\*/g, "$1")
        .replace(/__(.*?)__/g, "$1")
        .replace(/\*(.*?)\*/g, "$1")
        .replace(/_(.*?)_/g, "$1")
        .replace(/^\s*[-*+]\s+/gm, "- ")
        .replace(/^\s*(\d+)[.)]\s+/gm, "$1. ")
        .replace(/\n{3,}/g, "\n\n")
        .trim();
}

function downloadReport() {
    if (!currentReport) {
        formMessage.textContent = "No report is available to download.";
        return;
    }

    const machineName = currentMetadata.machine_name || "machine";
    const investigationId =
        currentMetadata.investigation_id ??
        currentMetadata.id ??
        "unknown";

    const evidenceStatus =
        currentMetadata.evidence_check_passed === true
            ? "Passed"
            : currentMetadata.evidence_check_passed === false
                ? "Failed"
                : "Unavailable";

    const fileContent = [
        "FORGEIQ - INDUSTRIAL AI TROUBLESHOOTING REPORT",
        "===============================================",
        `Machine: ${machineName}`,
        `Investigation ID: ${investigationId}`,
        `Status: ${currentMetadata.status || "unknown"}`,
        `Report source: ${currentMetadata.report_source || "unknown"}`,
        `Evidence validation: ${evidenceStatus}`,
        "",
        "INVESTIGATION FINDINGS",
        "======================",
        convertReportToPlainText(currentReport),
        "",
        "EVIDENCE ISSUES",
        "===============",
        ...(Array.isArray(currentMetadata.evidence_issues) &&
        currentMetadata.evidence_issues.length
            ? currentMetadata.evidence_issues.map(issue => `- ${issue}`)
            : ["None"]),
        "",
        "Safety note: Possible causes are hypotheses until independently confirmed.",
        "Follow site safety procedures and applicable lockout/tagout requirements."
    ].join("\n");

    const blob = new Blob([fileContent], {
        type: "text/plain;charset=utf-8"
    });

    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    const safeMachineName = String(machineName)
        .replace(/[<>:"/\\|?*\x00-\x1F]/g, "_")
        .replace(/\s+/g, "_");

    link.href = url;
    link.download = `investigation_${investigationId}_${safeMachineName}.txt`;

    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);

    formMessage.textContent = "Report download requested.";
}

function renderReport(report, metadata = {}) {
    reportContent.replaceChildren();

    currentReport = report || null;
    currentMetadata = { ...metadata };

    const details = createElement(
        "p",
        "report-meta",
        `Machine: ${metadata.machine_name || "Unknown"} | Investigation ID: ${
            metadata.investigation_id ?? metadata.id ?? "Unavailable"
        }`
    );

    reportContent.appendChild(details);

    const evidencePassed = metadata.evidence_check_passed;
    const evidenceText =
        evidencePassed === true
            ? "Evidence validation passed"
            : evidencePassed === false
                ? "Evidence validation failed"
                : "Evidence validation status unavailable";

    const evidenceKind =
        evidencePassed === true
            ? "success"
            : evidencePassed === false
                ? "error"
                : "warning";

    reportContent.appendChild(
        createElement("span", `status-badge ${evidenceKind}`, evidenceText)
    );

    if (metadata.evidence_issues?.length) {
        const issuesSection = createElement("section", "report-section");
        issuesSection.appendChild(
            createElement("h3", "", "Evidence issues")
        );

        const list = document.createElement("ul");

        metadata.evidence_issues.forEach(issue => {
            list.appendChild(createElement("li", "", String(issue)));
        });

        issuesSection.appendChild(list);
        reportContent.appendChild(issuesSection);
    }

    if (metadata.error) {
        const errorSection = createElement("section", "report-section");
        errorSection.appendChild(
            createElement("h3", "", "Investigation error")
        );
        errorSection.appendChild(
            createElement("p", "", metadata.error)
        );
        reportContent.appendChild(errorSection);
    }

    if (!report) {
        reportContent.appendChild(
            createElement("p", "empty-state", "No report was generated.")
        );
        return;
    }

    const reportSection = createElement("section", "report-section");
    reportSection.appendChild(
        createElement("h3", "", "Investigation findings")
    );

    reportSection.appendChild(renderMarkdownReport(report));
    reportContent.appendChild(reportSection);

    const downloadButton = createElement(
        "button",
        "download-report-button",
        "Download report (.txt)"
    );

    downloadButton.type = "button";
    downloadButton.addEventListener("click", downloadReport);
    reportContent.appendChild(downloadButton);
}

// Add a Show/Hide History control without requiring an HTML edit.
function setupHistoryToggle() {
    if (!historyContent) return;

    const toggleButton = createElement(
        "button",
        "history-toggle-button",
        "Show History"
    );

    toggleButton.type = "button";
    toggleButton.setAttribute("aria-expanded", "false");

    historyContent.hidden = true;

    toggleButton.addEventListener("click", () => {
        historyExpanded = !historyExpanded;
        historyContent.hidden = !historyExpanded;

        toggleButton.textContent = historyExpanded
            ? "Hide History"
            : "Show History";

        toggleButton.setAttribute(
            "aria-expanded",
            String(historyExpanded)
        );
    });

    historyContent.parentNode.insertBefore(toggleButton, historyContent);
}

async function checkApi() {
    try {
        const response = await fetch(`${API_BASE}/`);

        if (!response.ok) {
            throw new Error("API unavailable");
        }

        setBadge(connectionStatus, "API connected", "success");
    } catch {
        setBadge(connectionStatus, "API disconnected", "error");
    }
}

function renderHistory() {
    historyContent.replaceChildren();

    const visibleItems = historyItems.filter(item =>
        !hiddenHistoryIds.has(String(item.id))
    );

    if (visibleItems.length === 0) {
        historyContent.appendChild(
            createElement(
                "p",
                "empty-state",
                historyItems.length
                    ? "All currently displayed investigations are hidden. Refresh history to show saved records again."
                    : "No saved investigations yet."
            )
        );
        return;
    }

    const list = createElement("div", "history-list");

    visibleItems.forEach(item => {
        const card = createElement("div", "history-item");

        const openButton = createElement("button", "history-item-open");
        openButton.type = "button";

        const left = document.createElement("span");
        left.appendChild(
            createElement("strong", "", item.machine_name || "Unknown machine")
        );
        left.appendChild(
            createElement(
                "small",
                "",
                `${item.fault_description || "No fault description"} · ${item.created_at || ""}`
            )
        );

        const right = createElement(
            "span",
            "history-item-meta",
            `#${item.id} · ${item.status || "unknown"}`
        );

        openButton.append(left, right);
        openButton.addEventListener("click", () => loadInvestigation(item.id));

        const hideButton = createElement(
            "button",
            "history-hide-button",
            "Hide"
        );
        hideButton.type = "button";
        hideButton.title = "Hide this entry from the current history view";
        hideButton.setAttribute(
            "aria-label",
            `Hide investigation ${item.id} from the current view`
        );

        hideButton.addEventListener("click", () => {
            hiddenHistoryIds.add(String(item.id));
            renderHistory();

            if (formMessage) {
                formMessage.textContent =
                    `Investigation #${item.id} hidden from this view. It remains saved in the database.`;
            }
        });

        card.append(openButton, hideButton);
        list.appendChild(card);
    });

    historyContent.appendChild(list);
}

async function loadHistory() {
    historyContent.textContent = "Loading investigation history...";

    try {
        const response = await fetch(`${API_BASE}/investigations?limit=50`);

        if (!response.ok) {
            throw new Error(`History request failed (${response.status})`);
        }

        const history = await response.json();
        historyItems = Array.isArray(history) ? history : [];

        // A refresh resets the temporary hidden list, revealing saved records.
        hiddenHistoryIds.clear();

        renderHistory();
    } catch (error) {
        historyContent.textContent =
            `Could not load history: ${error.message}`;
    }
}

async function loadInvestigation(id) {
    reportContent.textContent = "Loading saved investigation...";

    currentReport = null;
    currentMetadata = {};

    try {
        const response = await fetch(`${API_BASE}/investigations/${id}`);

        if (!response.ok) {
            throw new Error(`Request failed (${response.status})`);
        }

        const result = await response.json();

        setBadge(
            reportStatus,
            result.status || "unknown",
            result.status === "success"
                ? "success"
                : result.status === "error"
                    ? "error"
                    : "warning"
        );

        renderReport(result.report, {
            ...result,
            investigation_id: result.id
        });
    } catch (error) {
        reportContent.textContent =
            `Could not load investigation: ${error.message}`;
    }
}

if (form) {
    form.addEventListener("submit", async event => {
        event.preventDefault();

        const machineName =
            document.getElementById("machineName").value.trim();

        const faultDescription =
            document.getElementById("faultDescription").value.trim();

        if (!machineName || !faultDescription) {
            formMessage.textContent =
                "Enter both the machine name and fault description.";
            return;
        }

        submitButton.disabled = true;
        submitButton.textContent = "Investigating...";
        formMessage.textContent =
            "Investigation running. The local LLM may take some time.";

        try {
            const response = await fetch(`${API_BASE}/investigate`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    machine_name: machineName,
                    fault_description: faultDescription
                })
            });

            const result = await response.json();

            if (!response.ok) {
                throw new Error(
                    result.detail || `Request failed (${response.status})`
                );
            }

            setBadge(
                reportStatus,
                result.status || "unknown",
                result.status === "success"
                    ? "success"
                    : result.status === "error"
                        ? "error"
                        : "warning"
            );

            renderReport(result.report, result);

            formMessage.textContent =
                `Investigation #${result.investigation_id} saved.`;

            await loadHistory();
        } catch (error) {
            formMessage.textContent =
                `Investigation failed: ${error.message}`;
        } finally {
            submitButton.disabled = false;
            submitButton.textContent = "Run investigation";
        }
    });
}

if (refreshHistoryButton) {
    refreshHistoryButton.addEventListener("click", loadHistory);
}

setupHistoryToggle();
checkApi();
loadHistory();
