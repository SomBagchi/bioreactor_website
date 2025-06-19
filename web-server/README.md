# Bioreactor Web Server

User interface for uploading scripts and managing bioreactor experiments.

## Purpose

The web-server component provides a user-friendly web interface for uploading Python scripts, monitoring experiments, and downloading results. It acts as the entry point for users to interact with the bioreactor system.

## Features

- **Script Upload**: Secure file upload for Python experiments
- **Experiment Monitoring**: Real-time status and progress tracking
- **Result Download**: Download experiment results as ZIP files
- **User Interface**: Clean, modern web interface
- **SSH Communication**: Secure communication with bioreactor-hub
- **Session Management**: User session handling (future)

## User Workflow

1. **Upload Script**: User uploads Python script through web interface
2. **Validation**: Server validates script format and content
3. **Submission**: Script sent to bioreactor-hub for execution
4. **Monitoring**: User can monitor experiment progress
5. **Completion**: User receives notification when experiment completes
6. **Download**: User downloads results as ZIP file

## API Endpoints

### File Management
- `POST /upload` - Upload Python script
- `GET /files` - List uploaded files
- `DELETE /files/{id}` - Delete uploaded file

### Experiment Management
- `POST /experiments/start` - Start new experiment
- `GET /experiments` - List user experiments
- `GET /experiments/{id}/status` - Get experiment status
- `POST /experiments/{id}/stop` - Stop experiment
- `GET /experiments/{id}/download` - Download experiment results

### System Status
- `GET /status` - System health status
- `GET /hardware/status` - Hardware status (via hub)

## Supported Script Features

### Allowed Imports
- `numpy` - Numerical computing
- `pandas` - Data manipulation
- `matplotlib` - Plotting and visualization
- `scikit-learn` - Machine learning
- `time` - Time utilities
- `logging` - Logging functionality

### Bioreactor Access
Users can access bioreactor hardware through:
- `Bioreactor` class from `bioreactor.py`
- Utility functions from `utils.py`
- **No direct access** to `config.py` or hardware

### Example Scripts
See `user_script.py` and `user_script_2.py` for examples of:
- Chemostat mode operation
- Temperature control with PID
- Real-time data collection and plotting
- Multi-threaded operations

## Deployment

### Prerequisites
- Python 3.9+
- SSH access to bioreactor-hub
- Web server (nginx, Apache) for production

### Local Development
```bash
# Clone the repository
git clone <your-repo-url>
cd bioreactor_website/web-server

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp config.env.example config.env
# Edit config.env with your settings

# Run development server
python app.py
```

### Production Deployment
```bash
# Using Docker
docker build -t bioreactor-web-server .
docker run -d --name web-server -p 5000:5000 bioreactor-web-server

# Using Gunicorn
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Configuration

### Environment Variables
- `BIOREACTOR_HUB_HOST`: Hostname of bioreactor-hub
- `BIOREACTOR_HUB_PORT`: SSH port for bioreactor-hub
- `SSH_KEY_PATH`: Path to SSH private key
- `UPLOAD_FOLDER`: Directory for temporary file uploads
- `MAX_CONTENT_LENGTH`: Maximum file upload size (bytes)
- `SECRET_KEY`: Flask secret key for sessions

### SSH Configuration
1. Generate SSH key pair for web-server → bioreactor-hub communication
2. Add public key to bioreactor-hub authorized_keys
3. Configure private key path in environment variables

## Security

### File Upload Security
- **File Type Validation**: Only Python files allowed
- **Content Validation**: Check for disallowed imports
- **Size Limits**: Configurable maximum file size
- **Virus Scanning**: Optional virus scanning (future)

### Network Security
- **SSH Communication**: Encrypted communication with hub
- **HTTPS**: Use HTTPS in production
- **Input Validation**: Validate all user inputs
- **Rate Limiting**: Prevent abuse (future)

## User Interface

### Features
- **Modern Design**: Clean, responsive interface
- **Real-time Updates**: Live experiment status updates
- **File Management**: Upload, view, and delete scripts
- **Experiment History**: View past experiments
- **Result Download**: Easy download of experiment results

### Technologies
- **Backend**: Flask/FastAPI
- **Frontend**: HTML, CSS, JavaScript
- **Real-time**: WebSocket or Server-Sent Events
- **File Handling**: Secure file upload/download

## Development

### Project Structure
```
web-server/
├── app.py                 # Main Flask application
├── bioreactor.py          # Bioreactor hardware interface
├── config.py              # Hardware configuration
├── utils.py               # Utility functions
├── requirements.txt       # Python dependencies
├── src/
│   ├── web/              # Web interface components
│   ├── ssh/              # SSH communication
│   └── utils/            # Utility functions
├── static/               # Static files (CSS, JS)
├── templates/            # HTML templates
└── uploads_tmp/          # Temporary upload directory
```

### Adding Features
1. **New API Endpoints**: Add to `app.py`
2. **UI Components**: Add to `templates/` and `static/`
3. **SSH Communication**: Extend `src/ssh/`
4. **File Handling**: Extend `src/utils/`

## Monitoring

### Health Checks
- `GET /health` - Application health status
- `GET /status` - System status including hub connectivity

### Logging
- Application logs: `/var/log/bioreactor-web/`
- Upload logs: `bioreactor_uploads.log`
- Error logs: Flask error handling

## Troubleshooting

1. **Upload fails**: Check file size limits and permissions
2. **SSH connection issues**: Verify SSH keys and network connectivity
3. **Experiment not starting**: Check bioreactor-hub status
4. **Download fails**: Verify file permissions and disk space 
