# Research Paper Technical Source Document

## Audit scope and evidence rule

This document is a code- and artifact-level technical audit of the current
`Smart Public Safety Surveillance & Weapon Detection` project. It is a source
document for a future paper, not the paper itself.

Evidence examined:

- Python source under `core/`, `streams/`, `backend/`, `alerts/`, `database/`,
  `evidence/`, `auth/`, and `config/`
- Vanilla JavaScript, HTML, and CSS under `frontend/`
- `models/best.pt` and `models/yolo11n.pt` checkpoint metadata
- `data/surveillance.db` schema and current row aggregates
- `README.md`, `requirements.txt`, and the automated tests

No claim is made below unless it is supported by those artifacts. Where the
repository does not contain evidence, the exact statement **“Not available in
the current project evidence.”** is used.

---

## A. Verified project facts

### Project identity

- **Project title:** Smart Public Safety Surveillance & Weapon Detection.
- **Application name in configuration:** Smart Safety Command Center.
- **Primary problem:** detect weapon objects in visual surveillance inputs,
  validate that a detected weapon is spatially associated with a detected
  person, create a durable security event, retain evidence, and deliver an
  authority-facing alert.
- **Target users represented by the code:** an authority/operator user for
  alert review and a monitoring user for live visual monitoring.
- **Implemented user interfaces:** a general monitoring/analysis SPA at `/`
  and a dedicated authority alert console at `/authority`.
- **Backend:** FastAPI application in `backend/main.py`.
- **Inference:** Ultralytics YOLO models, OpenCV frame handling, and a custom
  IoW-based validation stage.
- **Persistence:** SQLAlchemy with SQLite by default, using
  `data/surveillance.db`.
- **Real-time transport:** `/ws/monitoring` for monitoring frames and
  `/ws/alerts` for authenticated authority alert events.
- **Evidence:** JPEG files stored below `evidence/captures/YYYY/MM/DD/` and
  referenced by security events.
- **Server alarm:** one `AlarmManager` owned by the singleton `AlertService`.

### What is implemented versus what is not demonstrated

The implementation combines two object detectors, human-weapon spatial
validation, event persistence, asynchronous evidence saving, server-side alarm
control, and two dashboards. These are implementation characteristics, not
automatically research novelties.

The repository contains no literature review, citations, ablation study,
benchmark protocol, independently labeled evaluation set, training dataset
copy, hardware report, or reproducible experiment report. Accuracy,
precision, recall, F1, throughput, latency, and deployment-scale claims must
not be presented as measured project results without additional experiments.

### Limitations already visible in the implementation

- Authentication uses a fixed prototype bearer token and configured
  evaluation credentials.
- The dashboard statistics endpoint currently returns `active_threats: 0`
  as a placeholder.
- Notification dispatch is a print-based mock, not a confirmed external
  notification integration.
- The video endpoint stores an uploaded file in the system temporary
  directory and reuses the monitoring WebSocket flow; there is no independent
  video-job/status model.
- The default database is SQLite and there is no demonstrated multi-process
  deployment strategy.
- No verified dataset composition or class distribution is stored in the
  repository.
- No measured field performance is available.

---

## B. Complete system architecture

### End-to-end architecture

```text
Browser webcam / IP camera / RTSP / video file / uploaded image
                         |
                         v
       OpenCV acquisition or browser JPEG frame transport
                         |
                         v
       WeaponDetector (custom best.pt) + HumanDetector (yolo11n.pt)
                         |
                         v
       ThreatEngine: highest IoW human for each weapon
                         |
                         v
       ValidatedThreat objects (IoW >= configured threshold)
                         |
                         v
       SecurityEvent persisted in SQLite
          |                 |                 |
          |                 |                 +--> NotificationDispatcher
          |                 |
          |                 +--> asynchronous EvidenceCapture
          |
          +--> AlertService --> singleton AlarmManager
                              |
                              +--> authenticated /ws/alerts

MonitoringSession --> /ws/monitoring --> monitoring dashboard frames
Authority REST APIs + /ws/alerts --> authority alert dashboard
```

### Stage-by-stage implementation

