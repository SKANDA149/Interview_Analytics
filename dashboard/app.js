// Edge Interview Analytics Dashboard Logic

let currentReportData = null;
let currentTimelineData = [];

document.addEventListener("DOMContentLoaded", () => {
    fetchData();
});

async function fetchData() {
    let dataFound = false;

    try {
        // Fetch Full Report JSON (primary data source)
        const fullReportRes = await fetch('../data/reports/final_report.json', { cache: 'no-store' });
        if (fullReportRes.ok) {
            const fullReportData = await fullReportRes.json();
            currentReportData = fullReportData;
            dataFound = true;

            // Update KPIs from speech metrics
            if (fullReportData.candidate_metrics && fullReportData.candidate_metrics.speech) {
                const speech = fullReportData.candidate_metrics.speech;
                updateKPIs({
                    average_words_per_minute: speech.words_per_minute || 0,
                    total_filler_words: speech.total_filler_words || 0,
                    total_long_pauses: speech.total_long_pauses || 0,
                    total_silence_seconds: speech.total_silence_sec || 0,
                    total_chunks_processed: (fullReportData.processing_metadata || {}).total_chunks || 0
                });
            }

            // Update NLP scores
            if (fullReportData.candidate_metrics && fullReportData.candidate_metrics.nlp) {
                updateNLPScores(fullReportData.candidate_metrics.nlp);
            }

            // Diarization summary
            if (fullReportData.diarization_summary) {
                renderDiarizationSummary(fullReportData.diarization_summary);
            }

            // Speaker-labelled transcript
            if (fullReportData.transcripts && fullReportData.transcripts.speaker_labelled_transcript) {
                renderAnnotatedTranscript([]);
            }

            // Timeline from embedded data
            if (fullReportData.timeline && fullReportData.timeline.length > 0) {
                renderTimelineTable(fullReportData.timeline);
            }
        }

        // Fallback: try aggregated report if full report not available
        if (!dataFound) {
            const reportRes = await fetch('../data/reports/final_aggregated_report.json', { cache: 'no-store' });
            if (reportRes.ok) {
                currentReportData = await reportRes.json();
                updateKPIs(currentReportData.overall_metrics);
                dataFound = true;
            }
        }

        // Always fetch CSV to populate timeline table (since it is not embedded in the JSON reports)
        const csvRes = await fetch('../data/reports/interview_timeline.csv', { cache: 'no-store' });
        if (csvRes.ok) {
            const csvText = await csvRes.text();
            currentTimelineData = parseCSV(csvText);
            renderTimelineTable(currentTimelineData);
            dataFound = true;
            
            // Use CSV for transcript only if we didn't already render a speaker-labeled transcript from the JSON
            if (!currentReportData || !currentReportData.transcripts || !currentReportData.transcripts.speaker_labelled_transcript) {
                renderAnnotatedTranscript(currentTimelineData);
            }
        }

    } catch (err) {
        console.warn("Error loading pipeline data:", err);
    }

    // If no data was found at all, show helpful prompts
    if (!dataFound) {
        const container = document.getElementById("transcript-container");
        if (container) {
            container.innerHTML = `<div style="padding: 2rem; text-align: center;">
                <div style="font-size: 1.5rem; margin-bottom: 0.5rem;">📋</div>
                <div style="color: var(--text-muted); font-size: 0.95rem;">No analysis data yet.</div>
                <div style="color: var(--text-muted); font-size: 0.85rem; margin-top: 0.25rem;">Click <strong style="color: var(--accent-cyan);">Analyze Interview</strong> to process the video.</div>
            </div>`;
        }

        const tbody = document.getElementById("timeline-table-body");
        if (tbody) {
            tbody.innerHTML = `<tr><td colspan="6" style="text-align: center; color: var(--text-muted);">Click "Analyze Interview" to generate timeline data.</td></tr>`;
        }

        const diarizationBox = document.getElementById("diarization-summary");
        if (diarizationBox) {
            diarizationBox.innerHTML = `<p style="color: var(--text-muted);">No diarization data yet. Run the analysis first.</p>`;
        }
    }
}

function updateKPIs(metrics) {
    if (!metrics) return;
    document.getElementById("kpi-wpm").textContent = `${metrics.average_words_per_minute || 0} WPM`;
    document.getElementById("kpi-fillers").textContent = metrics.total_filler_words || 0;
    document.getElementById("kpi-pauses").textContent = metrics.total_long_pauses || 0;
    document.getElementById("kpi-silence").textContent = `${metrics.total_silence_seconds || 0}s`;
    
    document.getElementById("transcript-count-pill").textContent = `${metrics.total_chunks_processed || 0} Chunks Processed`;

    if (currentReportData && currentReportData.candidate_metrics && currentReportData.candidate_metrics.nlp) {
        updateNLPScores(currentReportData.candidate_metrics.nlp);
    }
}

