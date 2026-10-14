# Windows Computer Use MCP - User Guide (Task Patterns)

This guide shows how to ask for everyday Windows automation and which tool
handles each job. Every pattern names the operation, the arguments that
matter, and how to confirm it worked. Ask in plain language; the agent maps
to tools.

## Windows: find, focus, arrange

"Show me all open windows" → `automation_windows` list. You get titles,
handles, and processes. Follow with find by title substring when you know
the app ("find the window with Invoice in the title"), then focus it before
any input. Sending keystrokes to the wrong window is the classic beginner
failure; focusing first eliminates it.

"Maximize Notepad and put Paint beside it" → find each handle, then manage
(maximize) and position with explicit coordinates. Positioning needs all four
numbers; get the screen size from telemetry first if unsure. "Close the
calculator" → manage close by handle. If a close triggers an unsaved-changes
dialog, that is a second task (see dialogs), not a failure.

When a handle stops working, the window was recreated (common with Electron
apps and installers). Find again. Never retry a dead handle more than once.

## Elements: click, type, read inside apps

"Click the Save button in Settings" → `automation_elements` click with title
"Save" plus control_type Button inside the Settings handle. "Type
hello@example.com into the email field" → set_text on the Edit control, then
verify with get_text. "Is the Submit button enabled?" → enabled check before
clicking, so a greyed-out button becomes information instead of a mystery.

"Read everything in this dialog" → list with a deeper max_depth, then get_text
on the interesting nodes. Element snapshots beat screenshots for forms:
precise, cheap, and unambiguous. When the tree is huge, scope to one pane by
combining title with control_type rather than dumping the desktop.

"Wait for the Export button to appear" → wait operation with a timeout, not a
sleep loop. "Press Enter in this exact field" → set focus first via click or
focus, then keyboard press. Focus is a precondition, not a detail.

## Screens and vision: get_window_state and get_desktop_state

"Show me this window so I can decide" → `get_window_state` with capture_mode
som (annotated screenshot plus addressable elements). Then click by
element_index, which survives better than coordinates across resizes.

"What's on screen right now?" → `get_desktop_state` for the full inventory
when starting cold. Once oriented, switch to single-window snapshots; the
desktop scan on every step is how machines get slow.

"Read the error in that custom-drawn panel" → vision mode plus OCR, or
`automation_visual` extract_text on a tight region. Custom controls are why
both paths exist; try UIA first, vision second, and say which one worked.

## Pixels: automation_visual

"Click the red boat icon on the toolbar" → find_image with a template you
provide, threshold 0.8 to start, lower deliberately (0.6) only for
resolution-mismatched assets. "Read the total from this invoice region" →
extract_text on coordinates you read from a fresh screenshot, Tesseract
default, WinRT provider when available for handwriting-ish fonts.

"Prove the chart changed after I clicked Refresh" → screenshot before,
perform, screenshot after, diff or assert_changed with a threshold. The
evidence bundle (before/after/diff paths) is the deliverable for any visual
claim. "Check this dialog title says Export complete" → assert_text with
exact_match off unless punctuation matters.

"Highlight the field you're about to fill" → highlight briefly during
complex sequences so a watching human can follow. Telemetry, not decoration.

## Mouse and keyboard

"Double-click that file, then drag it to the folder" → mouse double_click
then drag with explicit start and target coordinates from a fresh rect call.
"Scroll down three pages" → scroll with amount, not a loop of wheel ticks.
"Select all, copy" → keyboard hotkey ctrl+a, ctrl+c — or better, the
semantic shortcut tool if the app profile exists.

"Hold Shift while clicking these five items" → keyboard hold for the
modifier across the click sequence, release after. Modifier state leaking
into later steps is a classic heisenbug; the hold operation scopes it.

"Type this 200-character key" → paste via clipboard (dialog helper or
clipboard_set plus ctrl+v), never character typing. Typing is for humans;
paste is for agents. Typing a password? Same rule, and never log it.

## Shortcuts: automation_shortcut