| Stage | Source | Input | Processing | Output / side effect | Failure handling |
|---|---|---|---|---|---|
| Configuration | `config/settings.py` | environment and constants | resolves model, database, evidence and thresholds | runtime settings | directories are created; missing model failures occur during model loading |
| Browser webcam | `frontend/js/monitoring.js` | camera permission and video frames | `getUserMedia`, canvas JPEG every 100 ms | binary WebSocket frames | user-facing alerts and stop/reset on camera errors |
| IP/RTSP/video capture | `backend/services/monitoring_service.py` | URL/path | `cv2.VideoCapture`, capture thread | latest frame in session | failed open returns; capture errors break loop; `finally` releases capture |
| Static image | `backend/api/analysis.py` | multipart image | OpenCV decode | one analyzed frame and base64 annotated image | invalid MIME/decode returns HTTP 400 |
| Video upload | `backend/api/analysis.py` | multipart video | writes temporary file | session ID and path | invalid MIME returns HTTP 400 |
| Weapon detection | `core/weapon_detector.py` | NumPy BGR frame | custom YOLO prediction | `Detection` list | model/API exceptions are not converted into a domain result |
| Person detection | `core/human_detector.py` | same frame | YOLO prediction restricted to class 0 | person `Detection` list | same general exception behavior |
| Association | `core/threat_engine.py` | weapon and person detections | intersection area divided by weapon area; highest human retained | `ValidatedThreat` list | zero-area weapons are skipped |
| Event persistence | `database/repository.py` | validated threat | inserts `SecurityEvent`, commits and refreshes | durable event ID | database exceptions propagate |
| Alert publication | `backend/services/alert_service.py` | event | publishes queue message and starts alarm activation thread | `THREAT_DETECTED` | duplicate event IDs are rejected in memory |
| Evidence | `evidence/capture.py` and `AlertService.persist_evidence` | annotated frame and threat | draws weapon/person boxes and writes JPEG | evidence path, later `EVIDENCE_READY` | persistence catches and prints failures |
| Notification | `alerts/dispatcher.py` | event | prints event details | mock notification output | no external delivery is implemented |
| Server alarm | `alerts/alarm.py` | activation/mute/stop | pygame mixer and looping buzzer | physical/server-side alarm state | unavailable mixer gives `UNAVAILABLE`; playback errors are logged |
| Monitoring WebSocket | `backend/websocket/monitoring_ws.py` | control JSON and binary frames | session queue polling | frame JSON messages | disconnect/finally stops session |
| Authority WebSocket | `backend/websocket/alerts_ws.py` | token query parameter | subscriber queue bridge | connection and alert messages | invalid token closes with 1008; subscriber is removed |

### Singleton inference architecture

`backend/services/inference_service.py` implements a singleton-like
`InferenceService`. It creates one `WeaponDetector`, one `HumanDetector`, and
one `ThreatEngine` for the process and updates the IoW and weapon confidence
settings from in-memory application settings before each inference call.

The singleton inference service is separate from the singleton alarm
ownership. The only `AlarmManager()` constructor call is in
`AlertService.__init__`.

---

## C. AI and model audit

### Custom weapon checkpoint: `models/best.pt`

Verified checkpoint metadata:

- Ultralytics task: `detect`
- Architecture metadata: `yolo11s.yaml`, scale `s`
- Number of classes: 5
- Input image size in checkpoint arguments: 640
- Class names: `gun`, `knife`, `grenade`, `missile`, `sword`
- Dataset path recorded in checkpoint: `/kaggle/working/v9-weapon-detection-dataset/data.yaml`
- Training date recorded: `2026-09-06T13:53:45.520238+00:00`
- Recorded run name: `YOLO11s_V9_60E_CONTINUED`
- Recorded model source: `/kaggle/working/weapon_training/YOLO11s_V9_60E_2GPU/weights/last.pt`
- Recorded `epochs`: 8 for the stored training-result series
- Recorded batch: 32
- Recorded device: `0`
- Recorded workers: 2
- Recorded optimizer: `auto`
- Recorded `lr0`: 0.01
- Recorded `lrf`: 0.01
- Recorded momentum: 0.937
- Recorded weight decay: 0.0005
- Recorded image size: 640
- Recorded `pretrained`: `true`
- Recorded AMP: `true`
- Recorded validation enabled: `true`
- Recorded validation split: `val`
- Stored checkpoint epoch field: `-1`
- Stored `best_fitness`: `None`

The checkpoint contains eight entries for precision, recall, mAP50,
mAP50-95, and loss histories. The final entries in those stored histories are:

| Metric | Final stored series value |
|---|---:|
| Precision (B) | 0.82744 |
| Recall (B) | 0.74578 |
| mAP50 (B) | 0.81470 |
| mAP50-95 (B) | 0.57057 |

These are checkpoint training-result metadata, not a newly reproduced
evaluation. The repository does not include the dataset, the exact validation
split, an evaluation script, or a reproducible run log. They should therefore
be reported as **checkpoint-recorded values**, not as independently verified
generalization performance.

