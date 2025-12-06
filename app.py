# app.py
# Sort Dash — Bubble Sort Learning Game (complete)
# - Tutorial (play/pause/next/prev/speed)
# - Practice (enforces bubble-sort rules + feedback)
# - Prediction (hint + fair % scoring)
# - Swap sound, highlighting gradients, capped bar heights, progress + badges
#
# Author: Justin Duggan
# AI-assisted [Level 4]: ChatGPT (GPT-5 Thinking mini)
# Compatible with Gradio 6.x
# ----------------------------------------------------------------------------

import gradio as gr
import random
import time
from typing import List, Tuple, Dict, Optional
from datetime import datetime
import html

# ---------------------------
# Algorithm utilities
# ---------------------------
def bubble_sort_steps(arr: List[int]) -> Tuple[List[List[int]], List[Tuple[int,int]], List[Optional[int]]]:
    """
    Return (frames, swap_pairs, bubbling_index):
      - frames: array states (initial + after each comparison)
      - swap_pairs: (i,j) if a swap occurred for that frame, else (-1,-1)
      - bubbling_index: for each frame, which index is 'bubbling' (largest unsorted)
    """
    a = arr.copy()
    n = len(a)
    frames = [a.copy()]
    swap_pairs = [(-1, -1)]
    bubbling = [None]
    for i in range(n):
        made_swap = False
        bub_idx = n - i - 1
        for j in range(0, n - i - 1):
            if a[j] > a[j + 1]:
                a[j], a[j + 1] = a[j + 1], a[j]
                frames.append(a.copy())
                swap_pairs.append((j, j + 1))
                bubbling.append(bub_idx)
                made_swap = True
            else:
                frames.append(a.copy())
                swap_pairs.append((-1, -1))
                bubbling.append(bub_idx)
        if not made_swap:
            break
    return frames, swap_pairs, bubbling

def bubble_swap_count(arr: List[int]) -> int:
    _, swaps, _ = bubble_sort_steps(arr)
    return sum(1 for p in swaps if p != (-1, -1))

def is_sorted(arr: List[int]) -> bool:
    return all(arr[i] <= arr[i + 1] for i in range(len(arr) - 1))

# ---------------------------
# HTML visual builder (bars)
# ---------------------------
def bars_html(
    arr: List[int],
    highlight: Tuple[int, int] = (-1, -1),
    bubbling: Optional[int] = None,
    title: str = "",
    max_bar_height: int = 120,
) -> str:
    """Return HTML block showing bars with capped heights and gradient highlights."""
    safe_title = html.escape(title)
    if not arr:
        return f"<div style='color:#e6eef8'>{safe_title}<br/>(empty)</div>"

    max_val = max(arr) if max(arr) > 0 else 1
    css = f"""
    <style>
      .sd-block {{ padding:8px; border-radius:10px; background: linear-gradient(180deg,#071024,#041026); }}
      .sd-bars {{ display:flex; align-items:flex-end; gap:8px; height:{max_bar_height}px; padding:12px 8px 6px 8px; border-radius:8px; }}
      .sd-bar {{ display:flex; flex-direction:column; align-items:center; justify-content:flex-end; width:36px; border-radius:6px; transition: all 0.28s ease; box-shadow: 0 8px 16px rgba(0,0,0,0.6); }}
      .sd-val {{ font-size:12px; margin-top:6px; color:#e6eef8; user-select:none; }}
      .sd-idx {{ font-size:11px; margin-top:4px; color:#ffd966; font-weight:600; user-select:none; }}
      .sd-title {{ font-weight:700; color:#dbeafe; margin-bottom:6px; }}
    </style>
    """
    parts = []
    for idx, v in enumerate(arr):
        height_px = 20 + int((v / max_val) * (max_bar_height - 24))
        # choose gradient colors
        if highlight != (-1, -1) and (idx == highlight[0] or idx == highlight[1]):
            start_c, end_c = "#ff8a8a", "#ff4d4d"   # red gradient for compare/swap
        elif bubbling is not None and idx == bubbling:
            start_c, end_c = "#ffd86b", "#f59e0b"   # yellow gradient for bubbling
        else:
            start_c, end_c = "#60a5fa", "#2563eb"   # blue default
        block = f"""
        <div style="display:flex;flex-direction:column;align-items:center">
          <div class='sd-bar' style="height:{height_px}px; background: linear-gradient(180deg,{start_c},{end_c});"></div>
          <div class='sd-val'>{v}</div>
          <div class='sd-idx'>{idx}</div>
        </div>
        """
        parts.append(block)
    title_html = f"<div class='sd-title'>{safe_title}</div>" if safe_title else ""
    return css + f"<div class='sd-block'>{title_html}<div class='sd-bars'>{''.join(parts)}</div></div>"

