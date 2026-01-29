import threading
import time

# Global dictionary to store tasks
# Since this is a local app, we can use a simple global dict.
# Structure: { task_id: { "type": str, "status": str, "message": str, "progress": float, "result": Any } }
TASKS = {}

def get_tasks():
    return TASKS

def start_indexing_task(kb_name, filenames, kb_manager_cls):
    """
    Start a background thread to index files.
    kb_manager_cls: The KBManager class (passed to avoid circular imports or re-instantiation issues)
    """
    task_id = f"indexing_{kb_name}_{int(time.time())}"
    
    TASKS[task_id] = {
        "type": "indexing",
        "status": "running",
        "message": "准备开始处理...",
        "progress": 0.0,
        "kb_name": kb_name
    }
    
    def worker():
        try:
            # Instantiate a new manager in this thread
            manager = kb_manager_cls()
            total = len(filenames)
            
            for i, filename in enumerate(filenames):
                TASKS[task_id]["message"] = f"正在处理: {filename}"
                TASKS[task_id]["progress"] = i / total
                
                # Perform the heavy lifting
                try:
                    manager.add_single_file_to_index(kb_name, filename)
                except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    # We continue despite errors
            
            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["message"] = "处理完成"
            TASKS[task_id]["progress"] = 1.0
            
            # Auto-clean completed tasks after 10 seconds (optional, but good for UI)
            # time.sleep(10)
            # if task_id in TASKS:
            #    del TASKS[task_id]
                
        except Exception as e:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["message"] = f"任务失败: {str(e)}"
            print(f"Task failed: {e}")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return task_id

def start_import_folder_task(kb_name, source_dir, kb_manager_cls):
    """
    Start a background thread to import a folder.
    """
    task_id = f"import_{kb_name}_{int(time.time())}"
    
    TASKS[task_id] = {
        "type": "importing",
        "status": "running",
        "message": "正在扫描文件夹...",
        "progress": 0.0,
        "kb_name": kb_name
    }
    
    def worker():
        try:
            manager = kb_manager_cls()
            # We need to modify import_from_directory to be granular or just run it blindly.
            # Standard import_from_directory does everything.
            # To get progress, we might need to duplicate logic or add a callback.
            # For now, let's just run it and show "processing".
            # Or better: We assume import_from_directory is "fast enough" per file but total time is long.
            # But import_from_directory includes the loop.
            
            # Let's delegate to the existing method, but we won't get granular progress 
            # unless we refactor import_from_directory to accept a progress callback.
            # For MVP, just run it.
            
            TASKS[task_id]["message"] = f"正在导入 {source_dir}..."
            count, errs = manager.import_from_directory(kb_name, source_dir)
            
            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["message"] = f"导入完成: 成功 {count}, 失败 {errs}"
            TASKS[task_id]["progress"] = 1.0
            
        except Exception as e:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["message"] = f"导入失败: {str(e)}"

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return task_id

def start_rebuild_task(kb_name, kb_manager_cls):
    """
    Start a background thread to rebuild the KB index.
    """
    task_id = f"rebuild_{kb_name}_{int(time.time())}"
    
    TASKS[task_id] = {
        "type": "rebuild",
        "status": "running",
        "message": "正在重建索引 (可能需要较长时间)...",
        "progress": 0.0,
        "kb_name": kb_name
    }
    
    def worker():
        try:
            manager = kb_manager_cls()
            # rebuild_kb_index operations
            manager.rebuild_kb_index(kb_name)
            
            TASKS[task_id]["status"] = "completed"
            TASKS[task_id]["message"] = "索引重建完成"
            TASKS[task_id]["progress"] = 1.0
        except Exception as e:
            TASKS[task_id]["status"] = "failed"
            TASKS[task_id]["message"] = f"重建失败: {str(e)}"
            print(f"Rebuild task failed: {e}")

    t = threading.Thread(target=worker, daemon=True)
    t.start()
    return task_id

def clear_completed_tasks():
    to_remove = [k for k, v in TASKS.items() if v["status"] in ["completed", "failed"]]
    for k in to_remove:
        del TASKS[k]
