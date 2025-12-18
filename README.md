# SQTPM Deployment Script

Simple Python script for deploying SQTPM containers with assignment directories and password files.

## Quick Start

```bash
# Build and deploy
python deploy.py assignment1:users.pass

# Or use YAML config
python deploy.py --create-example-config
python deploy.py
```

## Requirements

- Docker & Docker Compose
- Python 3.6+ with PyYAML (`pip install PyYAML`)

## Usage

### Basic Commands

```bash
# Deploy assignment with password file
python deploy.py assignment1:users.pass

# Multiple assignments
python deploy.py assignment1:users.pass assignment2:admins.pass

# Assignment without passwords
python deploy.py assignment1

# Use YAML configuration
python deploy.py
```

### Build Management

```bash
# Build image only (no deployment)
python deploy.py --build-only

# Deploy without rebuilding (assumes image exists)
python deploy.py --no-rebuild assignment1:users.pass

# Clean up containers
python deploy.py --cleanup
```

### YAML Configuration

Create `deploy.yml`:

```yaml
assignments:
  assignment1: ["users.pass"]
  assignment2: ["users.pass", "admins.pass"] 
  assignment3: []  # No password files

# Optional settings
config_file: "custom-sqtpm.cfg"
container: "my-sqtpm-web-1"
build_only: true     # Only build image
no_rebuild: true     # Start without rebuilding
cleanup: true        # Stop and remove containers
```

## Typical Workflow

```bash
# 1. Build image once
python deploy.py --build-only

# 2. Deploy quickly (no rebuild)
python deploy.py --no-rebuild assignment1:users.pass

# 3. Add more assignments (incremental)
python deploy.py --no-rebuild assignment2:other.pass

# 4. Clean up when done
python deploy.py --cleanup
```

## How It Works

1. Mounts assignment directories and password files as Docker volumes
2. Creates symbolic links from assignments to their password files
3. Fixes permissions and restarts Apache
4. Changes are reflected immediately (no rebuild needed)

## Options

| Option | Description |
|--------|-------------|
| `--build-only` | Only build Docker image |
| `--no-rebuild` | Start without rebuilding image |
| `--cleanup` | Stop and remove containers |
| `--config-file FILE` | Mount custom sqtpm.cfg |
| `--container NAME` | Custom container name |
| `--list-pass-files` | List available .pass files |
| `--create-example-config` | Create example deploy.yml |

## Examples

```bash
# Simple deployment
python deploy.py homework1:students.pass

# Multiple assignments sharing passwords
python deploy.py hw1,hw2:students.pass,tas.pass

# Mixed deployment
python deploy.py hw1:students.pass hw2 final:profs.pass

# Custom config
python deploy.py hw1:students.pass --config-file exam.cfg
```

SQTPM will be available at <http://localhost:8080/sqtpm.cgi> after deployment.