"Export the model" → shortcut send export action on the app profile (VRoid,
Notepad, Paint supported; profiles extend the list). Prefer this over
remembering that export is F8 in one app and Ctrl+E in another: the name
carries intent, the profile carries the keys. Always focus the window first,
and let the post-send stability wait finish before asserting.

"Save, then close" → two shortcut sends with a wait_stable between them.
"Bold this heading" → select the text first (elements or keyboard), then the
bold action. Shortcuts act on selection and focus; verify both preconditions
in the evidence when it matters.

## Assertions: automation_assert

"Wait until the window stops changing, then confirm the canvas differs" →
wait_stable then assert_changed with a threshold and the evidence bundle on.
"Confirm nothing moved after that no-op" → assert_unchanged. "Check the OK
button is actually visible" → assert_template with your template image.
"Read this region and confirm it says Paid" → assert_text, exact only when
punctuation decides.

"Give me fingerprints before and after the upgrade" → hash or hash_region
(dhash tolerates GPU rendering noise; sha256 does not). Store both hashes;
comparisons across sessions need the algorithm recorded alongside.

If wait_stable times out, narrow the region to the editor panel and raise
the timeout before concluding anything. Full-screen stability on a busy
desktop is genuinely hard; scoped stability is easy and sufficient.

## Dialogs: automation_dialog

"Save this file to D colon Projects report docx" → submit_path after the
Save As dialog is open: fills via clipboard (reliable for long paths),
select-all first, Enter to confirm, with pauses around the confirm key.
"Just fill the path, I'll confirm" → set_path without confirm. "Press Enter
now" → confirm alone.

Recovery: if the dialog never appeared, focus the parent app and resend the
Save shortcut. If the path field isn't focused, Tab into it. Prefer this
helper over manual ctrl+a-type-enter sequences every time; the helper's
pauses exist because dialogs animate.

## System: automation_system