# ---------------------------
# Progress bar snippet
# ---------------------------
def progress_html(current: int, total: int) -> str:
    total = max(total, 0)
    pct = 100 if total == 0 else int((current / total) * 100)
    pct = max(0, min(100, pct))
    return f"""
    <div style='width:100%;margin-top:8px'>
      <div style='display:flex;justify-content:space-between;color:#cbd5e1;font-size:12px;margin-bottom:6px;'>
        <div>Progress</div><div>{pct}%</div>
      </div>
      <div style='height:12px;background:#021028;border-radius:8px;'>
        <div style='height:100%;width:{pct}%;background:linear-gradient(90deg,#60a5fa,#7c3aed);border-radius:8px;transition:width:0.3s'></div>
      </div>
    </div>
    """

# ---------------------------
# parsing + helpers
# ---------------------------
def parse_input_list(text: str) -> Tuple[List[int], str]:
    if not text:
        return [], "Input is empty"
    parts = [p for p in text.replace(",", " ").split() if p.strip()]
    try:
        arr = [int(p) for p in parts]
        return arr, "" if arr else ([], "No numbers found")
    except ValueError:
        return [], "Could not parse integers. Use commas or spaces."

def arr_to_text(arr: List[int]) -> str:
    return ", ".join(map(str, arr))

# ---------------------------
# initial state creator
# ---------------------------
def initial_state() -> Dict:
    return {
        "array": [],
        "tutorial_frames": [],
        "tutorial_pairs": [],
        "tutorial_bubbling": [],
        "tutorial_index": 0,
        "tutorial_playing": False,
        # Practice-specific:
        "practice_moves": 0,
        "practice_start": None,
        "practice_index": 0,   # which adjacent pair index we're at (j in inner loop)
        "practice_pass": 0,    # current pass number i
    }

# ---------------------------
# generation & load handlers
# ---------------------------
def cmd_generate_random(length: int, max_val: int, state: Dict):
    arr = [random.randint(1, max_val) for _ in range(length)]
    frames, pairs, bub = bubble_sort_steps(arr)
    state.update({
        "array": arr,
        "tutorial_frames": frames,
        "tutorial_pairs": pairs,
        "tutorial_bubbling": bub,
        "tutorial_index": 0,
        "tutorial_playing": False,
        "practice_moves": 0,
        "practice_start": None,
        "practice_index": 0,
        "practice_pass": 0,
    })
    html = bars_html(arr, (-1, -1), None, title=f"Random array (len={len(arr)})")
    status = "Random array generated. Choose Tutorial, Practice, or Prediction."
    prog = progress_html(0, max(len(frames) - 1, 0))
    return arr_to_text(arr), html, status, prog, state

def cmd_parse_input(text: str, state: Dict):
    arr, err = parse_input_list(text)
    if err:
        return "", f"<div style='color:#ffb4b4'>{err}</div>", "Error", progress_html(0, 0), state
    frames, pairs, bub = bubble_sort_steps(arr)
    state.update({
        "array": arr,
        "tutorial_frames": frames,
        "tutorial_pairs": pairs,
        "tutorial_bubbling": bub,
        "tutorial_index": 0,
        "tutorial_playing": False,
        "practice_moves": 0,
        "practice_start": None,
        "practice_index": 0,
        "practice_pass": 0,
    })
    html = bars_html(arr, (-1, -1), None, title=f"Loaded array (len={len(arr)})")
    status = "Input loaded. Choose a mode."
    prog = progress_html(0, max(len(frames) - 1, 0))
    return arr_to_text(arr), html, status, prog, state