function updateNLPScores(nlp) {
    if (!nlp) return;
    
    const overallScore = nlp.overall_score || 0;
    
    // Update KPI card
    const kpiNlp = document.getElementById("kpi-nlp");
    if (kpiNlp) kpiNlp.textContent = `${overallScore}%`;
    
    // Update sub-scores
    const scoreSemantic = document.getElementById("score-semantic");
    if (scoreSemantic) scoreSemantic.textContent = `${nlp.semantic_score || 0}%`;
    
    const scoreReq = document.getElementById("score-req");
    if (scoreReq) scoreReq.textContent = `${nlp.requirement_score || 0}%`;
    
    const scoreKeyword = document.getElementById("score-keyword");
    if (scoreKeyword) scoreKeyword.textContent = `${nlp.keyword_score || 0}%`;
    
    // Update overall score
    const evalScoreVal = document.getElementById("eval-score-val");
    if (evalScoreVal) evalScoreVal.textContent = `${overallScore}%`;
    
    const labelVal = document.getElementById("eval-label-val");
    if (labelVal) {
        labelVal.textContent = nlp.match_level || "Unknown";
        if (overallScore >= 75) {
            labelVal.className = "pill pill-emerald";
        } else if (overallScore >= 50) {
            labelVal.className = "pill pill-amber";
        } else {
            labelVal.className = "pill pill-rose";
        }
    }
    
    // Update the KPI NLP subtitle
    const kpiNlpLabel = document.getElementById("kpi-nlp-label");
    if (kpiNlpLabel) kpiNlpLabel.textContent = `${nlp.match_level || "N/A"}`;
}