"Is the server healthy?" → status. "What are this machine's specs?" → info
(CPU, RAM, GPU in one call). "Wait 10 seconds" → wait. "Wait until the
installer window appears" → wait_for_window with title and timeout, not a
sleep loop. "Copy this connection string to my clipboard" → clipboard_set;
"what's in the clipboard" → clipboard_get (pyperclip must be present; the
error says so when it isn't).

"Launch VLC" → start_app with the exe path. "What photo editors are
running?" → processes with a filter. "Listen to my voice command" → the
voice operations (listen, wake_start/stop/status) when audio plumbing is
installed. Timers, alarms, weather, and music control live here too; they
are conveniences, not automation primitives.

## Missions: automation_mission

"Install this app and verify it opens" → mission run with the goal in plain
language: it decomposes, executes with retry and refocus recovery, verifies
each step, and returns pass/fail with evidence paths. "Convert these ten
screenshots to a report" → run with the steps spelled out. "Plan the
migration but don't touch anything" → plan operation for the decomposition
without execution.

One mission at a time per goal; at most two concurrent missions system-wide
(extra callers get a clean blocked status, not a pileup). Long missions
belong in run with a timeout; status polling tracks progress; cancel stops
cleanly. Preset workflows (run_preset) replay vetted sequences by name.
Record-then-replay (record/replay) captures a demonstration for exact
repetition with verification.

"Run this overnight" → set the timeout generously, confirm evidence output
paths up front, and check host CPU/RAM in safety status first. A mission
that cannot explain its evidence directory is not ready to run unattended.

## Tasks and macros

"Export every open document to PDF" → `automation_task` run with per-step
evidence screenshots; prefer it over manual chaining for anything longer
than three steps. Status and cancel track and stop sessions. List profiles
and templates first when working a known app (VRoid export is the canonical
example: shortcut steps plus dialog plus file assertion in one call).

"Do exactly what I just showed you, ten times" → `automation_macro` record
while demonstrating, stop to save, replay (or replay_with_verify to check
each step against the recording). Macros are exact, not intelligent: any UI
change breaks them loudly, which is a feature.

## Smart, system, windows, task cross-reference

"Click the Save button, wherever it is" → `automation_smart` click by
description across all windows, OCR fallback included. Use when the target
window is unknown; switch to handle-scoped tools once found.

"Give me the UI inventory of everything running" → `automation_smart`
discover, optionally filtered by app. "List controls of this settings
window" → list_controls with the handle from a prior find.

"Open the second document and read its title" → windows find plus title op.
"Is this window still alive?" → rect or state; stale handles error cleanly,
find again.

## Cameras, faces, presence

"Enroll me" → `automation_face` enroll with your name (captures from the
camera and registers in one call, no image file needed). "Who does the
camera see?" → capture and match. "Forget me" → delete by exact name. "Who
is enrolled?" → list. All of it local; nothing leaves the machine.

"Tell me when someone sits down" / "lock when I leave" → the presence ops on
the same tool. `arm` starts watching, `presence_status` reports (armed,
status, grace and lock timeouts, seconds since last seen), `presence` checks
now, `test` checks without ever locking, `set_timeouts` adjusts grace
(default 300 seconds, the coffee run) and lock timeout (default 900 seconds,
going home) plus the auto-lock switch (default off), `disarm` stops. A short
absence inside grace does nothing by design; a long absence recommends
locking; the workstation locks only with auto-lock explicitly on. Poll
`presence_status` every 15 seconds from a dashboard for the live view.

"Prove the camera works" → test op: captures, recognizes, reports, never
locks, frame info included. Camera missing or busy returns a clean error
with the fix (index, cable, permissions, another app holding it), and every
camera-free op (arm, disarm, timeouts, status) keeps working regardless.

## Safety, watchers, and approvals

"Is it safe to click?" → `automation_safety` status: counters, kill-switch
state, rate budget, watcher census, host CPU/RAM snapshot. Read it before
long jobs on busy machines. "Stop everything" → kill switch semantics via
the safety controls; cancel each running mission too. "Reset the counters"
→ reset_counters (does not clear a kill switch; that is deliberate).

"Approve clicking for ten minutes" → `approve_automation` with duration;
all mouse/keyboard flows through the window. "Watch for the render dialog
and tell me" → `automation_watch` start with condition window_appears and a
timeout (capped at one hour), then status polling; stop deletes it. At most
eight watchers run at once; faster than half-second polling is clamped.

"How loaded is the host?" → safety status resource snapshot (CPU/RAM
percentages) plus the watcher census. If CPU sits above ninety sustained,
defer the mission or raise caps explicitly with justification, never
silently.

## Chat, skills, help, logs

"Talk me through this setup" → the chat surface (personalities, memory)
for guided work. "What can this server do?" → the skills catalog and the
help system (per-category, per-tool). "Show me what happened" → logs and
telemetry: every action recorded with timestamp, tool, target, duration,
and outcome; query by recency or failure.

"Export this conversation" / "summarize the session" → session tools that
read the same telemetry the agent writes. One store, many views.

## Advanced patterns, second round

"Record my exact clicks and replay them nightly, failing loudly on any UI
change" → macro record once carefully (slow, deliberate, no stray clicks),
stop and name it, then replay_with_verify on schedule. Verification compares
each step's outcome hash against the recording; drift fails the run instead
of clicking hopefully. Keep recordings short: one workflow per macro, named
for what it does, with the app version noted. Re-record after app updates;
never trust a year-old macro.

"Watch three conditions at once during the render" → three watchers (window
appears, text appears, element appears), each with its own timeout, status
polled together. Stop each as it fires. Eight is the cap; three is comfort.
Name watchers after their purpose so the list reads as documentation.

"Which OCR engine for this job?" → Tesseract default for UI text and
documents; WinRT provider for handwriting-like fonts and touch keyboards;
region OCR over full-screen OCR always. If results are noisy, halve the
region and retry before changing engines; geometry beats engines.

"How do I tune template matching?" → start at 0.8 threshold with an exact
screenshot-template pair. On miss: check resolution and theme first (dark
mode changes pixels), then step down 0.1 at a time to a 0.6 floor, and below
that switch to feature matching or OCR anchoring instead. Record the winning
threshold with the template; thresholds are per-asset data, not global
settings.

"Handle Save As for five different filenames" → dialog submit_path in a
loop with the path parameterized, verifying file existence after each.
"Handle an Open dialog" → same helper, Open variant. "The dialog has extra
option checkboxes" → set them with element clicks before confirming, then
confirm. Dialogs are state machines: fill, verify the fill with get_text
where possible, then confirm. Never confirm blind.

"Tune presence for my routine" → start with defaults (300s grace, 900s
lock, auto-lock off) for a week and read the status history. Commute away
from the desk often? Raise grace. Notebook full of secrets that travels?
Lower lock timeout and enable auto-lock explicitly, understanding what it
does. Shared office? Enroll only yourself and keep tolerance strict.
Presence is a personal instrument; defaults are a starting point, not a
prescription. Disarm on vacation. Re-check after camera or lighting changes.

"Read safety status like a pilot" → counters tell rate (actions per minute
against the cap), flags tell mode (kill switch, dry run, face opt-in),
watcher census tells background load, resource snapshot tells host strain.
All green and idle: proceed. Anything red: resolve before starting. Amber
(HITL window open, three watchers running): proceed with attention. Make
this scan a habit at session start; it takes ten seconds and prevents most
classes of surprise.

"Drive Notepad end to end" → targets page pattern: find by class
Notepad, activate, get_window_state, type via elements, save via shortcut,
verify via file dialog helper and a file listing. "Drive VRoid export" →
task runner with the app profile: shortcut steps, dialog step, file
assertion step, evidence screenshots throughout. "Drive KiCad / LibreOffice"
→ same shape with their profiles: discover controls once, then element
operations; canvas work goes through visual tools. App profiles exist so
nobody re-derives Export means F8 more than once per app.

"Debug why my shortcut does nothing" → verify focus (get_active window),
verify the profile lists the action (describe), send with stability wait,
assert the expected change. Four stations, in order, no skipping. Nine times
out of ten it was focus. The tenth time the profile needs the new action
added; say so explicitly.

"Automate across two apps" → mission with explicit handoff steps: finish
app A to a verifiable artifact (saved file with asserted size), then start
app B from that artifact path. Never pass pixels between apps; pass files.
Files are the inter-application API. Verify the artifact at the boundary
both ways: A says it wrote it, B says it opened it.

"Run the same check on every settings page" → batch over a list with the
client model choosing the operation per item where sampling is available;
fixed sequences where it is not. Cap parallelism (two missions), collect
evidence per item, summarize as a table with pass/fail plus the one-line
reason for each fail. Tables, not prose, for repetitive verification.

"Recover from a half-finished migration" → status every session (what ran,
what verified, what is unknown), resume from the first unverified step,
never re-run verified steps blindly (idempotency is verified, not assumed).
If a step is not idempotent (sends, deletes), confirm its outcome from
independent signals before deciding to skip or repeat. Partial progress
with evidence beats restart-from-zero every time.

"Keep the box healthy while I automate" → watch the resource snapshot
between missions; rotate the evidence directory (keep failures, prune
success screenshots older than a week); stop idle watchers; restart the
server monthly (fresh process, same config) the way you would reboot a
router. Automation infrastructure is infrastructure: it needs the same
boring maintenance as everything else that runs Pizza Friday to payroll.

## Domain walkthroughs, third round

"Crawl this whole application and map it" → analyze_winapp crawl with a
sensible max depth (five is the default for a reason; deeper trees cost
exponentially), output directory set per target, then read the element map
plus the screenshot portfolio. "Probe its shortcuts safely" → discover
operation, which presses candidate keys and captures before/after states
so nothing destructive hides in the results. "Capture these three dialog
states for the docs" → portfolio with named states. The crawl is the
spec-writer's best friend: every reversal, every test plan, every onboarding
tour starts from a crawl, not from clicking around hopefully.

"Query the logs for what failed last night" → logs with source, level, and
free-text filters; start broad (ERROR across all sources, last 24 hours),
then narrow by source name once a suspect emerges. "Show me only the
mission failures" → filter by the mission source. "How often does OCR
miss on this dialog?" → search the message text for the dialog name plus
the miss pattern, count over a week. Logs answer every question you ask
twice; the third time, make it a watcher or a scheduled check instead.

"Set up my LLM providers" → settings LLM page backed by the provider
operations: list providers, add or edit base URL plus key plus default
model, test the connection (which reports reachability per provider type:
Ollama version endpoint, OpenAI-compatible model list, Anthropic model
list), save, then list models to confirm. "Chat with my local model" →
chat surface with the provider selected, or the chat API directly with
provider plus model plus messages. "Why does the model list come back
empty?" → test the provider first; nine times in ten the base URL is wrong
or the local server is not running. Provider problems are connectivity
problems until proven otherwise.

"Navigate the help like documentation" → help system per category, then
per tool: categories first for orientation, tool detail for exact
parameters, examples for the shape of a good call. "Activate the skill for
this workflow" → skills catalog, staged loading (table of contents first,
sections on demand), so a 50-page skill costs a paragraph of context until
the deep part is needed. "What changed in this version?" → changelog plus
the skill telemetry that shows which guidance actually gets used.