# ---------------------------
# Tutorial helpers: next / prev / reset / play (streaming) / pause
# ---------------------------
def generate_status(idx: int, pair: Tuple[int, int], bub: Optional[int], arr: List[int], total: int) -> str:
    if total <= 0:
        return "<div>No steps — array is trivial / already sorted.</div>"
    if pair != (-1, -1):
        i, j = pair
        return (
            f"<div><b>Step {idx}/{total}</b>: Comparing indices <code>{i}</code> and <code>{j}</code> — "
            f"<code>a[{i}] = {arr[i]}</code> vs <code>a[{j}] = {arr[j]}</code>. <b>Swap</b> because <code>a[{i}] &gt; a[{j}]</code>.<br>"
            "Code-level: this corresponds to <code>if a[j] &gt; a[j+1]: swap</code> in the inner loop. "
            f"Element at bubbling index {bub} is moving to its final position."
            "</div>"
        )
    else:
        return (
            f"<div><b>Step {idx}/{total}</b>: Pair already in order — <b>no swap</b>.<br>"
            "Code-level: the inner loop does not swap, keeping local sorted order.</div>"
        )

def tutorial_reset(state: Dict):
    state["tutorial_index"] = 0
    state["tutorial_playing"] = False
    arr = state.get("array", [])
    frames = state.get("tutorial_frames", [])
    html = bars_html(arr, (-1, -1), None, title="Tutorial reset")
    status = "Tutorial reset. Press Next to step or Play to animate."
    prog = progress_html(0, max(len(frames) - 1, 0))
    return html, status, prog, state

def tutorial_next(state: Dict):
    # auto-pause
    state["tutorial_playing"] = False
    frames = state.get("tutorial_frames", [])
    pairs = state.get("tutorial_pairs", [])
    bub = state.get("tutorial_bubbling", [])
    if not frames:
        return "<div>(no array)</div>", "Load/generate an array", progress_html(0, 0), state
    idx = min(state.get("tutorial_index", 0) + 1, len(frames) - 1)
    state["tutorial_index"] = idx
    arr = frames[idx]
    pair = pairs[idx] if idx < len(pairs) else (-1, -1)
    bubbling = bub[idx] if idx < len(bub) else None
    status_html = generate_status(idx, pair, bubbling, arr, len(frames) - 1)
    visual_html = bars_html(arr, pair, bubbling, title=f"Tutorial step {idx}")
    if pair != (-1, -1):
        visual_html += "<script>playSwap();</script>"
    prog = progress_html(idx, len(frames) - 1)
    return visual_html, status_html, prog, state

def tutorial_prev(state: Dict):
    state["tutorial_playing"] = False
    frames = state.get("tutorial_frames", [])
    pairs = state.get("tutorial_pairs", [])
    bub = state.get("tutorial_bubbling", [])
    if not frames:
        return "<div>(no array)</div>", "Load/generate an array", progress_html(0, 0), state
    idx = max(state.get("tutorial_index", 0) - 1, 0)
    state["tutorial_index"] = idx
    arr = frames[idx]
    pair = pairs[idx] if idx < len(pairs) else (-1, -1)
    bubbling = bub[idx] if idx < len(bub) else None
    status_html = generate_status(idx, pair, bubbling, arr, len(frames) - 1)
    visual_html = bars_html(arr, pair, bubbling, title=f"Tutorial step {idx}")
    prog = progress_html(idx, len(frames) - 1)
    return visual_html, status_html, prog, state

