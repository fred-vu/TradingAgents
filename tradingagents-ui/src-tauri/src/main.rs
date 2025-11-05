#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    env,
    io,
    path::PathBuf,
    process::{Child, Command, Stdio},
    sync::Mutex,
};

use tauri::{AppHandle, Manager, RunEvent};

struct BackendState {
    child: Mutex<Option<Child>>,
}

impl BackendState {
    fn new() -> Self {
        Self {
            child: Mutex::new(None),
        }
    }

    fn replace(&self, child: Child) {
        if let Ok(mut guard) = self.child.lock() {
            *guard = Some(child);
        }
    }

    fn stop(&self) {
        if let Ok(mut guard) = self.child.lock() {
            if let Some(mut child) = guard.take() {
                let _ = child.kill();
            }
        }
    }
}

fn preferred_python() -> PathBuf {
    if let Ok(explicit) = env::var("TRADINGAGENTS_PYTHON") {
        let path = PathBuf::from(explicit);
        if path.exists() {
            return path;
        }
    }

    if let Ok(venv) = env::var("VIRTUAL_ENV") {
        let mut candidate = PathBuf::from(&venv);
        if cfg!(target_os = "windows") {
            candidate.push("Scripts");
            candidate.push("python.exe");
        } else {
            candidate.push("bin");
            candidate.push("python");
        }
        if candidate.exists() {
            return candidate;
        }
    }

    if cfg!(target_os = "windows") {
        PathBuf::from("python.exe")
    } else {
        PathBuf::from("python3")
    }
}

fn locate_backend_script(app: &AppHandle) -> Option<PathBuf> {
    if let Ok(explicit) = env::var("TRADINGAGENTS_BACKEND_SCRIPT") {
        let candidate = PathBuf::from(explicit);
        if candidate.exists() {
            return Some(candidate);
        }
    }

    let resource_candidates = [
        "run_backend.py",
        "../run_backend.py",
        "../../run_backend.py",
    ];

    for candidate in resource_candidates {
        if let Some(path) = app.path_resolver().resolve_resource(candidate) {
            if path.exists() {
                return Some(path);
            }
        }
    }

    let cwd = env::current_dir().unwrap_or_else(|_| PathBuf::from("."));
    for relative in &["run_backend.py", "../run_backend.py"] {
        let candidate = cwd.join(relative);
        if candidate.exists() {
            return Some(candidate);
        }
    }

    None
}

fn spawn_backend(app: &AppHandle) -> tauri::Result<Child> {
    let script_path = locate_backend_script(app).ok_or_else(|| {
        io::Error::new(io::ErrorKind::NotFound, "run_backend.py not found")
    })?;

    let python = preferred_python();

    Command::new(python)
        .arg(script_path)
        .stdin(Stdio::null())
        .stdout(Stdio::null())
        .stderr(Stdio::null())
        .spawn()
        .map_err(tauri::Error::from)
}

fn main() {
    tauri::Builder::default()
        .manage(BackendState::new())
        .setup(|app| {
            let backend_state = app.state::<BackendState>();
            let app_handle = app.handle();
            if let Ok(child) = spawn_backend(&app_handle) {
                backend_state.replace(child);
            } else {
                println!("warning: failed to spawn FastAPI backend. Launch manually with `python run_backend.py --reload`.");
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|app_handle, event| {
            if matches!(event, RunEvent::Exit | RunEvent::ExitRequested { .. }) {
                if let Some(state) = app_handle.try_state::<BackendState>() {
                    state.stop();
                }
            }
        });
}