The evidence does **not** support describing this checkpoint as trained from
scratch. Its metadata explicitly records `pretrained: true` and a continued
run name. The exact original pretraining source and the complete prior
training history are **Not available in the current project evidence.**

### Person checkpoint: `models/yolo11n.pt`

Verified metadata:

- Ultralytics task: `detect`
- Architecture: `yolo11n.yaml`, scale `n`
- 80 COCO class names
- class 0 is `person`
- input image size: 640
- recorded data path: `/usr/src/ultralytics/ultralytics/cfg/datasets/coco.yaml`
- recorded `pretrained`: `true`
- recorded training-result series length: 600
- checkpoint date: `2024-09-25T21:10:26.629566`

The application does not use all 80 classes. `HumanDetector.detect()` passes
`classes=[0]`, so only the person class is emitted. The model is separate from
the weapon model because it supplies human localization used by the IoW
validation stage; the custom model supplies weapon detections.

The final stored checkpoint series values are:

| Metric | Final stored series value |
|---|---:|
| Precision (B) | 0.6563741360 |
| Recall (B) | 0.5024662662 |
| mAP50 (B) | 0.5514423440 |
| mAP50-95 (B) | 0.3939947731 |

As with the custom checkpoint, these are artifact metadata and not a
reproduced project evaluation.

### Model details not available

The following are **Not available in the current project evidence.**:

- verified dataset image counts
- dataset source identity beyond the paths embedded in the checkpoint
- class distribution
- train/validation/test file split
- annotation export details
- duplicate handling
- hardware model and memory
- training duration
- complete original training history for `best.pt`
- reproducible validation command
- confusion matrix
- deployment FPS
- deployment inference latency
- project-specific NMS setting

---

## D. Weapon classes and inference configuration

| Class ID | Class name | Role |
|---:|---|---|
| 0 | gun | custom weapon detector output |
| 1 | knife | custom weapon detector output |
| 2 | grenade | custom weapon detector output |
| 3 | missile | custom weapon detector output |
| 4 | sword | custom weapon detector output |

`WeaponDetector.detect()` runs YOLO prediction with the configured confidence
threshold, extracts integer `xyxy` coordinates, confidence, class ID, and
class name, and returns `Detection` records.

Verified runtime thresholds:

| Setting | Default | Source |
|---|---:|---|
| Weapon confidence | 0.25 | `config/settings.py` |
| Person confidence | 0.40 | `config/settings.py` |
| IoW validation threshold | 0.50 | `config/settings.py` |
| Event cooldown | 10 seconds | `config/settings.py` |
| Consecutive no-threat alarm dismissal | 15 frames | `config/settings.py` |
| Alarm duration timer | 5 seconds | `config/settings.py` |

Weapon confidence is mutable at runtime through the in-memory settings API.
IoW is also mutable through that API. The settings are not persisted to the
database.

---

## E. Human-weapon association and IoW formulation

For each weapon, `ThreatEngine.validate_threats()` evaluates every human.
For a weapon bounding box \(W\) and human bounding box \(H\):

\[
IoW(W,H) =
\frac{Area(W \cap H)}{Area(W)}
\]

The intersection uses axis-aligned rectangle coordinates:

\[
Area(W \cap H) =
\max(0, x_B-x_A)\times\max(0, y_B-y_A)
\]

The denominator is the weapon area, not union area. This answers the
question “what proportion of the detected weapon box overlaps the person
box?” rather than the conventional IoU question “what proportion of both
boxes is shared?”

For each weapon, the human with the largest IoW is selected. The weapon is
validated if:

\[
IoW \ge 0.50
\]

Zero-area weapons are skipped. A weapon without any human reaching the
threshold produces no `ValidatedThreat`. A human without a weapon also
produces no threat.

Explanatory example only: if weapon area is 1,000 pixels and intersection is
700 pixels, IoW is 0.70; with a 0.50 threshold it passes. This is not an
experimental result.

The intended engineering effect is to reject isolated or unassociated weapon
detections. The project contains no measured false-positive reduction study.

---

## F. Validated-threat logic

| Condition | Result |
|---|---|
| Weapon(s) and person(s), with one human reaching IoW threshold for a weapon | `ValidatedThreat`; event and alert path may run |
| Weapon detected but no human reaches threshold | no validated threat and no security event from that detection |
| Person detected without weapon | no weapon threat |
| Zero-area weapon box | skipped |

The validation stage is deterministic, frame-level, and does not perform
tracking or temporal identity association. Multiple weapons can create
multiple validated threats for one frame, subject to the source-specific
cooldown gate.