def tutorial_play(state: Dict, delay: float):
    """
    Streaming generator that respects state['tutorial_playing'] and can be paused by setting it False.
    Delay is passed in so slider changes affect subsequent frames.
    """
    frames = state.get("tutorial_frames", [])
    pairs = state.get("tutorial_pairs", [])
    bub = state.get("tutorial_bubbling", [])
    if not frames:
        yield "<div>(no array)</div>", "Load/generate an array", progress_html(0, 0), state
        return
    state["tutorial_playing"] = True
    idx = state.get("tutorial_index", 0)
    total = len(frames) - 1
    while idx <= total and state.get("tutorial_playing", False):
        state["tutorial_index"] = idx
        arr = frames[idx]
        pair = pairs[idx] if idx < len(pairs) else (-1, -1)
        bubbling = bub[idx] if idx < len(bub) else None
        status_html = generate_status(idx, pair, bubbling, arr, total)
        visual_html = bars_html(arr, pair, bubbling, title=f"Tutorial step {idx}")
        if pair != (-1, -1):
            visual_html += "<script>playSwap();</script>"
        yield visual_html, status_html, progress_html(idx, total), state
        # respect dynamic delay slider value by reading function param; speed changes will take effect next frame
        time.sleep(delay)
        # check if paused has been set by a button callback; tutorial_play uses tutorial_playing flag
        idx += 1
    state["tutorial_playing"] = False

# Pause handler (explicit)
def tutorial_pause(state: Dict):
    state["tutorial_playing"] = False
    arr = state.get("array", [])
    idx = state.get("tutorial_index", 0)
    frames = state.get("tutorial_frames", [])
    prog = progress_html(idx, max(len(frames) - 1, 0))
    return bars_html(arr), "<div>Paused</div>", prog, state

# ---------------------------
# Practice mode (enforce bubble-sort rules)
# ---------------------------
def practice_start(state: Dict):
    state["practice_moves"] = 0
    state["practice_start"] = datetime.now().timestamp()
    state["practice_index"] = 0
    state["practice_pass"] = 0
    return "Practice started — follow Bubble Sort rules. You will be shown the current pair; press Swap if left>right, otherwise press Next.", state

def practice_swap_current(state: Dict):
    """
    Attempt swap at current practice_index (j). Only allowed if arr[j] > arr[j+1].
    After swap, advance to next pair. If at end of pass, advance to next pass (reset index).
    """
    arr = state.get("array", []).copy()
    n = len(arr)
    j = state.get("practice_index", 0)
    i = state.get("practice_pass", 0)
    # compute last index allowed this pass: n - i - 2 (since pair is j and j+1)
    if n == 0:
        return "<div>(no array)</div>", "Load or generate an array first.", state
    max_j = n - i - 2
    if j > max_j:
        # end of pass
        state["practice_index"] = 0
        state["practice_pass"] = i + 1
        return bars_html(arr), f"End of pass {i}. Moving to pass {i+1}.", state
    left, right = arr[j], arr[j + 1]
    if left <= right:
        # not allowed to swap
        visual_html = bars_html(arr, highlight=(j, j + 1), bubbling=None, title=f"Practice pair ({j},{j+1})")
        msg = (
            f"❌ Cannot swap: a[{j}] = {left} ≤ a[{j+1}] = {right}. "
            "Bubble Sort rule: swap only when left > right. Use Next to advance."
        )
        return visual_html, msg, state
    # perform allowed swap
    arr[j], arr[j + 1] = arr[j + 1], arr[j]
    state["array"] = arr
    state["practice_moves"] = state.get("practice_moves", 0) + 1
    # advance index
    state["practice_index"] = j + 1
    # if we've reached the end of the pass, move to next pass and reset index
    if state["practice_index"] > max_j:
        state["practice_index"] = 0
        state["practice_pass"] = i + 1
    visual_html = bars_html(arr, highlight=(j, j + 1), bubbling=None, title=f"Practice move #{state['practice_moves']}")
    visual_html += "<script>playSwap();</script>"
    msg = f"✔ Swapped indices ({j},{j+1}) because {left} > {right}."
    return visual_html, msg, state

def practice_next_pair(state: Dict):
    """Advance to next pair (without swapping), following bubble sort inner loop order."""
    arr = state.get("array", []).copy()
    n = len(arr)
    i = state.get("practice_pass", 0)
    j = state.get("practice_index", 0)
    max_j = n - i - 2
    if n == 0:
        return "<div>(no array)</div>", "Load array first.", state
    if j >= max_j:
        # end of pass
        state["practice_index"] = 0
        state["practice_pass"] = i + 1
        return bars_html(arr), f"End of pass {i}. Moving to pass {i+1}.", state
    else:
        state["practice_index"] = j + 1
        new_j = state["practice_index"]
        visual = bars_html(arr, highlight=(new_j, new_j + 1), bubbling=None, title=f"Practice pair ({new_j},{new_j+1})")
        msg = f"Now comparing pair ({new_j},{new_j+1}). If a[{new_j}] > a[{new_j+1}], press Swap."
        return visual, msg, state

