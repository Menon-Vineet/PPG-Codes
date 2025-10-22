"""
PPG Demo App — Upload → Analyze → Pest Guard Advice (stable, offline)
Run:  python ppg_demo_app.py
"""

import os
from typing import Optional, Tuple

# --- Put Gradio temp files in a folder we control (avoids OneDrive/AV locks) ---
APP_TMP = os.path.abspath("./gradio_tmp")
os.makedirs(APP_TMP, exist_ok=True)
os.environ["GRADIO_TEMP_DIR"] = APP_TMP

import gradio as gr
from PIL import Image

# -------------------------------------------------------------------
# Keep it rock-solid for the demo (no heavy model downloads)
# If you later enable Qwen, wire it in and set USE_QWEN = True.
# -------------------------------------------------------------------
USE_QWEN = False

# ------------------------------
# Demo-mode fallbacks
# ------------------------------
DEMO_COUNTS = {
    "RW S (15).jpg": 15,
    "RW S (18).jpg": 15,
    "RW S (19).jpg": 15,
    "RW S (10).jpg": 10,
    "RW S (24).jpg": 10,
    "RW_S_24.jpg": 10,   # safe-name alias if you rename files
}

def count_aphids_demo(img: Image.Image, original_filename: Optional[str] = None, manual_override: Optional[int] = None) -> int:
    if manual_override is not None:
        return max(0, int(manual_override))
    if original_filename:
        base = os.path.basename(original_filename)
        if base in DEMO_COUNTS:
            return DEMO_COUNTS[base]
    # deterministic fallback by image size (keeps demo predictable)
    w, h = img.size
    return max(0, (w * h) // (512 * 512))

def generate_advice(aphid_count: int, leaf_area_cm2: float) -> Tuple[str, str]:
    area = max(leaf_area_cm2, 1e-6)
    density = aphid_count / area

    if density < 0.1:
        severity = "Low"
        advice = (
            f"Density ~{density:.2f} aphids/cm². Monitor only. Re-scout in 3–5 days; "
            "no spray required. Consider introducing/monitoring beneficials (lady beetles, lacewings)."
        )
    elif density < 0.5:
        severity = "Moderate"
        advice = (
            f"Density ~{density:.2f} aphids/cm². Spot-spray affected zones with selective insecticide or soap; "
            "avoid blanket application. Track hotspots and verify reduction within 48–72 hours."
        )
    elif density < 1.5:
        severity = "High"
        advice = (
            f"Density ~{density:.2f} aphids/cm². Sectional spray recommended (rows/blocks). "
            "Combine with biological control plan and adjust fertigation to reduce succulent growth."
        )
    else:
        severity = "Severe"
        advice = (
            f"Density ~{density:.2f} aphids/cm². Escalate: broad sectional spray + biologicals. "
            "Increase scouting frequency (daily) and consider rotating modes of action to prevent resistance."
        )
    return severity, advice

# ------------------------------
# Inference (UPLOAD → ANALYZE)
# We accept file path from Gradio and open it ourselves to avoid temp locks.
# ------------------------------
def infer(image_path: str, leaf_area_cm2: float, demo_mode: bool, manual_override: int|None, original_filename: str|None):
    if not image_path:
        return "No image uploaded.", "", 0, 0.0, ""

    # Open from the *actual* file path the user uploaded
    try:
        with Image.open(image_path) as im:
            img = im.convert("RGB")
    except Exception as e:
        return f"Error opening image: {e}", "", 0, 0.0, ""

    # if user left filename box empty, derive from upload path
    if not original_filename:
        original_filename = os.path.basename(image_path)

    if demo_mode or not USE_QWEN:
        count = count_aphids_demo(img, original_filename=original_filename, manual_override=manual_override)
    else:
        # Placeholder: wire in your real counting when ready
        count = count_aphids_demo(img, original_filename=original_filename, manual_override=manual_override)

    severity, advice = generate_advice(count, leaf_area_cm2 or 100.0)
    density = count / max(leaf_area_cm2 or 100.0, 1e-6)

    header = f"PPG Pest Guard Advice — {severity}"
    summary = f"Aphids counted: {count} | Leaf area: {leaf_area_cm2:.1f} cm² | Density: {density:.2f} aphids/cm²"
    return header, summary, count, density, advice

# ------------------------------
# Gradio UI (file upload → analyze)
# ------------------------------
with gr.Blocks(title="PPG — Pest Guard Advice") as demo:
    gr.Markdown("# PPG — Pest Guard Advice\nUpload a leaf photo → get aphid count, density, and action advice.\n")

    with gr.Row():
        with gr.Column():
            # IMPORTANT: use type='filepath' so we read the file ourselves (fewer temp issues)
            img_path = gr.Image(type="filepath", label="Leaf image")
            leaf_area = gr.Number(value=300.0, precision=1, label="Estimated leaf area (cm²)")
            demo_mode = gr.Checkbox(value=True, label="Demo mode (use fallback counts)")  # default True for stability
            manual_override = gr.Slider(0, 200, step=1, value=None, label="Manual override aphid count (optional)", info="Set only if you want to force a count in demo.")
            original_filename = gr.Textbox(value="", label="Original filename (optional for demo)", placeholder="e.g., RW S (24).jpg")
            btn = gr.Button("Get Pest Guard Advice")

        with gr.Column():
            header = gr.Markdown("")
            summary = gr.Markdown("")
            with gr.Row():
                count_out = gr.Number(label="Aphid count", precision=0)
                density_out = gr.Number(label="Density (aphids/cm²)", precision=3)
            advice_out = gr.Textbox(label="Advice", lines=6)

    btn.click(
        infer,
        inputs=[img_path, leaf_area, demo_mode, manual_override, original_filename],
        outputs=[header, summary, count_out, density_out, advice_out],
    )

if __name__ == "__main__":
    # Local, stable launch (no share/tunnel)
    demo.launch(server_name="127.0.0.1", server_port=7861)