"Talk instead of type" → voice operations: dictate transcribes into notes,
speak reads content aloud in the chosen voice and speed, listen executes a
short voice command window, wake words enable hands-free with start/stop/
status lifecycle. Weather, timers, alarms, and music control ride the same
audio plumbing. Voice needs microphone consent plus a working input device;
check both before promising anything hands-free, and keep listen windows
short (the default few seconds) unless the task genuinely needs more.

"Capture the full state of this window for the bug report" → window-scoped
screenshot plus element snapshot plus the last fifty log lines for the
process, bundled with versions (app, server, OS). "Capture the whole
desktop" → desktop state with vision on for the annotated overview.
"Compare today's state with last week's" → hash_region fingerprints of the
key panels, stored with dates. State captures are evidence; evidence needs
timestamps, versions, and the exact operation parameters that produced it,
or the comparison next week is meaningless.

"Choose the right capture mode" → ax for speed (tree only, no pixels),
som for grounding (tree plus annotated screenshot, the default for
agent-driven clicks), vision for pure pixels (custom canvases, remote
frames). "Click this element reliably" → snapshot with element indices,
then click by index within the same turn. "Tune element timeouts" → longer
for cold-start apps and installers, shorter for warm dialogs; per-element
timeout beats global impatience. Foreground dispatch is the default;
background dispatch exists for driving one app while working in another,
with the documented trade-offs around focus-dependent controls.