def practice_check(state: Dict):
    arr = state.get("array", [])
    if is_sorted(arr):
        moves = state.get("practice_moves", 0)
        elapsed = 0.0
        if state.get("practice_start"):
            elapsed = datetime.now().timestamp() - state["practice_start"]
        # optimal (may be computed on original array; here we approximate on current)
        optimal = bubble_swap_count(arr)
        score = max(0, int(100 - 5 * abs(moves - optimal)))
        badge = f"<div style='display:inline-block;padding:8px;border-radius:8px;background:linear-gradient(90deg,#10b981,#06b6d4);color:white;font-weight:700'>Practice Score: {score}/100</div>"
        return f"Sorted ✔ Moves: {moves}. Optimal: {optimal}. Time: {elapsed:.1f}s<br/>{badge}", state
    else:
        # show current pair to guide user
        j = state.get("practice_index", 0)
        return f"Not sorted yet. Current pair: ({j},{j+1}). Follow the rule: swap only when left > right.", state

# ---------------------------
# Prediction: hint + percent scoring
# ---------------------------
def prediction_hint(state: Dict):
    arr = state.get("array", [])
    if not arr:
        return "Load an array first."
    # generic hint: inversion count idea (conceptual)
    return (
        "Hint: Count how many times a larger number appears before a smaller number (inversions). "
        "Each inversion roughly corresponds to one swap in Bubble Sort. Try estimating inversions."
    )

def prediction_run(state: Dict, guess: int):
    arr = state.get("array", [])
    if not arr:
        return "No array loaded.", gr.update(value=0), "<div>Load/generate an array first.</div>", state
    actual = bubble_swap_count(arr)
    # score by relative difference (percentage accuracy)
    # accuracy = max(0, 100 * (1 - abs(guess-actual)/max(actual, guess, 1)))
    # use symmetrical scaling:
    if actual == 0 and guess == 0:
        accuracy = 100
    else:
        accuracy = max(0, int(100 * (1 - (abs(guess - actual) / max(actual, guess, 1)))))
    msg = f"Your guess: {guess}. Actual swaps: {actual}. Accuracy: {accuracy}%."
    badge = f"<div style='display:inline-block;padding:8px;border-radius:8px;background:linear-gradient(90deg,#f97316,#f43f5e);color:white;font-weight:700'>Prediction Score: {accuracy}/100</div>"
    final_html = bars_html(sorted(arr), highlight=(-1, -1), bubbling=None, title="Final sorted array")
    return msg + "<br/>" + badge, gr.update(value=0), final_html, state

