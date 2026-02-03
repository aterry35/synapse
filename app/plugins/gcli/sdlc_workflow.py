import time
import os
import json
import subprocess
import google.generativeai as genai
from app.core.config_manager import ConfigManager
import datetime

class SDLCManager:
    def __init__(self, config):
        self.config = config
        self.current_phase = "IDLE"
        self.last_msg = ""
        self.projects_root = os.path.join(ConfigManager.get_plugin_config("antigravity").get("project_root", "Projects"), "GCLI_Projects")
        
        # Ensure root exists
        if not os.path.exists(self.projects_root):
            os.makedirs(self.projects_root, exist_ok=True)
            
        # Configure Gemini
        api_key = ConfigManager.get_google_api_key()
        print(f"[DEBUG] SDLCManager Init. API Key present: {bool(api_key)}")
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-2.0-flash')
            print("[DEBUG] Gemini Configured Successfully.")
        else:
            self.model = None
            print("[DEBUG] ERROR: No Google API Key found.")

        self.pending_prompt = None
        self.context_secrets = {}

    def _get_active_project_path(self):
        # We need to track which project is 'active' for resume. 
        # Simple file-based tracker.
        tracker = os.path.join(self.projects_root, "active_session.json")
        if os.path.exists(tracker):
            with open(tracker, 'r') as f:
                return json.load(f).get("path")
        return None

    def _set_active_project(self, path):
        tracker = os.path.join(self.projects_root, "active_session.json")
        with open(tracker, 'w') as f:
            json.dump({"path": path, "updated": str(datetime.datetime.now())}, f)

    def _analyze_needs(self, prompt):
        """Asks Gemini if the project needs credentials."""
        try:
            q = f"Does the following request require external API keys, secrets, or database credentials? Request: '{prompt}'. Return ONLY a JSON list of the key names needed, e.g. ['OPENAI_API_KEY', 'DB_URL']. If none, return []."
            resp = self.model.generate_content(q)
            text = resp.text.strip().replace("```json", "").replace("```", "")
            return json.loads(text)
        except:
            return []

    def start_new_project(self, prompt, stop_callback):
        if not self.model:
            return "Error: GOOGLE_API_KEY missing."

        # 0. Analyze Needs
        stop_callback()
        self.last_msg = "Analyzing project requirements..."
        needs = self._analyze_needs(prompt)
        
        if needs:
            self.pending_prompt = prompt
            self.current_phase = "WAITING_FOR_CREDENTIALS"
            return json.dumps({
                "message": f"🧠 **Smart Interceptor**\nI noticed this project likely needs the following credentials:\n`{needs}`\n\nDo you want to provide them now?\n- Reply `/gcli use KEY=VAL,KEY2=VAL` to securely inject them.\n- Reply `/gcli skip` to use placeholders (e.g., .env.example)."
            })
            
        return self._continue_starting_project(prompt, {}, stop_callback)

    def inject_credentials(self, creds_str, stop_callback):
        if not self.pending_prompt:
             return "Error: No pending project found. Start one with /gcli create ..."
        
        secrets = {}
        try:
            # Parse "KEY=VAL, KEY2=VAL"
            parts = creds_str.split(',')
            for p in parts:
                if '=' in p:
                    k, v = p.split('=', 1)
                    secrets[k.strip()] = v.strip()
        except:
            return "Error parsing credentials. Use format: KEY=VALUE,KEY2=VALUE"
            
        return self._continue_starting_project(self.pending_prompt, secrets, stop_callback)

    def skip_credentials(self, stop_callback):
        if not self.pending_prompt:
             return "Error: No pending project to skip."
        return self._continue_starting_project(self.pending_prompt, {}, stop_callback)

    def _continue_starting_project(self, prompt, secrets, stop_callback):
        self.pending_prompt = None
        self.context_secrets = secrets
        
        # 1. Identity Project Name using Gemini
        try:
            name_resp = self.model.generate_content(f"Suggest a short, safe, filesystem-friendly folder name for: {prompt}. Return only the name.")
            project_name = name_resp.text.strip().replace(" ", "_")
        except:
            project_name = f"Project_{int(time.time())}"

        project_path = os.path.join(self.projects_root, project_name)
        os.makedirs(project_path, exist_ok=True)
        self._set_active_project(project_path)
        
        # 2. Generate Requirements
        stop_callback()
        self.current_phase = "PLANNING"
        self.last_msg = f"Generating requirements for {project_name}..."
        print(f"[DEBUG] Generating requirements for {project_name}")
        
        try:
            print("[DEBUG] Calling Gemini API...")
            
            secret_context = ""
            if secrets:
                secret_context = f"\n\nSECURITY CONTEXT: The user provided these secrets: {list(secrets.keys())}. Use them in the implementation. DO NOT LEAK VALUES IN MARKDOWN."
            else:
                secret_context = "\n\nSECURITY CONTEXT: The user did NOT provide secrets. You must generate a .env.example with placeholders."

            response = self.model.generate_content(f"Create a detailed REQUIREMENTS.md and Implementation Plan for: {prompt}. Focus on Python/Node/React as appropriate.{secret_context}")
            print(f"[DEBUG] Gemini Response received. Length: {len(response.text)}")
        except Exception as e:
            print(f"[DEBUG] Gemini API Error: {e}")
            return f"Error calling Gemini API: {e}"
        
        req_path = os.path.join(project_path, "REQUIREMENTS.md")
        with open(req_path, "w") as f:
            f.write(response.text)
            
        self.current_phase = "WAITING_APPROVAL"
        self.last_msg = f"Plan created at {req_path}. Waiting for approval."
        
        return json.dumps({
            "message": f"Project '{project_name}' initialized.\nRequirements:\n{response.text[:200]}...\n\nType '/gcli approve' to proceed or '/gcli refine <comments>'.",
            "files": [req_path]
        })

    def refine_requirements(self, feedback, stop_callback):
        project_path = self._get_active_project_path()
        if not project_path or not os.path.exists(project_path):
            return json.dumps({"message": "No active GCLI project found to refine."})
            
        self.current_phase = "PLANNING"
        self.last_msg = "Refining requirements..."
        stop_callback()
        
        req_path = os.path.join(project_path, "REQUIREMENTS.md")
        current_reqs = ""
        if os.path.exists(req_path):
            with open(req_path, 'r') as f:
                current_reqs = f.read()
                
        prompt = f"""
        Existing Requirements:
        {current_reqs}
        
        User Feedback:
        {feedback}
        
        Task: Update the REQUIREMENTS.md and Implementation Plan based on the feedback.
        Return the FULL updated markdown content.
        """
        
        try:
            response = self.model.generate_content(prompt)
            # Overwrite file
            with open(req_path, "w") as f:
                f.write(response.text)
                
            self.current_phase = "WAITING_APPROVAL"
            return json.dumps({
                "message": f"Requirements Updated.\nBased on: '{feedback}'\n\nType '/gcli approve' to build or '/gcli refine <comments>' again.",
                "files": [req_path]
            })
        except Exception as e:
            return json.dumps({"message": f"Refinement failed: {e}"})

    def resume_approval(self, stop_callback):
        project_path = self._get_active_project_path()
        if not project_path or not os.path.exists(project_path):
            return json.dumps({"message": "No active GCLI project found to approve."})

        req_path = os.path.join(project_path, "REQUIREMENTS.md")
        with open(req_path, 'r') as f:
            plan = f.read()

        # 3. Code Generation
        self.current_phase = "CODING"
        self.last_msg = "Generating code..."
        stop_callback()
        
        # Ask for JSON structure of files
        prompt = f"""
        Based on this plan, generate the actual code files.
        Return a JSON object where keys are filenames and values are file contents.
        Include all necessary config files (package.json, requirements.txt, etc).
        
        Plan:
        {plan}
        """
        # Note: Gemini JSON mode is unreliable without strict schema or via text parsing.
        # We'll stick to text parsing or expect markdown blocks. 
        # For robustness in v2.2, let's ask for a Python script that WRITES the files.
        
        code_prompt = f"""
        Write a Python script that, when run, creates the file structure and writes all necessary code files for this project.
        
        CRITICAL RULES:
        1. Define a helper function exactly like this:
           def create_file(filepath, content=""):
               directory = os.path.dirname(filepath)
               if directory:
                   os.makedirs(directory, exist_ok=True)
               with open(filepath, "w") as f:
                   f.write(content)
                  
        2. Use `create_file` for ALL file writing. Do not use `open` directly.
        3. Do not just make the root folder.
        
        MANDATORY FILES TO GENERATE:
        - A 'Dockerfile' for the application.
        - A 'README.md' with execution instructions.
        - 'requirements.txt' or 'package.json' as needed.
        
        SECRET INJECTION:
        - If the user provided secrets, create a '.env' file with the values.
        - If NOT, create '.env.example' with placeholders.
        - Secrets Provided: {self.context_secrets}
        
        Do not explain. Return only the python code block.
        
        Plan: {plan}
        """
        
        try:
            resp = self.model.generate_content(code_prompt)
            maker_script = resp.text.replace("```python", "").replace("```", "").strip()
            
            # Save maker script
            maker_path = os.path.join(project_path, "project_maker.py")
            with open(maker_path, "w") as f:
                f.write(maker_script)
                
            # Run maker script
            self.last_msg = "Writing files..."
            subprocess.run(["python3", "project_maker.py"], cwd=project_path, capture_output=True)
            
        except Exception as e:
            return json.dumps({"message": f"Coding failed: {e}"})

        # 4. Build & Fix Loop
        build_json = self._run_build_loop(project_path, stop_callback)
        build_res = json.loads(build_json)
        
        # 5. Docker Sandbox Loop
        docker_json = self._run_docker_loop(project_path, stop_callback)
        docker_res = json.loads(docker_json)
        
        final_msg = build_res["message"] + "\n\n" + docker_res["message"]
        
        self.current_phase = "DONE"
        return json.dumps({"message": final_msg})

    def _run_build_loop(self, project_path, stop_callback):
        self.current_phase = "BUILDING"
        
        # Detect System (Recursive find)
        build_targets = []
        
        # Check Root
        if os.path.exists(os.path.join(project_path, "package.json")):
            build_targets.append((project_path, ["npm", "install"]))
        if os.path.exists(os.path.join(project_path, "requirements.txt")):
            build_targets.append((project_path, ["pip3", "install", "-r", "requirements.txt"]))
            
        # Check Subdirectories (Depth 1)
        try:
            for item in os.listdir(project_path):
                subpath = os.path.join(project_path, item)
                if os.path.isdir(subpath):
                    if os.path.exists(os.path.join(subpath, "package.json")):
                        build_targets.append((subpath, ["npm", "install"]))
                    if os.path.exists(os.path.join(subpath, "requirements.txt")):
                        build_targets.append((subpath, ["pip3", "install", "-r", "requirements.txt"]))
        except:
            pass
            
        if not build_targets:
            return json.dumps({"message": f"Project created at {project_path}. No build system detected, skipping build."})

        results = []
        for target_path, build_cmd in build_targets:
            success = False
            for attempt in range(3):
                stop_callback()
                rel_path = os.path.relpath(target_path, project_path)
                self.last_msg = f"Building {rel_path} (Attempt {attempt+1})..."
                
                res = subprocess.run(build_cmd, cwd=target_path, capture_output=True, text=True)
                
                if res.returncode == 0:
                    results.append(f"SUCCESS: {rel_path}")
                    success = True
                    break
                
                # Failed - Auto Fix Logic (Simplified for now, we just retry)
                # In v2.2 we should call Gemini here.
                # error_log = res.stderr
                # ...
                
            if not success:
                results.append(f"FAILED: {rel_path}")

    def _ensure_docker_running(self):
        """Checks if Docker is running, tries to launch it if not (Mac specific)."""
        try:
            # Check info
            subprocess.run(["docker", "info"], check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            print("[DEBUG] Docker not running. Attempting launch...")
            # Mac specific open
            if os.path.exists("/Applications/Docker.app"):
                subprocess.run(["open", "-a", "Docker"])
                # Wait loop
                for i in range(30):
                    time.sleep(2)
                    try:
                        subprocess.run(["docker", "info"], check=True, capture_output=True)
                        print("[DEBUG] Docker started successfully.")
                        return True
                    except:
                        pass
            return False

    def _run_docker_loop(self, project_path, stop_callback):
        self.current_phase = "DOCKERIZING"
        self.last_msg = "Checking Docker Engine..."
        stop_callback()
        
        if not self._ensure_docker_running():
            return json.dumps({"message": "⚠️ Docker skipped: Not running or not installed."})

        # Check for Dockerfile
        if not os.path.exists(os.path.join(project_path, "Dockerfile")):
             return json.dumps({"message": "⚠️ Docker skipped: No Dockerfile generated."})
             
        project_name = os.path.basename(project_path).lower().replace("_", "")
        
        # 1. Build
        self.last_msg = f"Building Docker Image: {project_name}..."
        print(f"[DEBUG] Building image {project_name}")
        build_res = subprocess.run(["docker", "build", "-t", project_name, "."], cwd=project_path, capture_output=True, text=True)
        
        if build_res.returncode != 0:
            return json.dumps({"message": f"❌ Docker Build Failed:\n{build_res.stderr[:500]}"})
            
        # 2. Run (Cleanup old if exists)
        self.last_msg = "Starting Container..."
        subprocess.run(["docker", "rm", "-f", project_name], capture_output=True)
        
        # Run with random port mapping (-P)
        run_res = subprocess.run(["docker", "run", "-d", "--name", project_name, "-P", project_name], capture_output=True, text=True)
        
        if run_res.returncode != 0:
             return json.dumps({"message": f"❌ Docker Run Failed:\n{run_res.stderr[:500]}"})
             
        # 3. Get Port
        port_res = subprocess.run(["docker", "port", project_name], capture_output=True, text=True)
        ports = port_res.stdout.strip()
        
        return json.dumps({"message": f"✅ **Docker Sandbox Active** 🐳\nImage: `{project_name}`\nContainer: `{project_name}`\nPorts: `{ports}`\n\nTo view logs: `docker logs {project_name}`"})