---

## G. Real-time and multi-source pipeline

### Supported paths

1. **Browser webcam:** browser obtains camera frames, encodes JPEG blobs, and
   sends them to `/ws/monitoring`.
2. **IP camera:** backend opens the supplied URL and appends `/video` when the
   URL does not already end in `/video`.
3. **RTSP:** backend opens the supplied RTSP source through OpenCV.
4. **Video file:** uploaded video is written to the temporary directory and
   then processed as a monitoring source.
5. **Uploaded image:** one multipart image is decoded and analyzed by the
   same inference service.

The project also contains `streams/stream_manager.py`, a unified generator
for webcam, IP camera, RTSP, video, and static image inputs. The active FastAPI
monitoring route uses `MonitoringSession` directly; the repository does not
demonstrate a separate production service using `StreamManager`.

### Session reliability mechanisms

- `MonitoringSession` owns one capture and one inference loop per monitoring
  WebSocket.
- `threading.Event` stop tokens terminate loops.
- `capture_generation` prevents an old capture/inference loop from continuing
  after a source restart.
- A duplicate start for the same active source is ignored.
- Starting a different source calls `stop()` first.
- Video files are removed during session stop.
- The frame queue has `maxsize=1`; when full, the old frame is discarded and
  the newest frame is retained.
- Browser frames use a “latest unprocessed frame” slot rather than an
  unbounded queue.
- The asynchronous WebSocket sender polls the queue and sends JSON frames.

The code does not establish simultaneous multi-camera orchestration. Each
monitoring WebSocket has a session; multi-camera scale-out is **Not available
in the current project evidence.**

---

## H. WebSocket and REST architecture

### WebSockets

#### `/ws/monitoring`

- No bearer-token validation is performed in the shown endpoint.
- Client sends `{type: "start", source, url/path}`.
- Client may send `{type: "stop"}`.
- Browser webcam clients send binary JPEG data.
- Server sends `frame` messages containing:
  `fps`, `persons`, `weapons`, `threat_status`, base64 `image`, and optional
  event summary.

#### `/ws/alerts`

- Requires the prototype token in the `token` query parameter.
- Sends `CONNECTION_STATE` on connection.
- Sends messages published by `AlertService`:
  `THREAT_DETECTED`, `EVIDENCE_READY`, and `ALERT_STATE_CHANGED`.
- Alert messages include event data and alarm state.
- The subscriber bridge uses an asyncio queue and thread-safe
  `call_soon_threadsafe`.

### REST API inventory

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/auth/login` | prototype credential login |
| GET | `/api/auth/me` | bearer-token identity |
| POST | `/api/auth/logout` | response-only logout |
| GET | `/api/dashboard/stats` | dashboard totals and placeholder active count |
| GET | `/api/settings` | read in-memory settings |
| POST | `/api/settings` | update in-memory IoW/confidence/cooldown settings |
| POST | `/api/analysis/image` | analyze uploaded image |
| POST | `/api/analysis/video` | save uploaded video to temp path |
| GET | `/api/events` | recent events |
| GET | `/api/events/{event_id}` | one event |
| GET | `/api/events/{event_id}/evidence` | protected evidence download |
| DELETE | `/api/events/{event_id}` | delete event and contained evidence |
| DELETE | `/api/events/clear` | delete all events and contained evidence |
| GET | `/api/alerts/active` | active alert synchronization |
| POST | `/api/alerts/events/{id}/acknowledge` | acknowledge active/new event |
| POST | `/api/alerts/events/{id}/mute` | authenticated `MUTE_ALARM` command |
| POST | `/api/alerts/events/{id}/review` | review or classify event |

REST is used for durable state retrieval and commands; WebSocket is used for
live delivery.

---

## I. Two-dashboard architecture

### Security Monitoring Dashboard

The main SPA uses the monitoring WebSocket for visual frames and exposes
overview, monitoring, image analysis, video analysis, events, and settings
views. It displays detections and threat banners. It does not implement
browser alarm playback.

### Authority Alert Dashboard

`frontend/authority.html` and `frontend/js/authority.js` provide:

- authenticated authority login
- live alert WebSocket connection
- active alert synchronization
- active event and recent-event presentation
- evidence loading and modal display
- weapon, confidence, IoW, source, timestamp, and event ID
- acknowledgement
- server-controlled `TURN OFF ALARM`
- alarm states including active, muted, and off

The dashboards do not communicate directly. Both consume the FastAPI backend,
which centralizes detection, persistence, evidence, alert fan-out, and alarm
state.

The implemented architecture has one detection service, one database, one
evidence store, one `AlertService`, and one `AlarmManager`. It does not prove
that every possible deployment process would remain single-process.

---

## J. Server-side alarm architecture and lifecycle correction

`AlertService` owns the only `AlarmManager`. `MonitoringSession` calls
`alert_service.alarm.update(has_threat)` for frame-level no-threat dismissal,
while newly persisted validated events call `AlertService.publish_threat()`
and then `AlarmManager.activate()` in a background thread.

The prior lifecycle defect was:

```text
Authority opens
  -> GET /api/alerts/active
  -> restore_active(active database rows)
  -> AlarmManager.activate()