# ---------------------------
# Build the Gradio UI (Gradio 6.x compatible)
# ---------------------------
with gr.Blocks() as demo:
    # header & swap audio
    gr.HTML(f"""
      <div style='text-align:center;padding:10px 0'>
        <h1 style='margin:0;color:#7dd3fc'>🔵 Sort Dash — Bubble Sort Learning Game</h1>
        <div style='color:#c7d2fe;margin-top:6px'>Tutorial • Practice • Prediction — learn by visualizing and following rules</div>
        <div style='color:#FFFFFF;margin-top:6px'>Created by Justin Duggan</div>
      </div>
    """)

    # application state stored in a component
    state = gr.State(initial_state())

    # left column: input/generate + instructions
    with gr.Row():
        with gr.Column(scale=2):
            gr.Markdown("### Input / Generate")
            input_text = gr.Textbox(label="Enter numbers (comma or space separated)", placeholder="e.g. 5, 3, 9, 1, 6", lines=1)
            with gr.Row():
                gen_len = gr.Slider(3, 16, value=8, step=1, label="Random array length")
                gen_max = gr.Slider(5, 60, value=20, step=1, label="Random max value")
            gen_btn = gr.Button("Generate random array")
            load_btn = gr.Button("Use input array")
            gr.Markdown(
                """
                **How to use**<br/>
                • Generate an array or paste one into the input box and click *Use input array*.<br/>
                • Tutorial: step through or Play to see Bubble Sort in action. Speed adjustable while playing.<br/>
                • Practice: you must follow Bubble Sort rules (only swap adjacent elements when left > right); the UI will guide you.<br/>
                • Prediction: guess how many swaps Bubble Sort will take; use Hint if needed.
                """
            )
        with gr.Column(scale=3):
            gr.Markdown("### Current Array & Visualization")
            array_text = gr.Textbox(label="Current array", interactive=False)
            visual = gr.HTML("<div>(visualization)</div>")
            status = gr.HTML("<div style='color:#cbd5e1'>Status / Info will appear here</div>")
            prog = gr.HTML(progress_html(0, 0))

    gr.Markdown("---")

    with gr.Tabs():
        with gr.TabItem("Tutorial"):
            gr.Markdown("**Tutorial mode** — step through Bubble Sort or autoplay. Adjust speed while it runs.")
            with gr.Row():
                prev_btn = gr.Button("◀ Prev")
                next_btn = gr.Button("Next ▶")
                reset_btn = gr.Button("Reset")
                play_btn = gr.Button("Play ▶")
                pause_btn = gr.Button("Pause ⏸")
                play_delay = gr.Slider(0.05, 1.2, value=0.45, step=0.05, label="Play speed (seconds)")
            tut_status = gr.HTML("<div>Tutorial status will appear here.</div>")

        with gr.TabItem("Practice"):
            gr.Markdown("**Practice mode** — guided bubble-sort steps: you see the current pair; swap only when left > right.")
            with gr.Row():
                start_prac = gr.Button("Start Practice")
                swap_curr = gr.Button("Swap (if allowed)")
                next_pair = gr.Button("Next pair")
                check_prac = gr.Button("Check Sorted")
            practice_info = gr.HTML("<div>Practice info will appear here.</div>")

        with gr.TabItem("Prediction"):
            gr.Markdown("**Prediction mode** — guess the number of swaps. Use Hint for help.")
            pred_in = gr.Number(value=5, label="Your prediction (integer)")
            with gr.Row():
                pred_btn = gr.Button("Submit Prediction")
                hint_btn = gr.Button("Hint")
            pred_result = gr.HTML("<div>Prediction results here</div>")
            pred_final_html = gr.HTML("<div></div>")

    # ---------- Callbacks wiring ----------
    gen_btn.click(fn=cmd_generate_random, inputs=[gen_len, gen_max, state], outputs=[array_text, visual, status, prog, state])
    load_btn.click(fn=cmd_parse_input, inputs=[input_text, state], outputs=[array_text, visual, status, prog, state])

    # Tutorial controls
    reset_btn.click(fn=tutorial_reset, inputs=[state], outputs=[visual, tut_status, prog, state])
    next_btn.click(fn=tutorial_next, inputs=[state], outputs=[visual, tut_status, prog, state])
    prev_btn.click(fn=tutorial_prev, inputs=[state], outputs=[visual, tut_status, prog, state])
    play_btn.click(fn=tutorial_play, inputs=[state, play_delay], outputs=[visual, tut_status, prog, state], queue=True)
    pause_btn.click(fn=tutorial_pause, inputs=[state], outputs=[visual, tut_status, prog, state])

    # Practice
    start_prac.click(fn=practice_start, inputs=[state], outputs=[practice_info, state])
    swap_curr.click(fn=practice_swap_current, inputs=[state], outputs=[visual, practice_info, state])
    next_pair.click(fn=practice_next_pair, inputs=[state], outputs=[visual, practice_info, state])
    check_prac.click(fn=practice_check, inputs=[state], outputs=[practice_info, state])

    # Prediction
    pred_btn.click(fn=prediction_run, inputs=[state, pred_in], outputs=[pred_result, pred_in, pred_final_html, state])
    hint_btn.click(fn=prediction_hint, inputs=[state], outputs=[pred_result])

    # On app load, generate default array
    demo.load(fn=lambda: cmd_generate_random(8, 20, initial_state()), inputs=[], outputs=[array_text, visual, status, prog, state])

# Run
if __name__ == "__main__":
    demo.launch()
