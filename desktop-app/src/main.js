// Main JavaScript for Tauri app
// This script handles communication with the Rust backend and manages the Streamlit iframe

const { invoke } = window.__TAURI__ ? window.__TAURI__.core : { invoke: null };

let apiPort = 8501; // Default fall back
let portFound = false;
const MAX_RETRIES = 60; // 60 seconds max wait time
const RETRY_INTERVAL = 1000; // 1 second

let retryCount = 0;

function updateStatus(message) {
  const statusText = document.getElementById('status-text');
  if (statusText) {
    statusText.textContent = message;
  }
}

function showError(message) {
  const errorMsg = document.getElementById('error-msg');
  if (errorMsg) {
    errorMsg.textContent = message;
    errorMsg.style.display = 'block';
  }
}

async function checkStreamlitReady() {
  try {
    const response = await fetch(`http://127.0.0.1:${apiPort}/_stcore/health`);
    return response.ok;
  } catch (e) {
    console.warn("Health check failed:", e);
    return e.message; // Return error message instead of false
  }
}

async function waitForStreamlit() {
  updateStatus('正在启动 Python 服务...');
  
  while (retryCount < MAX_RETRIES) {
    retryCount++;
    
    // If we haven't found the port yet
    if (!portFound) {
         updateStatus(`正在等待服务端口分配... (${retryCount}/${MAX_RETRIES})`);
    } else {
         updateStatus(`正在连接服务 (端口 ${apiPort})... (${retryCount}/${MAX_RETRIES})`);
    }
    
    // Try to connect
    const result = await checkStreamlitReady();
    if (result === true) {
      showStreamlit();
      return;
    }
    
    // If result is string, it's an error message
    if (typeof result === 'string' && portFound) {
        console.log(`Connection attempt failed: ${result}`);
        
        // Don't scare user immediately, server takes time to bind socket even after printing log
        if (retryCount < 5) {
             updateStatus(`服务正在初始化... (${retryCount}/${MAX_RETRIES})`);
        } else {
             updateStatus(`连接尝试中... (${retryCount}/${MAX_RETRIES})`);
        }
    }
    
    await new Promise(resolve => setTimeout(resolve, RETRY_INTERVAL));
  }
  
  showError(`无法连接到服务 (端口 ${apiPort})，请重启应用或检查日志。`);
}

function showStreamlit() {
  const loading = document.getElementById('loading');
  const iframe = document.getElementById('streamlit-frame');
  
  if (loading && iframe) {
    loading.style.display = 'none';
    iframe.style.display = 'block';
    iframe.src = `http://127.0.0.1:${apiPort}`;
  }
}

// Listen for Tauri events
const { listen } = window.__TAURI__.event;
const logsEl = document.getElementById('logs');
const logContainer = document.getElementById('log-container');
const toggleBtn = document.getElementById('toggle-logs');

if (toggleBtn && logContainer) {
  toggleBtn.addEventListener('click', () => {
    if (logContainer.style.height === '40px') {
      logContainer.style.height = 'auto';
      toggleBtn.textContent = '收起';
      document.getElementById('logs').style.display = 'block';
    } else {
      document.getElementById('logs').style.display = 'none';
      toggleBtn.textContent = '展开';
    }
  });
}

function appendLog(message, isError = false) {
  if (!logsEl) return;
  
  const span = document.createElement('div');
  span.textContent = message;
  if (isError) span.className = 'log-error';
  
  logsEl.appendChild(span);
  logsEl.scrollTop = logsEl.scrollHeight;
  
  // Show logs on first error or if container is not visible during long wait
  if (isError && logContainer.style.display === 'none') {
    logContainer.style.display = 'block';
  }
}

if (listen) {
  console.log('Tauri API available');
  listen('python-log', (event) => {
    console.log('Python:', event.payload);
    appendLog(event.payload);
    
    // Check for port info
    if (event.payload.includes('PYTHON_BACKEND_PORT=')) {
        const match = event.payload.match(/PYTHON_BACKEND_PORT=(\d+)/);
        if (match && match[1]) {
            apiPort = parseInt(match[1]);
            portFound = true;
            console.log(`Discovered Streamlit port: ${apiPort}`);
        }
    }
  });
  
  listen('python-error', (event) => {
    console.error('Python Error:', event.payload);
    appendLog(event.payload, true);
    // If we see "Port 8501 is already in use", show friendly error
    if (event.payload.includes("Port") && event.payload.includes("already in use")) {
        showError("端口 8501 被占用，请关闭冲突的程序后重启。");
    }
  });
} else {
    // For browser testing
    appendLog("Tauri Event API not available (Browser Mode)");
}