"Run the vetted export preset" → mission presets by name (VRoid export is
the reference: shortcut steps, dialog step with path helper, file assertion
with size check, evidence screenshots). "List available presets and
templates" → list operations first, never guess preset names. "Build a new
preset from this working session" → record the macro, verify the replay,
promote the verified recording to a named preset with its app profile
attached. Presets are how individual competence becomes team capability;
name them for the job, version them when the app updates.

"Audit this machine for automation readiness" → system telemetry (CPU, RAM,
GPU, disk), process list filtered to targets and blockers, startup programs
reviewed, taskbar settings checked. "Something is slow and I don't know
what" → top resource consumers plus recent error events plus volume usage
in one diagnostics pass, then narrow. "Prepare this box for a week of
unattended runs" → disable sleep, confirm disk headroom (screenshots
accumulate), set generous mission timeouts, arm presence monitoring with
explicit timeouts if the human will be near, verify the evidence directory
is writable. Unattended means prepared, not merely unobserved.

## Watchers, approvals, and long-running vigilance

"Tell me the moment the download finishes" → watcher on window_appears with
the dialog title, generous timeout, status polled every few seconds, stop
on fire. "Alert me when this file lands" → filesystem watch on the
directory plus a window watcher for the completion toast; belt and
suspenders for unattended nights. "Watch for errors while I am away" →
text_appears watcher on the log window for the word ERROR, with presence
monitoring armed so the machine locks itself if nobody is there to see the
alert. Watchers compose: one condition per watcher, several watchers per
mission, all stopped in cleanup.

