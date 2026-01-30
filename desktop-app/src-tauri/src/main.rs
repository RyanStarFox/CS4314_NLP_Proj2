// Prevents additional console window on Windows in release, DO NOT REMOVE!!
#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Child, Command, Stdio};
use std::sync::Mutex;
use std::env;
use std::fs;
use std::io::Write;
use std::collections::HashMap;
use std::path::PathBuf;
use tauri::{
    menu::{Menu, MenuItem, PredefinedMenuItem, Submenu},
    Emitter, Listener, Manager,
};

// Global state to hold the Python process and logs
struct AppState {
    python_process: Mutex<Option<Child>>,
    log_buffer: Mutex<Vec<(String, bool)>>, // (message, is_error)
}

fn get_python_executable() -> PathBuf {
    let exe_dir = env::current_exe()
        .ok()
        .and_then(|p| p.parent().map(|p| p.to_path_buf()))
        .unwrap_or_else(|| PathBuf::from("."));
    
    #[cfg(target_os = "windows")]
    let python_binary = "python-backend.exe";
    
    #[cfg(not(target_os = "windows"))]
    let python_binary = "python-backend";

    // PyInstaller 'onedir' creates a folder with the same name as the binary
    let python_folder = "python-backend";

    let check_path = |base_path: PathBuf| -> Option<PathBuf> {
        // Case A: onedir structure -> base/python-backend/python-backend.exe
        let candidate_onedir = base_path.join(python_folder).join(python_binary);
        if candidate_onedir.exists() {
             return Some(candidate_onedir);
        }
        
        // Case B: flattened/onefile structure -> base/python-backend.exe
        let candidate_flat = base_path.join(python_binary);
        if candidate_flat.exists() {
             return Some(candidate_flat);
        }
        None
    };
    
    // 1. Direct check in current directory
    if let Some(p) = check_path(exe_dir.clone()) { return p; }

    // 2. Dev mode checks
    if let Some(p) = check_path(exe_dir.join("../../python-dist")) { return p; }
    if let Some(p) = check_path(exe_dir.join("../python-dist")) { return p; }
    
    // 3. MacOS Bundle checks
    #[cfg(target_os = "macos")]
    {
         if let Some(p) = check_path(exe_dir.join("../Resources/_up_/python-dist")) { return p; }
         if let Some(p) = check_path(exe_dir.join("../Resources/python-dist")) { return p; }
         if let Some(p) = check_path(exe_dir.join("../Resources")) { return p; }
    }

    // 4. Windows Bundled checks
    // Check likely resource locations for Tauri v1/v2
    if let Some(p) = check_path(exe_dir.join("resources/python-dist")) { return p; }
    if let Some(p) = check_path(exe_dir.join("python-dist")) { return p; }
    if let Some(p) = check_path(exe_dir.join("_up_/python-dist")) { return p; }

    // Fallback log path (for debugging, point to the deep structure)
    exe_dir.join("python-dist").join(python_folder).join(python_binary)
}

#[tauri::command]
fn get_logs(state: tauri::State<AppState>) -> Vec<(String, bool)> {
    let logs = state.log_buffer.lock().unwrap();
    logs.clone()
}

#[tauri::command]
fn get_settings(app: tauri::AppHandle) -> HashMap<String, String> {
    let mut settings = HashMap::new();
    
    // Get user data dir
    if let Ok(path) = app.path().app_data_dir() {
        let env_path = path.join(".env");
        if env_path.exists() {
            if let Ok(content) = fs::read_to_string(env_path) {
                for line in content.lines() {
                    let line = line.trim();
                    if line.is_empty() || line.starts_with('#') { continue; }
                    if let Some((key, value)) = line.split_once('=') {
                        settings.insert(key.trim().to_string(), value.trim().to_string());
                    }
                }
            }
        }
    }
    settings
}

#[tauri::command]
fn save_settings(app: tauri::AppHandle, settings: HashMap<String, String>) -> Result<(), String> {
    let path = app.path().app_data_dir().map_err(|e| e.to_string())?;
    if !path.exists() {
        fs::create_dir_all(&path).map_err(|e| e.to_string())?;
    }
    
    let env_path = path.join(".env");
    
    // Read existing lines to preserve comments
    let mut lines = Vec::new();
    if env_path.exists() {
        if let Ok(content) = fs::read_to_string(&env_path) {
            for line in content.lines() {
                lines.push(line.to_string());
            }
        }
    }
    
    let mut new_lines = Vec::new();
    let mut updated_keys = Vec::new();
    
    for line in lines {
        let trimmed = line.trim();
        if !trimmed.is_empty() && !trimmed.starts_with('#') {
            if let Some((key, _)) = trimmed.split_once('=') {
                let key = key.trim();
                if let Some(val) = settings.get(key) {
                    new_lines.push(format!("{}={}", key, val));
                    updated_keys.push(key.to_string());
                    continue;
                }
            }
        }
        new_lines.push(line);
    }
    
    // Append new keys
    for (key, val) in &settings {
        if !updated_keys.contains(key) {
            new_lines.push(format!("{}={}", key, val));
        }
    }
    
    let mut file = fs::File::create(env_path).map_err(|e| e.to_string())?;
    for line in new_lines {
        writeln!(file, "{}", line).map_err(|e| e.to_string())?;
    }
    
    Ok(())
}

