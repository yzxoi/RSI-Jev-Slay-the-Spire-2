"""Translucent, click-through macOS decision overlay; reads trace files only."""

import argparse
from pathlib import Path

from .monitor import TraceFeed


REASONS = {
    "low_hp_before_spending_energy": "生命危险：请求 Astra 决策",
    "lethal_end_turn": "结束回合会死亡：请求 Astra 决策",
    "macro_review": "路线 / 奖励：请求 Astra 决策",
    "explicit_card_review": "关键卡牌：请求 Astra 决策",
    "sandpit_expiry_before_spending_energy": "机制风险：请求 Astra 决策",
}


def display_options(decision, limit=5):
    """Keep the chosen action visible even when the candidate list is long."""
    choices = (decision or {}).get("options") or []
    shown = list(choices[:limit])
    if not any(option.get("selected") for option in shown):
        selected = next((option for option in choices if option.get("selected")), None)
        if selected:
            shown[-1:] = [selected]
    return shown, max(0, (decision or {}).get("option_count", len(choices)) - len(shown))


def run(feed, *, opacity=0.84, width=410, height=490, margin=20, screen_index=None, interactive=False):
    try:
        import objc
        from AppKit import (
            NSApplication, NSApplicationActivationPolicyAccessory, NSBackingStoreBuffered,
            NSBezierPath, NSColor, NSFloatingWindowLevel, NSFont, NSFontAttributeName,
            NSForegroundColorAttributeName, NSLineBreakByTruncatingTail, NSPanel,
            NSParagraphStyleAttributeName, NSScreen, NSWindowCollectionBehaviorCanJoinAllSpaces,
            NSWindowCollectionBehaviorFullScreenAuxiliary, NSWindowStyleMaskBorderless,
            NSWindowStyleMaskNonactivatingPanel, NSMutableParagraphStyle, NSView,
        )
        from Foundation import NSObject, NSProcessInfo, NSString, NSTimer
    except ImportError as exc:
        raise RuntimeError("macOS PyObjC/AppKit is required for the native overlay") from exc

    bg = NSColor.colorWithCalibratedRed_green_blue_alpha_(.055, .065, .10, .96)
    surface = NSColor.colorWithCalibratedRed_green_blue_alpha_(.115, .13, .19, .93)
    stroke = NSColor.colorWithCalibratedRed_green_blue_alpha_(.35, .38, .49, .8)
    white = NSColor.colorWithCalibratedRed_green_blue_alpha_(.96, .96, .94, 1)
    dim = NSColor.colorWithCalibratedRed_green_blue_alpha_(.68, .73, .82, 1)
    gold = NSColor.colorWithCalibratedRed_green_blue_alpha_(.97, .78, .43, 1)
    teal = NSColor.colorWithCalibratedRed_green_blue_alpha_(.45, .89, .76, 1)
    plum = NSColor.colorWithCalibratedRed_green_blue_alpha_(.79, .64, .99, 1)

    def box(x, y, w, h, radius, color, border=None):
        path = NSBezierPath.bezierPathWithRoundedRect_xRadius_yRadius_(((x, y), (w, h)), radius, radius)
        color.setFill()
        path.fill()
        if border:
            border.setStroke()
            path.setLineWidth_(1)
            path.stroke()

    def label(value, x, y, w, h=20, size=12, color=white, bold=False):
        style = NSMutableParagraphStyle.alloc().init()
        style.setLineBreakMode_(NSLineBreakByTruncatingTail)
        font = NSFont.boldSystemFontOfSize_(size) if bold else NSFont.systemFontOfSize_(size)
        NSString.stringWithString_(str(value or "")).drawInRect_withAttributes_(
            ((x, y), (w, h)), {NSFontAttributeName: font, NSForegroundColorAttributeName: color,
                            NSParagraphStyleAttributeName: style})

    class DecisionView(NSView):
        def initWithFrame_(self, frame):
            self = objc.super(DecisionView, self).initWithFrame_(frame)
            if self is not None:
                self.snapshot = {}
            return self

        def isOpaque(self):
            return False

        def drawRect_(self, rect):
            snap = self.snapshot
            decision = snap.get("current") or snap.get("latest") or {}
            context = decision.get("context") or {}
            source = decision.get("source") or "等待 trace"
            color = gold if source.startswith("Astra") else plum if source == "Jev" else teal
            W, H = self.bounds().size
            box(0, 0, W, H, 16, bg, stroke)
            box(13, H - 51, W - 26, 38, 9, surface)
            label("✦ STS2 决策", 24, H - 42, W - 155, 22, 15, white, True)
            label("回放" if snap.get("mode") == "replay" else "LIVE · 只读", W - 112, H - 39, 90, 16, 11, teal, True)

            run_id = snap.get("game_run_id") or context.get("run_id") or "—"
            floor = context.get("floor")
            turn = context.get("turn")
            hp = context.get("hp")
            max_hp = context.get("max_hp")
            position = f"{floor if floor is not None else '—'} 层 · {turn if turn is not None else '—'} 回合"
            hp_text = f"HP {hp}/{max_hp}" if hp is not None and max_hp is not None else "HP —"
            label(run_id, 22, H - 83, W * .54, 18, 11, dim)
            label(position, 22, H - 104, W * .6, 18, 12, white, True)
            label(hp_text, W - 126, H - 104, 105, 18, 12, white, True)

            box(13, H - 210, W - 26, 95, 11, surface)
            label(source, 25, H - 139, W - 50, 18, 12, color, True)
            action = REASONS.get(decision.get("label"), decision.get("label") or "等待决策…")
            label(action, 25, H - 172, W - 50, 29, 20, white, True)
            state_text = {"accepted": "已执行", "proposed": "待执行", "pending": "计算中",
                          "awaiting_astra": "等待 Astra", "rejected": "被拒绝",
                          "discarded": "状态过期", "delivery_unknown": "交付待确认"}.get(decision.get("state"), "—")
            label(f"{context.get('screen') or '—'}  ·  {state_text}", 25, H - 196, W - 50, 18, 11, dim)

            conf = decision.get("confidence")
            label("Jev confidence", 22, H - 244, W - 120, 18, 11, dim)
            label(f"{round(conf * 100)}%" if isinstance(conf, (int, float)) else "—", W - 72, H - 244, 48, 18, 12, gold, True)
            box(22, H - 259, W - 44, 5, 2.5, surface)
            if isinstance(conf, (int, float)):
                box(22, H - 259, (W - 44) * min(max(conf, 0), 1), 5, 2.5, gold)

            label("候选选项 · 模型分布", 22, H - 291, W - 44, 19, 12, dim, True)
            options, hidden = display_options(decision)
            y = H - 324
            if not options:
                label("当前没有候选分布记录", 26, y, W - 52, 18, 11, dim)
            for option in options:
                box(18, y - 3, W - 36, 29, 7, surface, gold if option.get("selected") else None)
                label(option.get("label"), 27, y + 2, W - 112, 18, 11, white if option.get("selected") else dim)
                probability = option.get("probability")
                label(f"{round(probability * 100)}%" if isinstance(probability, (int, float)) else "—",
                      W - 69, y + 2, 44, 18, 11, gold if option.get("selected") else dim, bool(option.get("selected")))
                y -= 34
            if hidden:
                label(f"另有 {hidden} 个选项", 22, y + 2, W - 44, 18, 10, dim)

            plan = decision.get("plan") or snap.get("plan")
            if plan and H >= 470:
                box(13, 40, W - 26, 52, 9, surface)
                plan_name = "Astra 房间方案" if plan.get("kind") == "room_plan" else "Astra 楼层方案"
                label(plan_name, 24, 68, W - 48, 16, 11, gold, True)
                label(plan.get("guidance") or "—", 24, 47, W - 48, 17, 10, dim)
            footer = snap.get("status") or "waiting"
            label(f"{footer} · {snap.get('segment') or '无 trace'}", 20, 13, W - 40, 18, 10, dim)

    class Controller(NSObject):
        def initWithFeed_view_(self, value, view):
            self = objc.super(Controller, self).init()
            if self is not None:
                self.feed = value
                self.view = view
            return self

        def tick_(self, timer):
            try:
                self.view.snapshot = self.feed.snapshot()
                self.view.setNeedsDisplay_(True)
            except Exception as exc:
                self.view.snapshot = {"status": f"trace error: {type(exc).__name__}"}
                self.view.setNeedsDisplay_(True)

    app = NSApplication.sharedApplication()
    app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)
    NSProcessInfo.processInfo().setProcessName_("STS2 Decision Overlay")
    screens = NSScreen.screens()
    screen = screens[screen_index] if screen_index is not None else NSScreen.mainScreen()
    if screen is None:
        raise RuntimeError("No display found for overlay")
    rect = screen.frame()
    frame = ((rect.origin.x + rect.size.width - width - margin,
              rect.origin.y + rect.size.height - height - margin), (width, height))
    panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
        frame, NSWindowStyleMaskBorderless | NSWindowStyleMaskNonactivatingPanel,
        NSBackingStoreBuffered, False)
    panel.setTitle_("STS2 Decision Overlay")
    panel.setLevel_(NSFloatingWindowLevel)
    panel.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces |
                                 NSWindowCollectionBehaviorFullScreenAuxiliary)
    panel.setOpaque_(False)
    panel.setBackgroundColor_(NSColor.clearColor())
    panel.setHasShadow_(True)
    panel.setAlphaValue_(opacity)
    panel.setIgnoresMouseEvents_(not interactive)
    panel.setMovableByWindowBackground_(interactive)
    view = DecisionView.alloc().initWithFrame_(((0, 0), (width, height)))
    panel.setContentView_(view)
    controller = Controller.alloc().initWithFeed_view_(feed, view)
    controller.tick_(None)
    timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
        .5, controller, "tick:", None, True)
    panel.orderFrontRegardless()
    print(f"Native overlay on screen {screen_index if screen_index is not None else 'main'}: {width}x{height}, opacity {opacity:.2f}, click-through {not interactive}", flush=True)
    app.run()
    timer.invalidate()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--trace", help="Pin one decisions.jsonl file")
    source.add_argument("--replay-trace", help="Animate a saved trace without touching the game")
    parser.add_argument("--game-run-id", help="Follow the newest native segment for this game run")
    parser.add_argument("--replay-interval", type=float, default=.25)
    parser.add_argument("--opacity", type=float, default=.84)
    parser.add_argument("--width", type=int, default=410)
    parser.add_argument("--height", type=int, default=490)
    parser.add_argument("--margin", type=int, default=20)
    parser.add_argument("--screen", type=int, help="0-based macOS display index; default active display")
    parser.add_argument("--interactive", action="store_true", help="Allow dragging; default click-through")
    args = parser.parse_args()
    if not .25 <= args.opacity <= 1 or args.width < 330 or args.height < 450 or args.margin < 0 or args.replay_interval <= 0:
        parser.error("Need opacity .25..1, width >=330, height >=450, margin >=0, replay interval >0")
    feed = TraceFeed(trace=args.trace, game_run_id=args.game_run_id,
                     replay_trace=args.replay_trace, replay_interval=args.replay_interval)
    run(feed, opacity=args.opacity, width=args.width, height=args.height,
        margin=args.margin, screen_index=args.screen, interactive=args.interactive)


if __name__ == "__main__":
    main()
