import os
from flask import Flask, request, render_template_string, redirect, url_for, flash, send_file
from dotenv import load_dotenv
import uuid
import paramiko
import shutil
import time
import traceback

# Load configuration from config.env
load_dotenv('config.env')

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100 MB upload limit

# Set secret key for session management
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev_secret_key_change_me')

# Load private configuration variables
BIOREACTOR_IP = os.getenv('BIOREACTOR_IP')  # <-- Set this in config.env
SSH_KEY_PATH = os.getenv('SSH_KEY_PATH')    # <-- Set this in config.env
BIOREACTOR_USER = os.getenv('BIOREACTOR_USER')  # <-- Set this in config.env
BIOREACTOR_WORLD_DIR = os.getenv('BIOREACTOR_WORLD_DIR', '/world')

UPLOAD_FOLDER = 'uploads_tmp'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {'py'}

LOG_FILE = 'bioreactor_uploads.log'

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/', methods=['GET'])
def index():
    return render_template_string('''
        <h1>Bioreactor Website: Upload your Python file</h1>
        <form method="post" action="/upload" enctype="multipart/form-data">
            <input type="file" name="file" accept=".py" required>
            <input type="submit" value="Upload">
        </form>
        {% with messages = get_flashed_messages() %}
          {% if messages %}
            <ul>
            {% for message in messages %}
              <li>{{ message }}</li>
            {% endfor %}
            </ul>
          {% endif %}
        {% endwith %}
    ''')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(url_for('index'))
    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(url_for('index'))
    if file and allowed_file(file.filename):
        file_uuid = str(uuid.uuid4())
        save_dir = os.path.join(UPLOAD_FOLDER, file_uuid)
        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, file.filename)
        file.save(file_path)
        user_ip = request.remote_addr
        timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
        execution_result = None
        output_files = []
        error_msg = None
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(BIOREACTOR_IP, username=BIOREACTOR_USER, key_filename=SSH_KEY_PATH)
            sftp = ssh.open_sftp()
            remote_dir = f"{BIOREACTOR_WORLD_DIR}/{file_uuid}"
            remote_output_dir = f"{remote_dir}/output"
            # Create directories on remote
            ssh.exec_command(f"mkdir -p {remote_output_dir}")
            # Transfer file
            remote_file_path = f"{remote_dir}/{file.filename}"
            sftp.put(file_path, remote_file_path)
            # Execute the script with Docker
            stdout_file = f"{remote_output_dir}/stdout.txt"
            stderr_file = f"{remote_output_dir}/stderr.txt"
            exitcode_file = f"{remote_output_dir}/exitcode.txt"
            docker_image = "bioreactor-python-runner"
            docker_cmd = (
                f"cd {remote_dir} && "
                f"docker run --rm "
                f"-v {remote_dir}:/workspace "
                f"-w /workspace "
                f"--memory=1g --memory-swap=1g "
                f"--name run-{file_uuid} "
                f"{docker_image} "
                f"timeout 3600 python {file.filename} > output/stdout.txt 2> output/stderr.txt; "
                f"echo $? > output/exitcode.txt"
            )
            stdin, stdout, stderr = ssh.exec_command(docker_cmd)
            exit_status = stdout.channel.recv_exit_status()  # Wait for command to finish
            ssh_stdout = stdout.read().decode('utf-8')
            ssh_stderr = stderr.read().decode('utf-8')
            # List output files
            try:
                output_files = sftp.listdir(remote_output_dir)
            except Exception as e:
                output_files = []
            # If output_files is empty, try to debug
            debug_info = ""
            if not output_files:
                # Try to read stderr.txt and exitcode.txt
                try:
                    with sftp.open(stderr_file) as f:
                        stderr_content = f.read().decode('utf-8')
                except Exception:
                    stderr_content = '[stderr.txt not found]'
                try:
                    with sftp.open(exitcode_file) as f:
                        exitcode_content = f.read().decode('utf-8')
                except Exception:
                    exitcode_content = '[exitcode.txt not found]'
                # List parent directory
                try:
                    parent_files = sftp.listdir(remote_dir)
                except Exception:
                    parent_files = []
                debug_info = (
                    f"stderr.txt: {stderr_content}\n"
                    f"exitcode.txt: {exitcode_content}\n"
                    f"Parent dir files: {parent_files}\n"
                    f"SSH stdout: {ssh_stdout}\n"
                    f"SSH stderr: {ssh_stderr}\n"
                    f"SSH exit status: {exit_status}"
                )
                error_msg = f"No output files found. Debug info: {debug_info}"
            execution_result = 'Success' if output_files else 'Error'
            sftp.close()
            ssh.close()
        except Exception as e:
            error_msg = str(e)
            execution_result = 'Error'
        # Logging
        with open(LOG_FILE, 'a') as logf:
            logf.write(f"{timestamp}\t{user_ip}\t{file.filename}\t{file_uuid}\t{execution_result}\t{','.join(output_files)}\t{error_msg}\n")
        if execution_result == 'Success':
            flash(f'File executed on bioreactor! UUID: {file_uuid}. Output files: {output_files}')
            return redirect(url_for('output', uuid=file_uuid))
        else:
            flash(f'Error during execution: {error_msg}')
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Only .py files are allowed.')
        return redirect(url_for('index'))