function renderDiarizationSummary(summary) {
    const container = document.getElementById("diarization-summary");
    if (!container) return;
    if (!summary || !summary.speakers || summary.speakers.length === 0) {
        container.innerHTML = "<p>No diarization data available.</p>";
        return;
    }

    let html = "";
    summary.speakers.forEach(speaker => {
        html += `
            <div style="flex: 1; padding: 1rem; background: var(--bg-card-hover); border-radius: 8px; border: 1px solid var(--border-color);">
                <div style="font-weight: 600; margin-bottom: 0.5rem; color: var(--text-color);">${speaker.role}</div>
                <div style="font-size: 1.25rem; font-weight: 700; color: var(--accent-cyan);">${parseFloat(speaker.total_speech_sec).toFixed(1)}s</div>
                <div style="font-size: 0.85rem; color: var(--text-muted);">${speaker.segment_count} segments</div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function renderAnnotatedTranscript(chunks) {
    const container = document.getElementById("transcript-container");
    const fillerRegex = /\b(um|uh|like|so|you know)\b/gi;
    let html = "";

    // Check if we have speaker-labelled transcript from the full report
    if (currentReportData && currentReportData.transcripts && currentReportData.transcripts.speaker_labelled_transcript) {
        const labelled = currentReportData.transcripts.speaker_labelled_transcript;
        if (labelled.length === 0) {
            container.innerHTML = "<p>No transcript data available.</p>";
            return;
        }
        
        labelled.forEach(turn => {
            const speaker = turn.speaker || "UNKNOWN";
            const text = turn.text || "";
            const start = parseFloat(turn.start || 0).toFixed(1);
            const end = parseFloat(turn.end || 0).toFixed(1);
            
            let annotatedText = text.replace(fillerRegex, (match) => `<span class="filler-tag">${match}</span>`);
            const pillClass = speaker === "CANDIDATE" ? "pill-emerald" : "pill-cyan";
            
            html += `<p style="margin-bottom: 12px;">
                <span class="pill ${pillClass}" style="margin-right: 8px;">${speaker}</span>
                <span style="font-size: 0.8em; color: var(--text-muted);">[${start}s - ${end}s]</span><br>
                ${annotatedText}
            </p>`;
        });
        container.innerHTML = html;
        return;
    }

    // Fallback to chunk-based transcript
    if (!chunks || chunks.length === 0) {
        container.innerHTML = "<p>No transcript data available.</p>";
        return;
    }

    chunks.forEach(chunk => {
        let text = chunk.Transcript || "";
        if (!text) return;

        // Highlight filler words
        let annotatedText = text.replace(fillerRegex, (match) => `<span class="filler-tag">${match}</span>`);
        
        // Add pause badge if chunk has long pauses
        let pauseBadge = "";
        const pauses = parseInt(chunk.Long_Pauses || 0);
        if (pauses > 0) {
            pauseBadge = `<span class="pause-tag">⏸️ ${pauses} Hesitation Pause(s)</span>`;
        }

        html += `<p style="margin-bottom: 12px;"><strong>[${chunk.Chunk_ID}]</strong> ${annotatedText} ${pauseBadge}</p>`;
    });

    container.innerHTML = html || "<p style='color: var(--text-muted);'>Transcript empty.</p>";
}

function renderTimelineTable(chunks) {
    const tbody = document.getElementById("timeline-table-body");
    if (!chunks || chunks.length === 0) {
        tbody.innerHTML = "<tr><td colspan='6' style='text-align:center;'>No chunks found.</td></tr>";
        return;
    }

    let html = "";
    chunks.forEach(chunk => {
        // Reports use snake_case while the CSV uses title-case headers.
        // Accept both formats so the embedded report is rendered correctly.
        const id = chunk.Chunk_ID || chunk.chunk_id || "—";
        const transcript = chunk.Transcript || chunk.candidate_transcript || "";
        const fillers = parseInt(chunk.Filler_Words ?? chunk.filler_words ?? 0);
        const pauses = parseInt(chunk.Long_Pauses ?? chunk.long_pauses ?? 0);
        const silence = parseFloat(chunk.Silence_Seconds ?? chunk.silence_sec ?? 0).toFixed(1);
        const wpm = parseFloat(chunk.WPM ?? chunk.wpm ?? 0).toFixed(0);

        const fillerPill = fillers > 0 ? `<span class="pill pill-amber">${fillers} fillers</span>` : `<span class="pill pill-emerald">0</span>`;
        const pausePill = pauses > 0 ? `<span class="pill pill-rose">${pauses} pause(s)</span>` : `<span class="pill pill-emerald">0</span>`;

        html += `
            <tr>
                <td><strong>${id}</strong></td>
                <td style="max-width: 320px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${transcript}</td>
                <td>${fillerPill}</td>
                <td>${pausePill}</td>
                <td>${silence}s</td>
                <td>${wpm} WPM</td>
            </tr>
        `;
    });

    tbody.innerHTML = html;
}

function parseCSV(text) {
    const lines = text.trim().split('\n');
    if (lines.length < 2) return [];

    const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''));
    const results = [];

    for (let i = 1; i < lines.length; i++) {
        // Handle CSV split with quotes safely
        const row = lines[i].split(/,(?=(?:[^\"]*\"[^\"]*\")*[^\"]*$)/);
        if (row.length === headers.length) {
            let obj = {};
            headers.forEach((h, index) => {
                obj[h] = row[index].trim().replace(/^"|"$/g, '');
            });
            results.push(obj);
        }
    }
    return results;
}

async function runAnalysis() {
    const jobTitle = document.getElementById("job-title-input").value.trim();
    const jobDesc = document.getElementById("job-desc-input").value.trim();
    const skills = document.getElementById("skills-input").value.trim();
    const additional = document.getElementById("additional-input").value.trim();

    const btn = document.getElementById("analyze-btn");
    const statusDiv = document.getElementById("analysis-status");
    
    // Show loading state
    btn.disabled = true;
    btn.textContent = "⏳ Running Pipeline...";
    statusDiv.style.display = "block";
    statusDiv.textContent = "Processing video through the full pipeline. This may take a few minutes...";

    const payload = {
        job_title: jobTitle,
        job_description: jobDesc,
        key_skills: skills,
        additional_keywords: additional
    };

    try {
        const response = await fetch('/api/run-pipeline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.ok) {
            const errData = await response.json().catch(() => ({}));
            throw new Error(errData.error || `Server error ${response.status}`);
        }

        const data = await response.json();
        statusDiv.textContent = "✅ Analysis complete. Refreshing dashboard...";
        
        // Reload all dashboard data from the freshly generated report
        await fetchData();
        
        statusDiv.style.display = "none";

    } catch (e) {
        console.error("Error running pipeline:", e);
        statusDiv.style.display = "block";
        statusDiv.style.color = "var(--accent-rose)";
        statusDiv.textContent = `❌ Error: ${e.message}`;
    } finally {
        btn.disabled = false;
        btn.textContent = "🎯 Analyze Interview";
    }
}

function exportReport() {
    alert("Exporting CSV report for interview candidate data...");
    window.open('../data/reports/interview_timeline.csv', '_blank');
}