fn emit_and_buffer(app: &tauri::AppHandle, state: &tauri::State<AppState>, message: String, is_error: bool) {
    // 1. Buffer log
    if let Ok(mut logs) = state.log_buffer.lock() {
        logs.push((message.clone(), is_error));
        // Keep buffer size reasonable (e.g., last 1000 lines)
        if logs.len() > 1000 {
            logs.remove(0);
        }
    }
    
    // 2. Emit event
    let event_name = if is_error { "python-error" } else { "python-log" };
    let _ = app.emit(event_name, message);
}

fn start_python_backend(app: &tauri::AppHandle) -> Option<Child> {
    let python_exe = get_python_executable();
    let app_handle = app.clone();
    let state = app.state::<AppState>();
    
    let msg = format!("Starting Python backend from: {:?}", python_exe);
    println!("{}", msg);
    emit_and_buffer(app, &state, msg, false);
    
    if !python_exe.exists() {
        let err_msg = format!("Python backend not found at: {:?}", python_exe);
        eprintln!("{}", err_msg);
        emit_and_buffer(app, &state, err_msg, true);
        return None;
    }
    
    let working_dir = python_exe.parent().unwrap_or(&python_exe);
    
    let mut child = Command::new(&python_exe)
        .current_dir(working_dir)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .expect("Failed to spawn python backend");

    let pid_msg = format!("Python backend started with PID: {}", child.id());
    println!("{}", pid_msg);
    emit_and_buffer(app, &state, pid_msg, false);

    let stdout = child.stdout.take().expect("Failed to open stdout");
    let stderr = child.stderr.take().expect("Failed to open stderr");

    let app_handle_out = app_handle.clone();
    std::thread::spawn(move || {
        use std::io::{BufRead, BufReader};
        let reader = BufReader::new(stdout);
        for line in reader.lines() {
            if let Ok(line) = line {
                println!("[Python] {}", line);
                let state = app_handle_out.state::<AppState>();
                emit_and_buffer(&app_handle_out, &state, line, false);
            }
        }
    });

    let app_handle_err = app_handle.clone();
    std::thread::spawn(move || {
        use std::io::{BufRead, BufReader};
        let reader = BufReader::new(stderr);
        for line in reader.lines() {
            if let Ok(line) = line {
                eprintln!("[Python Error] {}", line);
                let state = app_handle_err.state::<AppState>();
                emit_and_buffer(&app_handle_err, &state, line, true);
            }
        }
    });

    Some(child)
}

/*
fn create_main_menu(app: &tauri::AppHandle) -> tauri::Result<Menu> {
    // ... code commented out due to compilation errors ...
    Ok(Menu::new(app)?)
}
*/

fn cleanup_python(app_handle: &tauri::AppHandle) {
    let state = app_handle.state::<AppState>();
    // Split the lock call and the match to force lifetime ordering
    let lock_result = state.python_process.lock();
    if let Ok(mut guard) = lock_result {
        if let Some(child) = guard.as_mut() {
            println!("Stopping Python backend (PID: {})...", child.id());
            let _ = child.kill();
            let _ = child.wait();
        }
    }
}

fn main() {
    let state = AppState {
        python_process: Mutex::new(None),
        log_buffer: Mutex::new(Vec::new()),
    };
    
    tauri::Builder::default()
        .manage(state)
        .plugin(tauri_plugin_shell::init())
        .invoke_handler(tauri::generate_handler![
            get_logs, 
            get_settings, 
            save_settings
        ])
        .setup(|app| {
            /*
            // Setup Menu code commented out...
            */

            // Start Python backend on app startup
            let child = start_python_backend(app.handle());
            
            // Store process in state
            if let Some(child) = child {
                let state = app.state::<AppState>();
                let mut process = state.python_process.lock().unwrap();
                *process = Some(child);
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            match event {
                tauri::RunEvent::ExitRequested { .. } => {
                     cleanup_python(app_handle);
                }
                tauri::RunEvent::Exit => {
                     cleanup_python(app_handle);
                }
                _ => {}
            }
        });
}
