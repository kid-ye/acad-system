# Migrate the backend to Hugging Face Spaces (free, no card)

Moves `paperbank-api` off Google Cloud Run (~₹290/mo) to a free HF Docker Space.
No credit card and no international payments are needed for a free CPU Space.

What stays the same: the frontend on Cloudflare, the PDFs on HF, the search and
chat behaviour. What changes: where the backend runs and the URL the frontend
calls.

Files for this migration live in `hf-space/` (a `Dockerfile` and `README.md`)
plus this runbook.

---

## 0. Prerequisites
- A free Hugging Face account (https://huggingface.co/join). No card.
- The CLI: `pip install -U huggingface_hub`, then `huggingface-cli login` (paste a
  token from https://huggingface.co/settings/tokens, "write" scope).
- Your `DERIVED_DATA/` folder locally: `questions_v2.db`, `papers_v2.db`,
  `embeddings.npy`, `emb_keys.json`, `figures/`. (The ONNX model is built in the
  image, so it does not go in the dataset.)

## 1. Upload the data to a HF dataset (once)
The data is public exam content, so a public dataset is fine (no token needed at
build).

```bash
# create + upload in one go (repo is created if missing)
huggingface-cli upload kid-ye/acad-data ./DERIVED_DATA . \
  --repo-type=dataset --exclude "bge-onnx/*"
```

Confirm it lists the 4 files + `figures/` at
https://huggingface.co/datasets/kid-ye/acad-data. If you pick a different name,
edit the `ARG HF_DATA_REPO` default in `hf-space/Dockerfile`.

## 2. Create the Space
Web UI: New → Space → **Docker** SDK → name it (e.g. `pyqheaven-backend`),
Hardware = **CPU basic (free)**. Or CLI:

```bash
huggingface-cli repo create pyqheaven-backend --type space --space_sdk docker
```

## 3. Push the app to the Space
The Space is its own git repo. Put the backend + the HF Dockerfile/README in it:

```bash
git clone https://huggingface.co/spaces/kid-ye/pyqheaven-backend hf-space-repo
cd hf-space-repo

# copy from your project checkout:
cp -r <project>/backend .
cp <project>/requirements.txt <project>/requirements-export.txt .
mkdir -p scripts && cp <project>/scripts/export_onnx.py scripts/
cp <project>/hf-space/Dockerfile .
cp <project>/hf-space/README.md .

git add -A && git commit -m "deploy backend to HF Space" && git push
```

HF builds automatically. Watch the build logs in the Space UI. First build runs
the ONNX export (a few minutes).

## 4. Set the Space secrets
Space → Settings → **Variables and secrets**. Add (as *secrets*, not variables):
- `OPEN_AI_API_KEY` (or `LLM_API_KEY` + `LLM_BASE_URL` + `CHAT_MODEL` if you use
  Groq/Gemini — same values you have on Cloud Run now)
- `CORS_ORIGINS` = `https://pyqheaven.in`
- `PDF_BASE_URL` = your existing HF PDFs base URL
- `API_BASE_URL` = `https://kid-ye-pyqheaven-backend.hf.space` (your Space URL)

Re-build (Settings → Factory reboot) so the secrets take effect.

## 5. Verify the Space
```bash
curl https://kid-ye-pyqheaven-backend.hf.space/api/health
# {"status":"ok","questions":<n>,"semantic_loaded":true/false}
```
Then hit `/api/search?q=laplace` and `/api/search/semantic?q=deadlock` and
confirm results come back.

## 6. Point the frontend at the Space
In the frontend's build env (Cloudflare Pages/Worker settings), set
`VITE_API_URL=https://kid-ye-pyqheaven-backend.hf.space` and redeploy. Confirm
`CORS_ORIGINS` on the Space includes the frontend's origin (step 4).

## 7. Decommission Cloud Run (stop the bill)
Once the Space serves the live frontend:
```bash
gcloud run services delete paperbank-api --region=us-central1 --project=bmsce-503918
```
Also delete old images in Artifact Registry (the bulk of the ₹290 storage) and,
if nothing else uses the project, disable billing on it.

---

## Notes / caveats
- **Sleeps when idle.** A free Space pauses after ~48h of no traffic and wakes on
  the next request. The wake is fast now (ONNX loads in seconds, no torch), but
  the very first visitor after a long idle waits a few seconds. $0 for that.
- **Private data?** If you ever make the dataset private, add `HF_TOKEN` as a
  build secret and pass it to `snapshot_download`. Public needs nothing.
- **Rollback** is trivial: the Cloud Run service and image are untouched until
  step 7, so you can keep both running during cutover and only delete Cloud Run
  once the Space is proven.
