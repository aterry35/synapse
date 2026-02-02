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

    def start_new_project(self, prompt, stop_callback):
        if not self.model:
            return "Error: GOOGLE_API_KEY missing."

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
            response = self.model.generate_content(f"Create a detailed REQUIREMENTS.md and Implementation Plan for: {prompt}. Focus on Python/Node/React as appropriate.")
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
        return self._run_build_loop(project_path, stop_callback)

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

        self.current_phase = "DONE"
        return json.dumps({"message": f"Build Process Complete.\nResults:\n" + "\n".join(results)})
