"""
dashboard.py — Renders the resume analytics dashboard as a self-contained HTML string.
Call render_dashboard(data: dict) -> str and pass the output to st.components.v1.html().
"""

import json


def render_dashboard(data: dict) -> str:
    skills_json = json.dumps(data.get("skills", []))
    jobs_json = json.dumps(data.get("job_matches", []))
    keywords_found_json = json.dumps(data.get("keywords_found", []))
    keywords_missing_json = json.dumps(data.get("keywords_missing", []))

    ats_score = data.get("ats_score", 0)
    ats_label = data.get("ats_label", "Fair")
    percentile_note = data.get("percentile_note", "")
    bullet_quality = data.get("bullet_quality", 0)
    word_count = data.get("word_count", 0)
    formatting_issues = data.get("formatting_issues", 0)
    action_verbs = data.get("action_verbs_count", 0)
    quantified = data.get("quantified_bullets", 0)
    total_bullets = data.get("total_bullets", 0)
    section_comp = data.get("section_completeness", 0)
    kw_found_count = len(data.get("keywords_found", []))
    kw_total = kw_found_count + len(data.get("keywords_missing", []))
    kw_pct = round(kw_found_count / kw_total * 100) if kw_total else 0
    job_count = data.get("job_count", len(data.get("job_matches", [])))

    # Arc math: full arc = 251.2px. dashoffset = 251.2 * (1 - score/100)
    arc_offset = round(251.2 * (1 - ats_score / 100))

    label_colors = {
        "Needs Work": ("#E24B4A", "#FCEBEB"),
        "Fair": ("#EF9F27", "#FAEEDA"),
        "Good": ("#1D9E75", "#E1F5EE"),
        "Excellent": ("#178a62", "#d0f0e4"),
    }
    label_fg, label_bg = label_colors.get(ats_label, ("#1D9E75", "#E1F5EE"))

    fmt_color = "#E24B4A" if formatting_issues > 3 else "#EF9F27" if formatting_issues > 1 else "#1D9E75"
    quant_color = "#E24B4A" if quantified < 3 else "#EF9F27" if quantified < 6 else "#1D9E75"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1"/>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&display=swap" rel="stylesheet"/>
