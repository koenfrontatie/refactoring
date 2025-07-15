the-judge-app/                 # repo root
│
├─ python/                        
│  └─ the_judge/               # one installable package  →  
│     ├─ __init__.py           # tiny: version + public re-exports only
│     │
│     ├─ settings/             # env & config parsing
│     │   ├─ __init__.py       # get_settings() accessor (cached)
│     │   └─ base.py           # class Settings(BaseSettings, frozen=True)
│     │
│     ├─ domain/               # pure business objects & rules (no IO)
│     │   ├─ __init__.py
│     │   ├─ camera.py         # Entity: Camera(id, location, fov)
│     │   ├─ visitor.py        # Entity: Visitor(...)
│     │   ├─ post.py           # Entity: Post(...)
│     │   ├─ events.py         # DomainEvent classes (VisitorSeen, PostCreated…)
│     │   └─ repositories.py   # Protocols: VisitorRepository, PostRepository, ...
│     │
│     ├─ application/          # orchestrates use-cases
│     │   ├─ __init__.py
│     │   ├─ dtos.py           # GeneratePostInput / Result, VisitorSnapshot…
│     │   ├─ unit_of_work.py   # UoW interface (visitors, posts, frames…)
│     │   │
│     │   ├─ services/         # thin façades that chain commands
│     │   │   ├─ camera_service.py
│     │   │   ├─ tracking_service.py
│     │   │   └─ content_service.py
│     │   │
│     │   ├─ commands/         # write-side CQRS
│     │   │   ├─ capture_frame.py          # CaptureFrameCommand
│     │   │   ├─ process_frame.py          # ProcessFrameCommand
│     │   │   └─ generate_post.py          # GeneratePostCommand
│     │   │
│     │   └─ queries/          # read-side CQRS
│     │       ├─ recent_visitors.py        # RecentVisitorsQuery
│     │       └─ visitor_report.py
│     │
│     ├─ infrastructure/       # adapters / drivers (IO, frameworks)
│     │   ├─ __init__.py
│     │   │
│     │   ├─ db/
│     │   │   ├─ engine.py                     # create_engine, session factory
│     │   │   ├─ models/                       # SQLAlchemy tables
│     │   │   │   ├─ __init__.py
│     │   │   │   ├─ visitor_model.py
│     │   │   │   ├─ post_model.py
│     │   │   │   └─ frame_model.py
│     │   │   └─ repositories/                 # concrete repos
│     │   │       ├─ __init__.py
│     │   │       ├─ visitor_repo.py
│     │   │       └─ post_repo.py
│     │   │
│     │   ├─ hardware/                         # camera drivers
│     │   │   ├─ __init__.py
│     │   │   ├─ base.py                       # ICameraAdapter Protocol
│     │   │   ├─ usb_camera.py
│     │   │   └─ remote_camera.py
│     │   │
│     │   ├─ vision/                           # ML pipelines
│     │   │   ├─ __init__.py
│     │   │   ├─ detector.py
│     │   │   ├─ tracker.py
│     │   │   └─ face_embedder.py
│     │   │
│     │   └─ external/                         # 3rd-party APIs
│     │       ├─ openai_client.py
│     │       ├─ photomaker.py
│     │       └─ notification_service.py
│     │
│     ├─ presentation/         # delivery mechanisms (no business logic)
│     │   ├─ __init__.py
│     │   ├─ socket/              
│     │   │   ├─ __init__.py
│     │   │   ├─ client.py
│     │   │   └─ handlers/
│     │   │       ├─ __init__.py
│     │   │       ├─ tracking.py	# @sio.event handlers call application commands
│     │   │       └─ content.py
│     │   └─ cli/              # Typer command-line entry
│     │       └─ main.py
│     │
│     ├─ common/               # cross-cutting helpers (no IO)
│     │   ├─ __init__.py
│     │   ├─ logger.py
│     │   └─ validation.py
│     │
│     └─ main.py               # ASGI / CLI bootstrap (imports presentation)
│
├─ tests/                      # pytest tree mirrors src
│   ├─ __init__.py
│   ├─ unit/
│   │   ├─ test_camera_service.py
│   │   └─ test_generate_post_command.py
│   └─ integration/
│       └─ test_frame_ingest.py
│
├─ scripts/                    # one-off jobs & diagnostics
│   ├─ backfill_embeddings.py
│   └─ socket_tester.py
│
└─ README.md


the_judge/
├─ presentation/
│  └─ socket/              # ← new socket-facing boundary
│      ├─ __init__.py
│      ├─ client.py        
│      └─ handlers.py      # @sio.event handlers call application commands
└─ infrastructure/
   └─ messaging/
       ├─ sse_broadcaster.py
       └─ socketio_broadcaster.py   # optional: push DomainEvents to clients




domain/
├─ __init__.py          # root re‑exports           ← import domain as dj
├─ tracking/            # ← bounded context ➊
│   ├─ __init__.py      # public API for tracking  ← import domain.tracking as dt
│   ├─ entities.py      # Visitor, Session, Frame
│   ├─ control.py       # TrackingCmd enum (if any)
│   ├─ events.py        # VisitorSeen, FrameReady
│   └─ repositories.py  # Protocols: VisitorRepo, FrameRepo
└─ content/             # ← bounded context ➋
    ├─ __init__.py      # public API for content   ← import domain.content as dc
    ├─ entities.py      # Post, Asset
    ├─ control.py       # ContentOp enum (Generate, Publish…)
    ├─ events.py        # PostCreated
    └─ repositories.py  # PostRepo, AssetRepo
