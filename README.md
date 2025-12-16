# SQTPM Deployment Script

A powerful Python deployment script for SQTPM (Sistema de Recepção e Correção de Trabalhos de Programação) that automates container setup, assignment mounting, and password file management.

## Overview

The `deploy.py` script starts the SQTPM container and mounts assignment directories and password files as volumes in the container's server root. It creates symbolic links in assignment directories pointing to their associated password files, allowing for flexible and incremental deployments.

### Key Features

- **Incremental Deployments**: Add new assignments and password files without removing existing ones
- **Flexible Configuration**: Support for both command-line arguments and YAML configuration files
- **Volume Mounting**: Assignment directories and password files are mounted as volumes for real-time updates
- **Selective Password Management**: Each assignment can have its own set of password files
- **Container Management**: Automatic container startup, restart, and permission fixing

## Requirements

### System Dependencies

- Docker
- Docker Compose
- Python 3.6+

### Python Dependencies

Install the required Python packages:

```bash
pip install PyYAML
```

Or create a `requirements.txt` file:

```txt
PyYAML>=6.0
```

Then install with:

```bash
pip install -r requirements.txt
```

## Installation

1. Clone the repository or download the `deploy.py` script
2. Install Python dependencies (see above)
3. Ensure Docker and Docker Compose are installed and running
4. Make sure you have the necessary SQTPM Docker setup files (`docker-compose.yml`, `Dockerfile`, etc.)

## Usage

### Command Line Interface

#### Basic Usage

```bash
# Use YAML configuration (default)
python deploy.py

# Single assignment with password file
python deploy.py assignment1:users.pass

# Multiple assignments sharing password files
python deploy.py assignment1,assignment2:users.pass,admins.pass

# Multiple separate assignments with different password files
python deploy.py assignment1:users.pass assignment2:admins.pass

# Assignment without password files
python deploy.py assignment1

# Mixed assignment types
python deploy.py assignment1:users.pass assignment2 assignment3:other.pass
```

#### Advanced Options

```bash
# Use custom YAML configuration file
python deploy.py --yaml-file custom-deploy.yml

# Override container name
python deploy.py assignment1:users.pass --container my-sqtpm-web-1

# Skip container build/restart
python deploy.py assignment1:users.pass --no-build

# Mount custom configuration file
python deploy.py assignment1:users.pass --config-file custom-sqtpm.cfg

# List available password files
python deploy.py --list-pass-files

# Create example configuration file
python deploy.py --create-example-config
```

### YAML Configuration

The script supports YAML configuration files for easier management of complex deployments. If no command-line arguments are provided, it looks for `deploy.yml` by default.

#### Example Configuration

Create a `deploy.yml` file:

```yaml
# SQTPM Deployment Configuration
# Simple assignment -> password files mapping
assignments:
  assignment1: ["users.pass"]
  assignment2: ["users.pass", "admins.pass"]
  assignment3: []  # No password files
  data_structures: ["students.pass"]
  algorithms: ["advanced_users.pass", "tas.pass"]

# Optional: Custom configuration file
config_file: "custom-sqtpm.cfg"

# Optional: Container name override
container: "my-sqtpm-web-1"

# Optional: Skip container build/start
no_build: true
```

#### Alternative YAML Format (Deployment Groups)

```yaml
# Alternative format using deployment groups
deployments:
  - assignments: ["assignment1", "assignment2"]
    password_files: ["users.pass", "admins.pass"]
  - assignments: ["assignment3"]
    password_files: ["special.pass"]
  - assignments: ["final_project"]
    password_files: []
```

### Assignment-Password Pair Format

When using command-line arguments, use these formats:

- `assignment_dir:password_file.pass` - Single assignment with one password file
- `assignment1,assignment2:users.pass,admins.pass` - Multiple assignments sharing multiple password files
- `assignment_dir` - Assignment without password files
- Multiple pairs: `assignment1:users.pass assignment2:other.pass assignment3`

## How It Works

### Deployment Process

1. **Configuration Parsing**: Reads command-line arguments or YAML configuration
2. **Volume Mapping**: Updates `docker-compose.override.yml` with volume mappings for:
   - Assignment directories
   - Password files
   - Configuration files (optional)
