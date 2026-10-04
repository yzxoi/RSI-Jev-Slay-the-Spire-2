# E172 — Interactive decision overlay

Issue #332. User requested a polished translucent window that can be selected, dragged, resized and closed. Reuse E050/PR94's read-only projection and its existing confidence semantics; port files from `codex/e050-live-decision-window`, not its unrelated controller history. This is presentation, not policy strength.

Baseline is E050's borderless click-through panel. New default: titled floating interactive NSPanel, native close/minimize/resize affordances, minimum360x490, default430x540/opacity0.90, subdued teal/charcoal surfaces, adaptive candidate row count. Explicit --click-through retains old behavior; --builtin resolves the observed Built-in Retina Display by name, never silently chooses another monitor. Closing this UI terminates only its process; no game/model calls exist in its code path.

Fixed validation: inherited monitor/overlay synthetic cases plus E050 historical replay; native window drag/resize/close inspection while actual game remains at main menu. Read-only UI smoke only. Compile/import and targeted tests, then inspect native controls and placement. No manufactured confidence, no candidate execution. Commit implementation before evaluation; record actual observations and limitations before merge. Separate E173 owns subsequent gameplay.

Commands: `python3 -m unittest discover -s tests -p 'test_monitor.py'`; same for `test_overlay.py`; `python3 -m rsi.overlay --replay-trace <fixed-local-E050-trace> --replay-interval .08 --builtin`. Results follow.
