import os
import asyncio
import subprocess
import psutil
from datetime import datetime
from dotenv import dotenv_values
from .database import update_project_execution_info, get_project_by_id

running_processes = {}


# -------------------------------
# INSTALL DEPENDENCIES
# -------------------------------

async def install_project_dependencies(project_id, project):
    project_path = project['path']
    venv_path = os.path.join(project_path, ".venv")
    requirements_path = os.path.join(project_path, "requirements.txt")

    # Create venv if not exists
    if not os.path.exists(venv_path):
        process = await asyncio.create_subprocess_exec(
            "python3", "-m", "venv", ".venv",
            cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, err = await process.communicate()
        if process.returncode != 0:
            return False, f"❌ Failed to create venv:\n{err.decode()}"

    # Upgrade pip
    process = await asyncio.create_subprocess_exec(
        ".venv/bin/python", "-m", "pip", "install", "--upgrade", "pip",
        cwd=project_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    await process.communicate()

    # Install requirements
    if os.path.exists(requirements_path):
        process = await asyncio.create_subprocess_exec(
            ".venv/bin/python", "-m", "pip", "install", "-r", "requirements.txt",
            cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        out, err = await process.communicate()
        if process.returncode != 0:
            return False, f"❌ Pip install failed:\n{err.decode()}"

    return True, "✅ Virtual environment ready and dependencies installed."


# -------------------------------
# START PROJECT
# -------------------------------

async def start_project(project_id: str, project: dict):
    if project_id in running_processes and running_processes[project_id].poll() is None:
        return False, "⚠️ Project is already running."

    try:
        project_path = project['path']
        venv_python = os.path.join(project_path, ".venv", "bin", "python")

        if not os.path.exists(venv_python):
            return False, "❌ Virtual environment not found. Please install dependencies first."

        run_command = project.get("run_command", "python main.py").split()
        run_cmd = [venv_python] + run_command[1:]

        # Open log file
        log_file = open(project['execution_info']['log_file'], 'w')

        # Load user .env
        user_env_path = os.path.join(project_path, '.env')
        user_env_vars = dotenv_values(user_env_path) if os.path.exists(user_env_path) else {}

        process_env = {
            **os.environ,
            **user_env_vars
        }

        process = subprocess.Popen(
            run_cmd,
            cwd=project_path,
            stdout=log_file,
            stderr=log_file,
            start_new_session=True,
            env=process_env
        )

        running_processes[project_id] = process

        update_data = {
            'is_running': True,
            'pid': process.pid,
            'last_run_time': datetime.utcnow(),
            'status': 'running'
        }
        await update_project_execution_info(project_id, update_data)

        return True, f"✅ Process started with PID: {process.pid}"

    except Exception as e:
        return False, f"❌ Execution failed: {e}"


# -------------------------------
# STOP PROJECT
# -------------------------------

async def stop_project(project_id):
    if project_id not in running_processes:
        return False, "⚠️ Project is not running."

    process = running_processes.pop(project_id)

    if process.poll() is not None:
        return False, "⚠️ Process already stopped."

    try:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

        await update_project_execution_info(project_id, {
            'is_running': False,
            'pid': None,
            'status': 'stopped'
        })

        return True, "✅ Process stopped successfully."

    except Exception as e:
        return False, f"❌ Failed to stop process: {e}"


# -------------------------------
# RESTART PROJECT
# -------------------------------

async def restart_project(project_id, project):
    await stop_project(project_id)
    await asyncio.sleep(1)
    return await start_project(project_id, project)


# -------------------------------
# PROJECT STATUS
# -------------------------------

async def get_project_status(project_id, project, detailed=False):
    exec_info = project['execution_info']

    is_running = False
    if project_id in running_processes and running_processes[project_id].poll() is None:
        is_running = True

    if is_running:
        status = "🟢 Running"
        pid = running_processes[project_id].pid
        try:
            p = psutil.Process(pid)
            uptime = datetime.now() - datetime.fromtimestamp(p.create_time())
            uptime_str = str(uptime).split('.')[0]
        except:
            uptime_str = "N/A"
    else:
        status = "🔴 Stopped"
        pid = "N/A"
        uptime_str = "N/A"

    if not detailed:
        return status

    last_run_str = "Never"
    if isinstance(exec_info.get('last_run_time'), datetime):
        last_run_str = exec_info['last_run_time'].strftime("%Y-%m-%d %H:%M:%S UTC")

    return (
        f"**Project Status: `{project['name']}`**\n\n"
        f"🔹 **Status:** {status}\n"
        f"🔹 **PID:** `{pid}`\n"
        f"🔹 **Uptime:** `{uptime_str}`\n"
        f"🔹 **Last Run:** `{last_run_str}`\n"
        f"🔹 **Run Command:** `{project.get('run_command')}`"
    )


# -------------------------------
# PROJECT LOGS
# -------------------------------

async def get_project_logs(project_id):
    project = await get_project_by_id(project_id)
    return project['execution_info']['log_file']


# -------------------------------
# PROJECT RESOURCE USAGE
# -------------------------------

async def get_project_usage(project_id):
    if project_id not in running_processes:
        return "⚠️ Project is not running."

    process = running_processes[project_id]
    if process.poll() is not None:
        return "⚠️ Project is stopped."

    try:
        p = psutil.Process(process.pid)
        cpu_usage = p.cpu_percent(interval=1)
        mem_info = p.memory_info()
        ram_usage = mem_info.rss / (1024 * 1024)

        return (
            f"**Resource Usage (PID `{p.pid}`)**\n\n"
            f"📊 **CPU:** {cpu_usage:.2f}%\n"
            f"🧠 **RAM:** {ram_usage:.2f} MB"
        )
    except Exception as e:
        return f"❌ Could not retrieve usage: {e}"