<style>
  *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'DM Sans', system-ui, sans-serif;
    background: #0f0f14;
    color: #e0e0ee;
    padding: 20px;
    min-height: 100vh;
  }}

  /* ── Stat row ── */
  .stat-row {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-bottom: 16px;
  }}
  .stat-card {{
    background: #1a1a24;
    border: 1px solid #2a2a3a;
    border-radius: 14px;
    padding: 14px 16px;
  }}
  .stat-label {{ font-size: 11px; color: #666; letter-spacing: .04em; text-transform: uppercase; margin-bottom: 6px; }}
  .stat-val {{ font-size: 22px; font-weight: 600; color: #e8e8f0; line-height: 1; }}
  .stat-val span {{ font-size: 13px; font-weight: 400; color: #666; }}
  .stat-sub {{ font-size: 11px; color: #555; margin-top: 4px; }}
  .up {{ color: #1D9E75; }}

  /* ── Cards ── */
  .card {{
    background: #1a1a24;
    border: 1px solid #2a2a3a;
    border-radius: 16px;
    padding: 18px 20px;
  }}
  .card-title {{ font-size: 14px; font-weight: 600; color: #e0e0ee; margin-bottom: 3px; }}
  .card-sub {{ font-size: 12px; color: #555; margin-bottom: 16px; }}

  /* ── Mid row ── */
  .mid-row {{
    display: grid;
    grid-template-columns: 1fr 260px;
    gap: 12px;
    margin-bottom: 12px;
  }}

  /* ── Skill bars ── */
  .skill-row {{ display: flex; align-items: center; gap: 10px; margin-bottom: 11px; }}
  .skill-label {{ font-size: 12px; color: #888; width: 120px; flex-shrink: 0; }}
  .bar-bg {{ flex: 1; height: 7px; background: #2a2a3a; border-radius: 4px; overflow: hidden; }}
  .bar-fill {{ height: 100%; border-radius: 4px; width: 0; transition: width 1.1s cubic-bezier(.4,0,.2,1); }}
  .skill-score {{ font-size: 12px; font-weight: 500; color: #ccc; width: 28px; text-align: right; }}

  /* ── Gauge ── */
  .gauge-wrap {{ display: flex; flex-direction: column; align-items: center; padding: 4px 0 0; }}
  .gauge-val {{ font-size: 36px; font-weight: 700; color: #e8e8f0; margin-top: -14px; }}
  .gauge-badge {{
    font-size: 12px; font-weight: 500;
    padding: 4px 16px; border-radius: 20px;
    background: {label_bg}; color: {label_fg};
    margin-top: 6px;
  }}
  .gauge-note {{ font-size: 11.5px; color: #555; text-align: center; margin-top: 10px; line-height: 1.6; max-width: 200px; }}

  /* ── Bottom row ── */
  .bottom-row {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}

  /* ── Job list ── */
  .job-item {{
    display: flex; justify-content: space-between; align-items: flex-start;
    padding: 11px 0; border-bottom: 1px solid #1e1e2a;
    gap: 10px;
  }}
  .job-item:last-child {{ border-bottom: none; }}
  .job-left {{ flex: 1; min-width: 0; }}
  .job-title {{ font-size: 13px; font-weight: 500; color: #ddd; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
  .job-co {{ font-size: 11px; color: #666; margin-top: 2px; }}
  .job-meta {{ display: flex; gap: 8px; margin-top: 5px; flex-wrap: wrap; }}
  .job-tag {{
    font-size: 10px; padding: 2px 8px; border-radius: 20px;
    background: #1e1e2a; color: #888; border: 1px solid #2a2a3a;
  }}
  .job-salary {{ color: #1D9E75; border-color: #0d2b1a; background: #0a1f12; }}
  .job-right {{ display: flex; flex-direction: column; align-items: flex-end; gap: 6px; flex-shrink: 0; }}
  .match-pill {{ font-size: 11px; padding: 3px 10px; border-radius: 20px; font-weight: 600; }}
  .match-high {{ background: #0d2b1a; color: #1D9E75; }}
  .match-mid  {{ background: #2b1f08; color: #EF9F27; }}
  .match-low  {{ background: #2b0d0d; color: #E24B4A; }}
  .apply-btn {{
    font-size: 10px; padding: 3px 10px; border-radius: 6px;
    background: transparent; color: #378ADD;
    border: 1px solid #1a3a5a; cursor: pointer;
    text-decoration: none; display: inline-block;
    transition: background .15s;
  }}
  .apply-btn:hover {{ background: #0d1f33; }}

  /* ── Impact metrics ── */
  .impact-row {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 9px 0; border-bottom: 1px solid #1e1e2a;
    font-size: 13px; color: #aaa;
  }}
  .impact-row:last-child {{ border-bottom: none; }}
  .impact-val {{ font-weight: 600; color: #ddd; }}

  /* ── Keywords ── */
  .kw-section-label {{ font-size: 11px; color: #555; margin: 12px 0 6px; text-transform: uppercase; letter-spacing: .04em; }}
  .kw-row {{ display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; }}
  .kw {{
    font-size: 11px; padding: 4px 10px; border-radius: 20px;
    border: 1px solid transparent; font-weight: 500;
  }}
  .kw.found {{ background: #0d2b1a; color: #1D9E75; }}
  .kw.miss  {{ background: #2b0d0d; color: #E24B4A; }}

  @media (max-width: 600px) {{
    .stat-row {{ grid-template-columns: repeat(2, 1fr); }}
    .mid-row, .bottom-row {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<!-- Top stat row -->
<div class="stat-row">
  <div class="stat-card">
    <div class="stat-label">ATS score</div>
    <div class="stat-val">{ats_score}<span>/100</span></div>
    <div class="stat-sub">{ats_label}</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Keywords matched</div>
    <div class="stat-val">{kw_found_count}<span>/{kw_total}</span></div>
    <div class="stat-sub">{kw_pct}% coverage</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Job matches</div>
    <div class="stat-val">{job_count}</div>
    <div class="stat-sub">roles found</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Bullet quality</div>
    <div class="stat-val">{bullet_quality}<span>/10</span></div>
    <div class="stat-sub">use XYZ format</div>
  </div>
  <div class="stat-card">
    <div class="stat-label">Word count</div>
    <div class="stat-val">{word_count}</div>
    <div class="stat-sub">ideal: 400–600</div>
  </div>
</div>

<!-- Mid row: skill bars + gauge -->
<div class="mid-row">
  <div class="card">
    <div class="card-title">Skill strength by field</div>
    <div class="card-sub">How your resume scores across key competency areas</div>
    <div id="skills-area"></div>
  </div>
  <div class="card">
    <div class="card-title">ATS format rating</div>
    <div class="card-sub">Applicant tracking system compatibility</div>
    <div class="gauge-wrap">
      <svg width="210" height="120" viewBox="0 0 210 120"
           role="img" aria-label="ATS compatibility gauge showing {ats_score} out of 100">
        <title>ATS Score: {ats_score}/100</title>
        <defs>
          <linearGradient id="arcGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%"   stop-color="#E24B4A"/>
            <stop offset="38%"  stop-color="#EF9F27"/>
            <stop offset="72%"  stop-color="#1D9E75"/>
            <stop offset="100%" stop-color="#0f6e50"/>
          </linearGradient>
        </defs>
        <!-- Track -->
        <path d="M25,108 A80,80 0 0,1 185,108"
              fill="none" stroke="#2a2a3a" stroke-width="13" stroke-linecap="round"/>
        <!-- Fill -->
        <path d="M25,108 A80,80 0 0,1 185,108"
              fill="none" stroke="url(#arcGrad)" stroke-width="13" stroke-linecap="round"
              stroke-dasharray="251.2" stroke-dashoffset="{arc_offset}"
              id="arcFill"/>
        <!-- Score text -->
        <text x="105" y="98" text-anchor="middle"
              font-size="34" font-weight="700" fill="#e8e8f0"
              font-family="DM Sans, sans-serif">{ats_score}</text>
        <text x="105" y="113" text-anchor="middle"
              font-size="11" fill="#555"
              font-family="DM Sans, sans-serif">out of 100</text>
      </svg>
      <div class="gauge-badge">{ats_label}</div>
      <div class="gauge-note">{percentile_note}</div>
    </div>
  </div>
</div>

<!-- Bottom row: jobs + keyword check -->
<div class="bottom-row">
  <div class="card">
    <div class="card-title">Job recommendations</div>
    <div class="card-sub">Roles matching your resume profile</div>
    <div id="jobs-area"></div>
  </div>
  <div class="card">
    <div class="card-title">Resume health check</div>
    <div class="card-sub">Key quality signals from your resume</div>
    <div class="impact-row">
      <span>Section completeness</span>
      <span class="impact-val">{section_comp}/10</span>
    </div>
    <div class="impact-row">
      <span>Formatting issues</span>
      <span class="impact-val" style="color:{fmt_color}">{formatting_issues} found</span>
    </div>
    <div class="impact-row">
      <span>Action verbs used</span>
      <span class="impact-val">{action_verbs}</span>
    </div>
    <div class="impact-row">
      <span>Quantified bullets</span>
      <span class="impact-val" style="color:{quant_color}">{quantified}/{total_bullets}</span>
    </div>
    <div class="kw-section-label">Keywords found</div>
    <div class="kw-row" id="kw-found"></div>
    <div class="kw-section-label">Keywords missing</div>
    <div class="kw-row" id="kw-miss"></div>
  </div>
</div>

<script>
const skills = {skills_json};
const jobs   = {jobs_json};
const kwFound  = {keywords_found_json};
const kwMissing = {keywords_missing_json};

// ── Render skill bars ──────────────────────────────────────────────────────
const sa = document.getElementById('skills-area');
skills.forEach(s => {{
  sa.innerHTML += `
    <div class="skill-row">
      <div class="skill-label">${{s.name}}</div>
      <div class="bar-bg">
        <div class="bar-fill" data-w="${{s.score}}" style="background:${{s.color || '#378ADD'}}"></div>
      </div>
      <div class="skill-score">${{s.score}}</div>
    </div>`;
}});

// ── Render jobs ────────────────────────────────────────────────────────────
const ja = document.getElementById('jobs-area');
if (!jobs || jobs.length === 0) {{
  ja.innerHTML = '<div style="color:#555;font-size:13px;padding:20px 0;">No jobs found. Check your JSearch API key in .env</div>';
}} else {{
  jobs.forEach(j => {{
    const cls = j.match_pct >= 80 ? 'match-high' : j.match_pct >= 60 ? 'match-mid' : 'match-low';
    const salaryTag = j.salary ? `<span class="job-tag job-salary">${{j.salary}}</span>` : '';
    const typeTag = j.job_type ? `<span class="job-tag">${{j.job_type}}</span>` : '';
    const postedTag = j.posted ? `<span class="job-tag">${{j.posted}}</span>` : '';
    const applyBtn = j.apply_link
      ? `<a class="apply-btn" href="${{j.apply_link}}" target="_blank">Apply ↗</a>`
      : '';
    const matchBadge = j.match_pct > 0
      ? `<span class="match-pill ${{cls}}">${{j.match_pct}}% match</span>`
      : '';
    ja.innerHTML += `
      <div class="job-item">
        <div class="job-left">
          <div class="job-title">${{j.title}}</div>
          <div class="job-co">${{j.company}} · ${{j.location}}</div>
          <div class="job-meta">${{salaryTag}}${{typeTag}}${{postedTag}}</div>
        </div>
        <div class="job-right">
          ${{matchBadge}}
          ${{applyBtn}}
        </div>
      </div>`;
  }});
}}

// ── Render keywords ────────────────────────────────────────────────────────
const kf = document.getElementById('kw-found');
const km = document.getElementById('kw-miss');
kwFound.slice(0, 10).forEach(k => {{
  kf.innerHTML += `<span class="kw found">${{k}}</span>`;
}});
kwMissing.slice(0, 8).forEach(k => {{
  km.innerHTML += `<span class="kw miss">${{k}}</span>`;
}});

// ── Animate bars on load ───────────────────────────────────────────────────
requestAnimationFrame(() => {{
  setTimeout(() => {{
    document.querySelectorAll('.bar-fill').forEach(el => {{
      el.style.width = el.dataset.w + '%';
    }});
  }}, 120);
}});
</script>
</body>
</html>"""
    return html