our main working directory: C:\Users\koenv\Documents\Dev\NodeProjects\refactoring

our reference project: the-judge-app

we are refactoring my the-judge-app python code.

i want to move to a DDD setup

in refactoring/python/tree_output.txt you can see current file structure

your code style must be pythonic
we are using domain driven design and the repository pattern (dto uow)
we make use of libraries SQLAlchemy 
avoid using emojis
commands come in via /network/socket.python

do not make changes excessively, ask for confirmation when you decide on things.

i want you to brainstorm with me in how we can best approach this. i would like to start with the tracking functionality of the-judge-app.


you should have access to the new folder now. we will not write migration scripts. we are gonna start with the camera system -> processing system

here is an outline of my ideas for the structure

python/                        # language silo; venv + code live here
├─ venv/                       # local virtual‑env (git‑ignored)
├─ requirements.txt            # pinned deps for dev/CI
└─ src/                        # import‑root guard (prevents shadowing)
   └─ the_judge/               # installable package  →  import the_judge
      │
      ├─ __init__.py           # version + public re‑exports only
      │
      ├─ settings/             # config parsed from .env / env‑vars
      │   ├─ __init__.py
      │   └─ base.py           # class Settings(BaseSettings…)
      │
      ├─ common/               # cross‑cutting, no I/O
      │   ├─ __init__.py
      │   ├─ logger.py         # setup_logger() wrapper around std‑log
      │   └─ validation.py     # shared Pydantic / dataclass helpers
      │
      ├─ domain/               # business language, zero tech deps
      │   ├─ __init__.py
      │   ├─ tracking/         # visitor / camera bounded‑context
      │   │   ├─ __init__.py
      │   │   ├─ entities.py        # Camera, Visitor, Frame
      │   │   ├─ control.py         # CamCmd enum (CAPTURE, LOOP_ON…)
      │   │   ├─ events.py          # VisitorSeen, FrameReady
      │   │   └─ repositories.py    # Protocols: VisitorRepo, FrameRepo
      │   └─ content/          # AI‑post bounded‑context (later steps)
      │       ├─ __init__.py
      │       ├─ entities.py        # Post, Asset
      │       ├─ control.py         # ContentOp enum
      │       ├─ events.py          # PostCreated
      │       └─ repositories.py    # PostRepo protocol
      │
      ├─ application/          # orchestrates domain use‑cases
      │   ├─ __init__.py
      │   ├─ dtos.py                # in‑process DTOs (FrameDTO …)
      │   ├─ unit_of_work.py        # abstract UoW interface
      │   ├─ services/              # coarse‑grain behaviours
      │   │   ├─ camera_service.py      # control loop / capture
      │   │   ├─ tracking_service.py    # detect → embed → match
      │   │   └─ content_service.py     # generate & publish posts
      │   ├─ commands/             # write‑side wrappers (opt)
      │   │   ├─ capture.py             # CaptureNowCommand
      │   │   ├─ process_frames.py      # batch ingest job
      │   │   └─ toggle_capture.py
      │   └─ queries/              # read‑side helpers
      │       └─ recent_visitors.py     # list last‑30‑min visitors
      │
      ├─ infrastructure/         # tech‐specific adapters
      │   ├─ __init__.py
      │   ├─ db/                      # SQLAlchemy layer
      │   │   ├─ __init__.py
      │   │   ├─ engine.py                # engine+sessionmaker factory
      │   │   ├─ sqlalchemy_uow.py        # concrete UnitOfWork
      │   │   ├─ models/                  # ORM tables
      │   │   │   ├─ __init__.py
      │   │   │   ├─ tracking_models.py       # VisitorModel, FrameModel
      │   │   │   └─ content_models.py        # PostModel, AssetModel
      │   │   └─ repositories/            # concrete repo impls
      │   │       ├─ __init__.py
      │   │       ├─ tracking_repo.py         # SqlVisitorRepo…
      │   │       └─ content_repo.py
      │   │
      │   ├─ vision/                  # ML wrappers (heavy libs)
      │   │   ├─ detector.py              # YOLO face detector
      │   │   ├─ face_embedder.py         # ArcFace / FaceNet embedding
      │   │   └─ matcher.py               # cosine or Faiss search
      │   │
      │   ├─ network/                 # outbound protocols
      │   │   ├─ socket.py                # WsClient (python‑socketio)
      │   │   └─ handlers.py              # translate WS events ⇆ services
      │   │
      │   ├─ hardware/                # camera drivers (USB / RTSP)
      │   │   ├─ __init__.py
      │   │   ├─ base.py                  # ICameraAdapter Protocol
      │   │   ├─ usb_camera.py
      │   │   └─ remote_camera.py         # WebSocket proxy camera
      │   │
      │   └─ external/                # SaaS / HTTP APIs
      │       ├─ openai_client.py         # GPT image/meme generation
      │       ├─ photomaker_client.py     # PhotoMaker REST wrapper
      │       └─ sse_notifyer.py          # push events to browser SSE
      │
      ├─ presentation/             # system entrypoints, no biz‑logic
      │   ├─ __init__.py
      │   └─ cli/
      │       └─ main.py               # wire services + socket client, block
      │
      └─ main.py                  # tiny – delegates to presentation.cli