```

This treated every persisted `ACTIVE` row as a newly active alarm. The
correction makes restoration observational: synchronization records seen IDs
and reports state but does not activate the alarm. A persisted muted event
restores the in-memory alarm state as muted without starting playback.

Alarm and threat states are separate:

| Threat / alert state | Alarm state |
|---|---|
| `ACTIVE` | `ACTIVE`, `MUTED`, or process-level off |
| `ACKNOWLEDGED` | `INACTIVE` after acknowledgement |
| `REVIEWED` / `FALSE_POSITIVE` | `INACTIVE` |

`MUTE_ALARM` does not acknowledge or review the threat. It stops the server
alarm and persists `alarm_state = MUTED`. Command IDs are remembered for
idempotent retries.

The current implementation does not provide a manual “turn on” command for a
muted existing threat.

---

## K. Evidence capture

Evidence is started after event creation and initial alert publication in a
daemon thread. `EvidenceCapture.save_evidence()`:

- copies the frame
- draws the weapon bounding box in red
- writes weapon class and confidence
- draws the human bounding box in yellow
- writes the IoW value
- stores a JPEG under `evidence/captures/YYYY/MM/DD/`
- returns the generated path

`AlertService.persist_evidence()` updates the database event and publishes
`EVIDENCE_READY`. This keeps the initial publication path separate from image
writing. The event ID is used in the database and evidence URL, but the JPEG
filename itself is generated by a separate UUID inside `EvidenceCapture`.

Evidence access resolves the requested path and checks that it is within the
resolved evidence directory using `is_relative_to`, preventing path traversal.
Evidence is returned only through an authenticated endpoint.

The repository does not contain measured evidence-write latency or a formal
evidence retention policy.

---

## L. Database and state model

### SecurityEvent fields

| Field | Type / meaning |
|---|---|
| `id` | UUID-like string primary key |
| `timestamp` | timezone-aware default timestamp |
| `weapon_type` | detected custom weapon class |
| `weapon_confidence` | weapon model confidence |
| `camera_source` | source label |
| `person_count` | integer, currently created as 1 |
| `evidence_path` | stored JPEG path |
| `iow` | validated IoW |
| `status` | `NEW`, `ACKNOWLEDGED`, `REVIEWED`, `FALSE_POSITIVE` |
| `alert_state` | `ACTIVE` or `INACTIVE` |
| `alarm_state` | `ACTIVE`, `MUTED`, or `INACTIVE` |
| `acknowledged_at` / `acknowledged_by` | acknowledgement audit fields |
| `reviewed_at` / `reviewed_by` | review audit fields |

Other tables are `users`, `cameras`, and `notifications`. The current
database contains 45 security events at audit time:

| Status | Alert state | Alarm state | Count |
|---|---|---|---:|
| NEW | ACTIVE | ACTIVE | 15 |
| NEW | ACTIVE | INACTIVE | 20 |
| NEW | INACTIVE | INACTIVE | 10 |

These are current database contents, not a performance result.

### State transitions

```text
ValidatedThreat
  -> SecurityEvent(status=NEW, alert_state=ACTIVE, alarm_state=ACTIVE)

ACTIVE + MUTE_ALARM
  -> status=NEW, alert_state=ACTIVE, alarm_state=MUTED

NEW + ACKNOWLEDGE_ALERT
  -> status=ACKNOWLEDGED, alert_state=INACTIVE, alarm_state=INACTIVE

ACTIVE + REVIEW(REVIEWED/FALSE_POSITIVE)
  -> corresponding status, alert_state=INACTIVE, alarm_state=INACTIVE
```

The database is the durable source for events and evidence references.
In-memory subscriber queues, command-result memory, cooldown state, and the
pygame playback state are process-local.

---

## M. Exact alert lifecycle

```text
VALIDATED THREAT
      ↓
EVENT CREATED
      ↓