@app.route('/output/<uuid>')
def output(uuid):
    try:
        print(f"[DEBUG] Attempting SSH connection to bioreactor.")
        print(f"[DEBUG] BIOREACTOR_IP: {BIOREACTOR_IP}")
        print(f"[DEBUG] BIOREACTOR_USER: {BIOREACTOR_USER}")
        print(f"[DEBUG] SSH_KEY_PATH: {SSH_KEY_PATH}")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        print(f"[DEBUG] Connecting via SSH...")
        ssh.connect(BIOREACTOR_IP, username=BIOREACTOR_USER, key_filename=SSH_KEY_PATH)
        print(f"[DEBUG] SSH connection established.")
        sftp = ssh.open_sftp()
        remote_output_dir = f"{BIOREACTOR_WORLD_DIR}/{uuid}/output"
        print(f"[DEBUG] Listing files in remote output dir: {remote_output_dir}")
        output_files = sftp.listdir(remote_output_dir)
        print(f"[DEBUG] Output files found: {output_files}")
        # Download all output files to a temp dir
        local_tmp = os.path.join(UPLOAD_FOLDER, uuid, 'output')
        os.makedirs(local_tmp, exist_ok=True)
        for fname in output_files:
            print(f"[DEBUG] Downloading {fname} from remote to local {local_tmp}")
            sftp.get(f"{remote_output_dir}/{fname}", os.path.join(local_tmp, fname))
        sftp.close()
        ssh.close()
        # Zip the output files
        zip_path = os.path.join(UPLOAD_FOLDER, uuid, 'output.zip')
        print(f"[DEBUG] Creating zip archive at {zip_path}")
        shutil.make_archive(zip_path[:-4], 'zip', local_tmp)
        # Show output file names and download link
        return render_template_string('''
            <h2>Execution Output (UUID: {{uuid}})</h2>
            <ul>
            {% for fname in output_files %}
                <li>{{ fname }}</li>
            {% endfor %}
            </ul>
            <a href="{{ url_for('download_output', uuid=uuid) }}">Download all output as zip</a>
            <br><a href="/">Back to upload</a>
        ''', uuid=uuid, output_files=output_files)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[ERROR] Exception in /output/{{uuid}}: {e}\n{tb}")
        flash(f'Error retrieving output: {e}')
        return redirect(url_for('index'))

@app.route('/download_output/<uuid>')
def download_output(uuid):
    zip_path = os.path.join(UPLOAD_FOLDER, uuid, 'output.zip')
    return send_file(zip_path, as_attachment=True)

# TODO: Add upload route and logic

if __name__ == '__main__':
    required_vars = {
        'BIOREACTOR_IP': BIOREACTOR_IP,
        'BIOREACTOR_USER': BIOREACTOR_USER,
        'SSH_KEY_PATH': SSH_KEY_PATH,
    }
    for var, value in required_vars.items():
        if not value:
            print(f"[ERROR] Required environment variable {var} is not set!")
    app.run(debug=True) 