3. **Container Management**: Starts or restarts the SQTPM container
4. **Symbolic Links**: Creates symbolic links in assignment directories pointing to their associated password files
5. **Permission Fixing**: Ensures proper file ownership and permissions
6. **Service Reload**: Reloads Apache server to apply changes

### File Structure

After deployment, the container structure looks like:

```
/usr/local/apache2/htdocs/
├── data/                           # Persistent data volume
├── assignment1/                    # Mounted assignment directory
│   ├── users.pass -> ../users.pass # Symbolic link to password file
│   └── ... (assignment files)
├── assignment2/                    # Another assignment
│   ├── users.pass -> ../users.pass
│   ├── admins.pass -> ../admins.pass
│   └── ... (assignment files)
├── users.pass                     # Mounted password file
├── admins.pass                     # Another mounted password file
├── sqtpm.cfg                      # Configuration file (optional)
└── ... (other SQTPM files)
```

## Examples

### Example 1: Simple Deployment

```bash
# Create assignment directory and password file
mkdir my_assignment
echo "student1:password123" > students.pass

# Deploy
python deploy.py my_assignment:students.pass
```

### Example 2: Complex Multi-Assignment Setup

```bash
# Deploy multiple assignments with different password files
python deploy.py \
  data_structures:students.pass \
  algorithms:students.pass,tas.pass \
  final_project:professors.pass
```

### Example 3: YAML-Based Deployment

Create `deploy.yml`:
```yaml
assignments:
  homework1: ["students.pass"]
  homework2: ["students.pass"]
  midterm: ["students.pass", "tas.pass"]
  final: ["professors.pass"]
config_file: "exam-sqtpm.cfg"
no_build: true
```

Then run:
```bash
python deploy.py
```

## Incremental Deployments

The script supports incremental deployments, meaning you can add new assignments and password files without affecting existing ones:

```bash
# Initial deployment
python deploy.py assignment1:users.pass

# Add another assignment (preserves assignment1)
python deploy.py assignment2:admins.pass

# Add more assignments via YAML
echo "assignments:
  assignment3: ['special.pass']" > new-deploy.yml
python deploy.py --yaml-file new-deploy.yml
```

## Troubleshooting

### Common Issues

1. **Container not found**: Ensure Docker is running and the container name is correct
2. **Permission errors**: The script automatically fixes permissions, but ensure the host user has proper Docker access
3. **Mount failures**: Check that assignment directories and password files exist and are accessible
4. **YAML parsing errors**: Validate your YAML syntax

### Debug Commands

```bash
# Check container status
docker ps

# Check mounted volumes
docker inspect sqtpm-sqtpm-web-1 | grep -A 20 "Mounts"

# Check logs
docker logs sqtpm-sqtpm-web-1

# List password files in current directory
python deploy.py --list-pass-files
```

## Command Reference

### Options

| Option | Description |
|--------|-------------|
| `assignment_pairs` | Assignment-password pairs in format "assignment:password.pass" |
| `--config-file FILE` | Custom sqtpm.cfg file to mount |
| `--yaml-file FILE` | YAML configuration file (default: deploy.yml) |
| `--container NAME` | Container name (default: sqtpm-sqtpm-web-1) |
| `--no-build` | Skip docker-compose up (assume container is running) |
| `--list-pass-files` | List available .pass files in current directory |
| `--create-example-config` | Create an example deploy.yml file |
| `--help` | Show help message |

### Exit Codes

- `0`: Success
- `1`: General error (invalid arguments, missing files, container issues)

## Advanced Usage

### Custom Container Names

```bash
# Use custom container name
python deploy.py assignment1:users.pass --container my-custom-sqtpm
```

### Integration with CI/CD

```bash
# In your CI/CD pipeline
python deploy.py --yaml-file production-deploy.yml --no-build
```

### Custom Configuration Files

```bash
# Mount custom SQTPM configuration
python deploy.py assignment1:users.pass --config-file production-sqtpm.cfg
```

## Contributing

When modifying the script:

1. Ensure backward compatibility
2. Update examples and documentation
3. Test both command-line and YAML configuration modes
4. Verify incremental deployment functionality

## License

This script is part of the SQTPM project. See the main project documentation for license information.