DATABASE COMMIT
      ↓
THREAT_DETECTED published
      ↓
central AlarmManager.activate()
      ↓
authority /ws/alerts receives message
      ↓
  ┌───────────────┬─────────────────┬────────────────┐
  │ MUTE_ALARM    │ ACKNOWLEDGE     │ REVIEW         │
  ↓               ↓                 ↓
threat remains    ACKNOWLEDGED      REVIEWED or
ACTIVE            + INACTIVE        FALSE_POSITIVE
alarm MUTED      alarm INACTIVE    + INACTIVE
```

Dashboard refresh and WebSocket reconnect retrieve state but do not activate
an old event. Historical events can appear in recent alerts without restarting
the alarm.

---

## N. Alert-first delivery and timing markers

The implemented threat path is:

```text
Validated threat
  -> event ID / database commit
  -> lightweight THREAT_DETECTED publication
  -> alarm activation thread
  -> authority WebSocket/UI
  -> background evidence persistence
  -> EVIDENCE_READY
  -> mock notification dispatch
```

The code contains the following timing markers:

| Marker | Code location / meaning |
|---|---|
| `T0` | event processing begins before repository creation |
| `T1` | repository event insertion begins |
| `T2` | database commit completes |
| `T3` | `publish_threat()` publishes the threat |
| `T4` | authority alert WebSocket sends a message |
| `T5` | authority browser receives a WebSocket message |
| `T6` | authority UI renders the event |
| `A0` | alert service requests activation |
| `A1` | `AlarmManager.activate()` begins |
| `A2` | pygame mixer initialization |
| `A3` | buzzer load completed |
| `A4` | playback/timer activation path completed |

The logs contain nanosecond timestamps from `perf_counter_ns`, but the
repository does not contain an analyzed latency report. Numerical live
latency measurement was **Not available in the current project evidence.**

---

## O. Reliability and concurrency assessment

Positive mechanisms:

- per-session stop event
- generation ID stale-loop protection
- duplicate-start guard
- latest-frame backpressure
- queue size of one for monitoring frames
- `finally` cleanup for capture and WebSocket sessions
- thread-to-event-loop alert queue bridge
- command-result idempotency map

Engineering risks requiring future evaluation:

- `AlertService._seen_events`, `_commands`, and subscribers are process-local.
- SQLite and in-memory state are not a demonstrated clustered deployment.
- monitoring WebSocket authentication is not implemented in
  `monitoring_ws.py`.
- `MonitoringSession` calls the shared alarm’s `update()` for each monitoring
  session, so concurrent sessions would share alarm no-threat counters.
- a process restart loses in-memory command history and pygame state.

These are reliability observations, not measured failure rates.

---

## P. Security audit

Verified controls:

- bearer-token dependency for protected REST endpoints
- role check allowing `admin`, `authority`, or `operator`
- token check on `/ws/alerts`
- command ID replay/idempotency lookup for alert commands
- active-event validation for mute
- explicit `MUTE_ALARM` command type validation
- evidence path containment check
- MIME/decode validation for image and video upload endpoints
- evidence endpoint authentication

Important prototype limitations:

- token is a fixed constant (`prototype_token_123`)
- login compares configured evaluation credentials
- default credentials are documented in the README
- CORS allows all origins
- `/ws/monitoring` accepts connections without the authority bearer-token
  check
- settings update endpoint has no authentication dependency
- event deletion uses general current-user authentication rather than the
  authority dependency

No security penetration test or threat model is present.

---

## Q. Experimental methodology for the future paper

No new experimental results should be claimed from this audit. The following
are proposed protocols.

### Detection performance

Use a held-out, labeled test set disjoint from training data. Report
per-class and aggregate precision, recall, F1, mAP50, and mAP50-95 with the
exact confidence/NMS settings. Include class-wise support and confidence
curves.

### Threat validation ablation

Compare:

1. weapon detector alone
2. weapon detector plus person detection
3. weapon plus person plus IoW validation

Measure false positives, false negatives, precision, recall, and event-level
agreement against frame/event labels.

### IoW threshold study

Evaluate proposed thresholds such as 0.30, 0.40, 0.50, 0.60, and 0.70 on
the same held-out association set. These values are proposed settings, not
existing project results.

### Real-time performance

Record hardware, resolution, source type, frame rate, model inference time,
event creation time, evidence completion time, WebSocket delivery time, and
alarm activation time. Use the existing T0-T6 and A0-A4 markers, but report
distributions rather than isolated values.

### Source comparison

Run the same labeled scenarios through webcam, IP camera, RTSP, uploaded
image, and video. Report dropped frames, decode failures, FPS, alert latency,
and event consistency.

### Alert reliability

Test repeated threats, persistent threats, cooldown behavior, dashboard
refresh, WebSocket reconnect, mute persistence, acknowledgement, historical
events, evidence failures, and process restart. Verify that dashboard
synchronization never starts the alarm.

---

## R. Dataset and training evidence

The project does not include the dataset directory, annotation files, data
YAML, training script, experiment notebook, or hardware log. The custom model
checkpoint records a dataset path and five names, but not the dataset contents.

The following are **Not available in the current project evidence.**:

- total image count
- source organizations or collection procedure
- class distribution
- train/validation/test counts
- annotation format and quality process
- preprocessing and augmentation history beyond checkpoint arguments
- duplicate handling
- low-light, occlusion, camera-angle, or small-object coverage
- dataset license and consent details
- hardware used by the developer

The checkpoint does record `augment: false` in its stored training arguments,
but this should not be generalized to all prior training stages.

The evidence does not establish training from scratch. The custom artifact
records `pretrained: true` and a continued-run name. The precise initial
weights and earlier run are unavailable.

---

## S. Related-work positioning

Relevant literature areas for a later paper:

- YOLO-family real-time object detection
- custom weapon detection
- CCTV and public-safety computer vision
- human-object spatial association
- IoU/IoW-style geometric validation
- false-alarm reduction in surveillance
- evidence-backed alert systems
- WebSocket and low-latency event delivery
- edge and server-side real-time inference
- human-in-the-loop authority review

External literature is required. The repository contains no references or
citation list.

---

## T. Implementation contributions versus potential research contributions

| Area | Implemented fact | Evidence needed before calling it a research contribution |
|---|---|---|
| Custom weapon model | five-class YOLO detection checkpoint | reproducible dataset/training description and benchmark |
| Separate person model | YOLO11n restricted to person class | association benchmark and failure analysis |
| IoW validation | highest-human IoW, threshold 0.50 | threshold sweep and ablation |
| Validated-threat event architecture | events only for validated threats | event-level ground-truth evaluation |
| Evidence-backed events | asynchronous annotated JPEG evidence | evidence completeness and timing study |
| Centralized alarm | one process-level AlarmManager | concurrency and deployment reliability tests |
| Two dashboards | monitoring and authority views share backend | usability and operational evaluation |
| Alert-first delivery | publish before asynchronous evidence save | latency distributions against a blocking baseline |
| Threat/alarm separation | `alert_state` and `alarm_state` are separate | restart, mute, and lifecycle reliability tests |
| Multi-source support | webcam, IP, RTSP, image, video paths exist | cross-source benchmark and simultaneous-load test |

These are potential contributions or engineering design points, not proven
novel claims.

---

## U. Recommended paper figures

| Figure | Title | Source | Purpose |
|---:|---|---|---|
| 1 | Overall System Architecture | `backend/main.py`, service modules | end-to-end components |
| 2 | Dual YOLO Detection Pipeline | `weapon_detector.py`, `human_detector.py` | model separation |
| 3 | Human-Weapon IoW Validation | `threat_engine.py` | geometric formula |
| 4 | Validated Threat Decision Flow | `inference_service.py` | threat cases |
| 5 | Alert Lifecycle | repository and alert service | durable state transitions |
| 6 | Evidence/Event Pipeline | `capture.py`, `alert_service.py` | asynchronous evidence |
| 7 | Two-Dashboard Architecture | frontend and WebSocket routes | shared backend roles |
| 8 | WebSocket Alert Communication | `alerts_ws.py`, authority JS | live delivery |
| 9 | Alert-First Timing Architecture | T0-T6 and A0-A4 | proposed latency instrumentation |
| 10 | Authority Alarm State Machine | alarm and alert API | active, muted, off behavior |

Do not create experimental graphs until the proposed experiments have been
run. Architecture figures can be derived from the code.

---

## V. Recommended technical tables

1. Software stack: Python, FastAPI, Ultralytics, PyTorch, OpenCV, SQLAlchemy,
   SQLite, vanilla JavaScript, WebSockets, pygame.
2. Hardware/training environment: report only after developer training logs
   or hardware records are supplied; currently unavailable.
3. AI models: `best.pt` YOLO11s custom detector and `yolo11n.pt` person source.
4. Weapon classes: five verified classes and IDs.
5. Detection thresholds: weapon 0.25, person 0.40, IoW 0.50.
6. Threat validation rules: weapon/person/IoW cases.
7. Database/event fields: `SecurityEvent` schema.
8. REST APIs: endpoint, method, authentication, purpose.
9. WebSocket messages: monitoring frame and authority alert messages.
10. Dashboard responsibilities: monitoring versus authority.
11. Security mechanisms and prototype limitations.
12. Testing/validation: actual automated results plus clearly labeled missing
    experiments.

---

## W. Recommended future work

Prioritized future work based on the current architecture:

1. Add a reproducible dataset manifest, training script, split definition, and
   evaluation command.
2. Evaluate the IoW threshold and compare against weapon-only detection.
3. Add temporal tracking or consecutive-frame threat confirmation.
4. Add authenticated monitoring WebSockets and authenticated settings writes.
5. Replace fixed prototype authentication with durable identity/session
   management.
6. Add persistent command/audit records and multi-process alarm coordination.
7. Add multi-camera orchestration and resource limits.
8. Add model optimization, quantization, or TensorRT only after baseline
   measurements.
9. Improve evidence metadata by storing event ID, capture timestamp, and
   source metadata explicitly.
10. Evaluate official emergency notification integrations only with suitable
    operational and privacy controls.

---

## X. Recommended future paper structure

| Section | Content from this project | Additional evidence required |
|---|---|---|
| Title | validated weapon surveillance and alert architecture | final research claim |
| Abstract | system and measured findings | actual experiments |
| Keywords | weapon detection, IoW, surveillance, alerting | literature alignment |
| 1. Introduction | public-safety problem and motivation | citations and scope |
| 2. Problem Statement | isolated detections versus person-associated threats | formal dataset definition |
| 3. Related Work | YOLO, surveillance, association, alert systems | external literature |
| 4. Proposed System | implemented pipeline | precise contribution boundary |
| 5. System Architecture | code-derived architecture | deployment diagram |
| 6. Dataset and Data Preparation | only verified checkpoint facts | dataset manifest |
| 7. Model Training | checkpoint metadata | complete reproducible training record |
| 8. Weapon Detection | classes, boxes, confidence | test metrics |
| 9. Human-Weapon Association | IoW formula and best-human rule | labeled association study |
| 10. IoW-Based Validation | threshold and cases | threshold/ablation results |
| 11. Real-Time Alert Architecture | WebSockets, event service, alarm | latency distributions |
| 12. Evidence/Event Management | database and asynchronous evidence | reliability measurements |
| 13. Authority Dashboard | live review, acknowledgement, mute | usability/operational evaluation |
| 14. Experimental Methodology | proposed protocols in this document | finalized protocol |
| 15. Results | measured detection and system metrics | not currently available |
| 16. Discussion | trade-offs and failure modes | results-supported analysis |
| 17. Limitations | dataset, prototype security, scale | field validation |
| 18. Future Work | tracking, scale, optimization | implementation roadmap |
| 19. Conclusion | bounded conclusions | no unsupported superiority claims |
| References | related work | external literature required |

---

## Y. Verified validation results

At audit time:

- Python compilation of the project modules: passed in the prior engineering
  validation.
- Focused automated tests: 7 passed.
- The full suite included a browser test that requires a running server; its
  failure without a server is an environment/setup failure, not a model
  metric.
- Threat-engine tests cover no overlap, full overlap, below-threshold
  overlap, and selection of the best human.
- The SQLite database contained 45 events and the state aggregate shown above.
- Model metadata was successfully read from both `.pt` files.

No live detection benchmark, live FPS benchmark, field trial, confusion
matrix, or independently reproduced model evaluation was performed as part
of this audit.

---

## Z. Claims that must not be made without additional experiments

Do not claim any of the following from the current repository alone:

- the model is trained from scratch
- state-of-the-art or best performance
- superior performance over YOLO or another baseline
- a particular real-world accuracy
- a particular precision, recall, F1, mAP, or confusion matrix result
- a particular FPS, latency, or throughput
- reduced false positives by a measured percentage
- robust operation in low light, occlusion, or crowded scenes
- simultaneous multi-camera scalability
- production-grade authentication or security
- reliable emergency notification delivery
- novelty of IoW association without literature comparison
- effectiveness of the mute/restart correction without lifecycle tests
- generalization to weapons or scenes absent from the verified dataset
- a known training dataset size, distribution, or hardware environment

The defensible current conclusion is that the project implements a
two-detector, IoW-validated, evidence-backed, server-alert surveillance
prototype with separate monitoring and authority interfaces. Its scientific
effectiveness and research novelty require the experiments and external
literature review described above.