// Start checking when page loads
document.addEventListener('DOMContentLoaded', () => {
    // Show logs container after 5 seconds if not connected yet
    setTimeout(() => {
        if (logContainer && document.getElementById('loading').style.display !== 'none') {
            logContainer.style.display = 'block';
        }
    }, 5000);

    // Fetch historical logs from Rust backend
    if (invoke) {
        invoke('get_logs').then(logs => {
            logs.forEach(([msg, isError]) => {
                appendLog(msg, isError);
                
                // Check if we missed the port announcement
                if (!isError && msg.includes('PYTHON_BACKEND_PORT=')) {
                    const match = msg.match(/PYTHON_BACKEND_PORT=(\d+)/);
                    if (match && match[1]) {
                        apiPort = parseInt(match[1]);
                        portFound = true;
                        console.log(`Discovered Streamlit port from history: ${apiPort}`);
                    }
                }

                if (isError && msg.includes("Port") && msg.includes("already in use")) {
                    showError("端口 8501 被占用，请关闭冲突的程序后重启。");
                }
            });
        }).catch(err => console.error("Failed to get logs:", err));
    }
    
  waitForStreamlit();

  // Settings Modal Logic
  const modal = document.getElementById("settings-modal");
  
  // Define openSettings function at module level so it can be called from anywhere
  function openSettings() {
      const settingsModal = document.getElementById("settings-modal");
      if (settingsModal) {
          settingsModal.style.display = "block";
          // Load current settings
          if (invoke) {
              invoke('get_settings').then(settings => {
                  const settingsForm = document.getElementById("settings-form");
                  for (const [key, value] of Object.entries(settings)) {
                      if (settingsForm && settingsForm.elements[key]) {
                          settingsForm.elements[key].value = value;
                      }
                  }
              });
          }
      }
  }
  
  function closeSettings() {
      const settingsModal = document.getElementById("settings-modal");
      if (settingsModal) {
          settingsModal.style.display = "none";
      }
  }
  
  // Check if elements exist to prevent errors if loading fails
  if (modal) {
      const closeBtn = modal.querySelector(".close-button");
      const cancelBtn = document.getElementById("cancel-settings");
      const saveBtn = document.getElementById("save-settings");
      const form = document.getElementById("settings-form");
      
      // Listen for open-settings event from Rust menu
      listen('open-settings', () => {
          openSettings();
      });
      
      if (closeBtn) closeBtn.onclick = closeSettings;
      if (cancelBtn) cancelBtn.onclick = closeSettings;
      
      if (saveBtn) {
          saveBtn.onclick = (e) => {
              e.preventDefault();
              if (!form) return;
              
              const formData = new FormData(form);
              const settings = {};
              formData.forEach((value, key) => {
                  settings[key] = value;
              });
              
              invoke('save_settings', { settings }).then(() => {
                  alert("Settings saved! Some changes may require restarting the app.");
                  closeSettings();
              }).catch(err => {
                  alert("Failed to save settings: " + err);
              });
          };
      }
      
      window.onclick = (event) => {
          if (event.target == modal) {
              closeSettings();
          }
      };
  }

  // Keyboard shortcut listener - ALWAYS register this, outside the modal check
  window.addEventListener('keydown', (e) => {
      // Check for Cmd+, or Ctrl+, (keyCode 188 is comma)
      if ((e.metaKey || e.ctrlKey) && (e.key === ',' || e.keyCode === 188)) {
          e.preventDefault();
          console.log('Keyboard shortcut detected: Cmd/Ctrl + ,');
          openSettings();
      }
  }, true); // Use capture phase
  
  // Listen for messages from iframe (for shortcut) - ALWAYS register this
  window.addEventListener('message', (event) => {
      if (event.data && event.data.type === 'open-settings') {
          console.log('Received open-settings message from iframe');
          openSettings();
      }
  });
});
