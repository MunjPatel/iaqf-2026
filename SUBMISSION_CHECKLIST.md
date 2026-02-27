# Submission Checklist

Use this checklist before submitting to **competition@IAQF.org** by **Friday, February 27, 2026, 5pm EST**.

---

## What to Submit (3 items)

### 1. Solution PDF

- File: `paper/main.pdf`
- **Max 10 pages**, single-sided, Times New Roman 12pt
- **No identifying information** (no school name, student names, team name)
- All figures, tables, and formulas must fit in these 10 pages

To build:
```
cd paper
pdflatex main.tex
pdflatex main.tex
```

### 2. Code Addendum (ZIP file)

Create a ZIP of this folder **excluding** the `.git` directory (which contains commit history with names).

**Include in the ZIP:**
- `INSTRUCTIONS.txt` (reproduction steps for judges)
- `run_all.py`, `config.yaml`, `requirements.txt`
- `src/` folder (all Python code)
- `paper/` folder (LaTeX source, tables)
- `scripts/` folder
- `data/supplementary/` (news_events.csv if present)

**Exclude from the ZIP:**
- `.git/` folder (contains your name/email in commits)
- `.venv/` folder (judges will create their own)
- `data/raw/`, `data/clean/`, `data/derived/` (generated at runtime)
- `results/` (generated at runtime)
- `__pycache__/` folders
- `paper/main.pdf` (submitted separately)
- This `SUBMISSION_CHECKLIST.md` (internal use only)
- `README.md` (replaced by INSTRUCTIONS.txt for submission)

**How to create the ZIP (Windows PowerShell):**
```powershell
# from project root
Compress-Archive -Path config.yaml, requirements.txt, run_all.py, INSTRUCTIONS.txt, src, paper, scripts, data\supplementary -DestinationPath code_addendum.zip
```

**How to create the ZIP (macOS/Linux):**
```bash
zip -r code_addendum.zip config.yaml requirements.txt run_all.py INSTRUCTIONS.txt src/ paper/ scripts/ data/supplementary/ -x "*.pyc" -x "*__pycache__*"
```

### 3. Team Submission Sheet

- Use the official IAQF form
- Fill in: team captain, all members, faculty overseer, program name
- This is the **only document** where your names and school appear

---

## Pre-Submission Checklist

- [ ] Solution PDF is **10 pages or fewer**
- [ ] Solution PDF has **no mention** of school, students, or team name
- [ ] Code ZIP **does not include `.git/`** folder
- [ ] Code ZIP includes `INSTRUCTIONS.txt` with reproduction steps
- [ ] Team submission sheet is filled out completely
- [ ] All 3 items attached to email
- [ ] Email sent to **competition@IAQF.org**
- [ ] Sent **before 5pm EST on Feb 27, 2026**

---

## After Submitting

- You should receive a confirmation of receipt from IAQF
- If you don't receive confirmation within 24 hours, follow up

---

## Competition Rules Summary

| Requirement | Status |
|-------------|--------|
| Max 10 pages, single-sided | Paper is ~9 pages |
| Times New Roman 12pt | Set in main.tex |
| No identifying info in solution | Verified (no names/school) |
| Code as separate addendum | ZIP file, not in 10 pages |
| Team submission sheet included | Separate document |
| Deadline: Feb 27, 2026, 5pm EST | Before deadline |