"Approve the next hour of clicking" → approval window with explicit
duration, then verify the window is actually open (safety status shows the
expiry timestamp) before starting. "Approve just this installer" → five
minutes, focused window, cancel after. Approval is a budget, not a
blessing: spend it on the planned steps and no further.

"Run a mission I can walk away from" → run with timeout set to the honest
duration plus margin, evidence directory confirmed writable, presence armed
with auto-lock off (locking mid-mission blinds the screenshots), watcher on
the completion condition as backstop. "Run one I can sleep through" →
everything above plus host telemetry checked first, power settings confirmed
(no sleep, no hibernate), and a morning review step scheduled. Unattended
success is designed in daylight, not discovered at 3 AM.

"Hand tonight's run to the morning shift" → mission status export (steps
done with evidence links, current step with exact state, remaining steps in
order), plus the three load-bearing claims verified afresh. "Audit who did
what" → telemetry query by session, tool, target, with timestamps and
outcomes. "Prove this ran correctly last Tuesday" → filter by date, export
the slice with evidence paths. Logs are the organization's memory; write
them as if a stranger must reconstruct your reasoning, because one will.

## Rapid troubleshooting Q&A

"Nothing is found, ever" → check the app is actually running (processes),
check the title spelling (find with partial match), check the session (an
elevated app is invisible to a non-elevated observer and vice versa),
check the desktop (locked screens and UAC prompts hide everything). Four
checks, in that order, before concluding anything is broken.

"It worked yesterday" → what changed overnight: app updates (re-crawl one
dialog and diff the trees), Windows updates (reboot pending changes focus
behavior), display changes (new scale, new monitor, RDP session with
different geometry), server updates (changelog, then canary checks).
Yesterday's evidence plus today's re-run of the same check names the
difference within minutes. Guessing wastes hours.

"OCR was right yesterday and wrong today" → lighting and theme did not
change, so look at scaling (screenshots at different DPI), region drift
(the window moved two pixels and the tight crop now clips a descender),
and provider (someone flipped Tesseract to WinRT or back). Re-capture the
region fresh, widen by ten pixels each side, retry. Region hygiene first,
engine changes last.

"The mission passed but nothing happened" → a verification step asserted
the wrong signal (window exists is not window shows the result; file
exists is not file has content). Strengthen assertions to effects, not
presences: row counts, file sizes, pixel diffs, confirmation strings.
A mission is only as honest as its weakest assert; audit the asserts
before trusting a green run that feels wrong.

"Two sessions fight over the mouse" → stop one of them. There is no
locking protocol that makes shared-cursor automation safe; the second
operator waits, watches, or works a different machine. If contention is
structural (nightly job plus morning human), schedule them apart and put
the boundary in writing where both can see it.

"The camera worked in the browser preview but not in capture" → different
device enumeration orders (browser video order versus OpenCV index order
are unrelated numbering schemes), another app holding the device
exclusively, or a permissions prompt nobody answered. List cameras via the
dedicated endpoint, match by name where possible, fix the default in
Windows Settings so both orders agree, and retry the capture alone before
blaming the automation.

"Face enrolled but never recognized" → lighting direction (overhead office
light hollows eyes; face a window or lamp), distance (arm's length, face
filling a third of the frame), angle (straight on for enrollment, tolerance
for daily use), and tolerance setting itself (lower is stricter; raise in
small steps with test captures between). Enroll three frames (straight,
slight left, slight right) when the tool supports it. Recognition is
physics plus statistics; improve the physics first.

"Everything is slow since Tuesday" → host telemetry first (CPU, RAM, disk,
plus the watcher census for background loops nobody stopped), then the
evidence directory size, then the server log size, then app updates. Slow
systems are usually full systems (disk), busy systems (runaway watcher),
or changed systems (update). The numbers say which within a minute; act on
the numbers, not the mood.
