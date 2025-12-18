#!/usr/bin/env python3
"""
SQTPM Deployment Script

This script starts the SQTPM container and mounts assignment directories
and password files as volumes in the container's server root. Symbolic 
links are created in assignment directories pointing to their associated 
password files. A custom sqtpm.cfg file can be mounted to override the 
default configuration. Changes to mounted files are reflected immediately 
in the container.

The script supports incremental deployments - you can add new assignments 
and password files without removing existing ones. Each assignment can 
have its own set of password files.

Configuration can be provided via command line arguments or via a YAML 
configuration file (deploy.yml by default). If no command line arguments 
are provided, the script will look for deploy.yml.

Usage:
    python deploy.py                                          # Use deploy.yml
    python deploy.py assignment1:users.pass                  # Command line
    python deploy.py assignment1,assignment2:users.pass,admins.pass
    python deploy.py assignment1:users.pass assignment2:other.pass
    python deploy.py assignment1:users.pass assignment2 --config-file my-sqtpm.cfg
    python deploy.py --create-example-config                 # Create example deploy.yml

Assignment-Password Pair Format:
    assignment_dir:password_file.pass
    assignment1,assignment2:users.pass,admins.pass  (multiple assignments and passwords)
    assignment_dir                                  (assignment without password files)

YAML Configuration Format (deploy.yml):
    assignments:
      assignment1: ["users.pass"]
      assignment2: ["users.pass", "admins.pass"] 
      assignment3: []
    config_file: "custom-sqtpm.cfg"  # optional
    container: "my-sqtpm-web-1"      # optional
    build_only: true                 # optional - only build image, don't deploy
    no_rebuild: true                 # optional - start without rebuilding image
"""

import sys
import os
import subprocess
import time
import argparse
import yaml

def run_command(cmd, check=True, capture_output=False):
    """Run a shell command"""
    print(f"Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if isinstance(cmd, str):
        cmd = cmd.split()
    
    result = subprocess.run(
        cmd, 
        check=check, 
        capture_output=capture_output, 
        text=True
    )
    return result

def wait_for_container(container_name, max_wait=60):
    """Wait for container to be running and healthy"""
    print(f"Waiting for container {container_name} to be ready...")
    
    for i in range(max_wait):
        try:
            result = run_command(
                ["docker", "ps", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
                capture_output=True,
                check=False
            )
            
            if result.returncode == 0 and "Up" in result.stdout:
                print(f"Container {container_name} is running!")
                return True
                
        except Exception as e:
            print(f"Error checking container status: {e}")
        
        time.sleep(1)
    
    print(f"Container {container_name} did not start within {max_wait} seconds")
    return False

def update_docker_compose_override(assignments, config_file=None, pass_files=None):
    """Update docker-compose.override.yml with volume mappings for assignments, config file, and password files, preserving existing ones"""
    import yaml
    import os
    
    # Read existing override file if it exists
    existing_volumes = ['./data:/var/www/data']  # Keep existing data volume
    if os.path.exists("docker-compose.override.yml"):
        try:
            with open("docker-compose.override.yml", "r") as f:
                existing_config = yaml.safe_load(f)
                if existing_config and 'services' in existing_config and 'sqtpm-web' in existing_config['services'] and 'volumes' in existing_config['services']['sqtpm-web']:
                    existing_volumes = existing_config['services']['sqtpm-web']['volumes']
        except Exception as e:
            print(f"Warning: Could not read existing override file: {e}")
    
    # Get absolute paths for new assignments and use basename for container mapping
    new_assignment_volumes = []
    for assignment in assignments:
        if os.path.exists(assignment) and os.path.isdir(assignment):
            abs_path = os.path.abspath(assignment)
            # Strip trailing slash to ensure basename works correctly
            assignment_basename = os.path.basename(assignment.rstrip('/'))
            if not assignment_basename:  # Handle edge case
                assignment_basename = os.path.basename(abs_path)
            volume_mapping = f"{abs_path}:/var/www/html/{assignment_basename}"
            
            # Check if this assignment is already mounted
            already_exists = False
            for existing_volume in existing_volumes:
                if f":/var/www/html/{assignment_basename}" in existing_volume:
                    print(f"Assignment '{assignment_basename}' already mounted, skipping")
                    already_exists = True
                    break
            
            if not already_exists:
                new_assignment_volumes.append(volume_mapping)
    
    # Add password file mappings
    new_pass_file_volumes = []
    if pass_files:
        for pass_file in pass_files:
            if os.path.exists(pass_file) and os.path.isfile(pass_file):
                abs_pass_path = os.path.abspath(pass_file)
                pass_file_basename = os.path.basename(pass_file)
                pass_volume_mapping = f"{abs_pass_path}:/var/www/html/{pass_file_basename}"
                
                # Check if this password file is already mounted
                pass_already_exists = False
                for existing_volume in existing_volumes:
                    if f":/var/www/html/{pass_file_basename}" in existing_volume:
                        print(f"Password file '{pass_file_basename}' already mounted, skipping")
                        pass_already_exists = True
                        break
                
                if not pass_already_exists:
                    new_pass_file_volumes.append(pass_volume_mapping)
                    print(f"Adding password file mapping: {pass_file} -> {pass_file_basename}")
    
    # Add config file mapping if provided
    new_config_volumes = []
    if config_file and os.path.exists(config_file) and os.path.isfile(config_file):
        abs_config_path = os.path.abspath(config_file)
        config_volume_mapping = f"{abs_config_path}:/var/www/html/sqtpm.cfg"
        
        # Check if config file is already mounted
        config_already_exists = False
        for existing_volume in existing_volumes:
            if ":/var/www/html/sqtpm.cfg" in existing_volume:
                print(f"Config file already mounted, updating with: {config_file} -> sqtpm.cfg")
                # Replace existing config mapping
                existing_volumes = [v for v in existing_volumes if ":/var/www/html/sqtpm.cfg" not in v]
                config_already_exists = False  # Allow replacement
                break
        
        if not config_already_exists:
            new_config_volumes.append(config_volume_mapping)
            print(f"Adding config file mapping: {config_file} -> sqtpm.cfg")
    elif config_file:
        print(f"Warning: Config file '{config_file}' does not exist or is not a file")
    
    # Combine existing and new volumes
    all_volumes = existing_volumes + new_assignment_volumes + new_pass_file_volumes + new_config_volumes
    
    if len(all_volumes) <= 1:  # Only data volume
        # Remove override file if no volumes needed
        if os.path.exists("docker-compose.override.yml"):
            os.remove("docker-compose.override.yml")
            print("Removed docker-compose.override.yml (no additional volumes needed)")
        return True
    
    override_config = {
        'version': '3.8',
        'services': {
            'sqtpm-web': {
                'volumes': all_volumes
            }
        }
    }
    
    try:
        with open("docker-compose.override.yml", "w") as f:
            yaml.dump(override_config, f, default_flow_style=False)
        new_assignment_count = len(new_assignment_volumes)
        new_pass_count = len(new_pass_file_volumes)
        new_config_count = len(new_config_volumes)
        total_count = len(all_volumes) - 1  # Subtract data volume
        print(f"Updated docker-compose.override.yml: added {new_assignment_count} assignment(s), {new_pass_count} password file(s), {new_config_count} config mapping(s). Total: {total_count} volume(s)")
        return True
    except Exception as e:
        print(f"Error updating docker-compose.override.yml: {e}")
        return False

def get_assignment_basenames(assignments):
    """Get basenames of assignment directories for use in container paths"""
    basenames = []
    for assignment in assignments:
        basename = os.path.basename(assignment.rstrip('/'))  # Remove trailing slash if any
        if not basename:  # Handle edge case where assignment might be empty or just '/'
            basename = os.path.basename(os.path.abspath(assignment))
        basenames.append(basename)
    return basenames

def validate_assignments(assignments):
    """Validate that assignment directories exist"""
    valid_assignments = []
    for assignment in assignments:
        if not os.path.exists(assignment):
            print(f"Warning: Assignment directory '{assignment}' does not exist")
            continue
            
        if not os.path.isdir(assignment):
            print(f"Warning: '{assignment}' is not a directory")
            continue
        
        valid_assignments.append(assignment)
        print(f"Validated assignment directory: {assignment}")
    
    return valid_assignments

def create_pass_file_links(assignment_pass_pairs, container_name="sqtpm-sqtpm-web-1"):
    """Create symbolic links to password files in their associated assignment directories"""
    if not assignment_pass_pairs:
        print("No assignment-password pairs specified, skipping symbolic link creation")
        return True
    
    server_root = "/var/www/html"
    
    print(f"Creating symbolic links for assignment-password pairs...")
    
    for assignments, pass_files in assignment_pass_pairs:
        if not pass_files:
            print(f"No password files for assignments {assignments}, skipping")
            continue
            
        print(f"Processing assignments {assignments} with password files {pass_files}")
        
        # Get basenames of assignments for container paths
        assignment_basenames = get_assignment_basenames(assignments)
        
        for assignment, assignment_basename in zip(assignments, assignment_basenames):
            if not assignment_basename or assignment_basename in ['.', '..']:
                print(f"Warning: Invalid basename '{assignment_basename}' for assignment '{assignment}', skipping")
                continue
                
            assignment_path = f"{server_root}/{assignment_basename}"
            
            # Check if assignment directory exists in container (mounted as volume)
            try:
                result = run_command([
                    "docker", "exec", container_name,
                    "test", "-d", assignment_path
                ], check=False, capture_output=True)
                
                if result.returncode != 0:
                    print(f"Warning: Assignment directory {assignment_basename} not found in container")
                    continue
                    
            except subprocess.CalledProcessError:
                print(f"Warning: Could not check assignment directory {assignment_basename}")
                continue
            
            print(f"Creating password file links in {assignment_basename}...")
            
            for pass_file in pass_files:
                # Extract just the filename from the pass file path
                pass_file_basename = os.path.basename(pass_file)
                
                # Password file should be mounted directly in server root
                pass_file_path = f"{server_root}/{pass_file_basename}"
                
                try:
                    result = run_command([
                        "docker", "exec", container_name,
                        "test", "-f", pass_file_path
                    ], check=False, capture_output=True)
                    
                    if result.returncode != 0:
                        print(f"Warning: Password file {pass_file_basename} not found in server root (not mounted?)")
                        continue
                        
                except subprocess.CalledProcessError:
                    print(f"Warning: Could not check password file {pass_file_basename}")
                    continue
                
                # Create symbolic link using just the basename
                link_target = f"../{pass_file_basename}"
                link_path = f"{assignment_path}/{pass_file_basename}"
                
                try:
                    # Remove existing link/file if it exists
                    run_command([
                        "docker", "exec", container_name,
                        "rm", "-f", link_path
                    ], check=False)
                    
                    # Create the symbolic link
                    run_command([
                        "docker", "exec", container_name,
                        "ln", "-s", link_target, link_path
                    ])
                    
                    print(f"  Created link: {assignment_basename}/{pass_file_basename} -> {link_target}")
                    
                except subprocess.CalledProcessError as e:
                    print(f"  Error creating link for {pass_file_basename} in {assignment_basename}: {e}")
                    return False
    
    return True

def parse_assignment_pass_pairs(args_list):
    """Parse command line arguments to extract assignment-password file pairs
    
    Format: assignment1,assignment2:pass1.pass,pass2.pass assignment3:pass3.pass
    Returns: [(assignments_list, pass_files_list), ...]
    """
    pairs = []
    
    for arg in args_list:
        if ':' in arg:
            # Split by ':' to separate assignments from password files
            assignments_part, pass_files_part = arg.split(':', 1)
            
            # Split assignments by comma
            assignments = [a.strip() for a in assignments_part.split(',') if a.strip()]
            
            # Split password files by comma
            pass_files = [p.strip() for p in pass_files_part.split(',') if p.strip()]
            
            pairs.append((assignments, pass_files))
        else:
            # Assignment without password files
            assignments = [a.strip() for a in arg.split(',') if a.strip()]
            pairs.append((assignments, []))
    
    return pairs

def get_all_assignments_from_pairs(assignment_pass_pairs):
    """Extract all unique assignments from assignment-password pairs"""
    all_assignments = set()
    for assignments, _ in assignment_pass_pairs:
        all_assignments.update(assignments)
    return list(all_assignments)

def get_all_pass_files_from_pairs(assignment_pass_pairs):
    """Extract all unique password files from assignment-password pairs"""
    all_pass_files = set()
    for _, pass_files in assignment_pass_pairs:
        all_pass_files.update(pass_files)
    return list(all_pass_files)

def validate_pass_files(pass_files):
    """Validate that password files exist"""
    if not pass_files:
        return []
    
    valid_pass_files = []
    for pass_file in pass_files:
        if not os.path.exists(pass_file):
            print(f"Warning: Password file '{pass_file}' does not exist locally")
            continue
            
        if not os.path.isfile(pass_file):
            print(f"Warning: '{pass_file}' is not a file")
            continue
        
        valid_pass_files.append(pass_file)
        print(f"Validated password file: {pass_file}")
    
    return valid_pass_files

def validate_assignment_pass_pairs(assignment_pass_pairs):
    """Validate assignment-password pairs"""
    valid_pairs = []
    
    for assignments, pass_files in assignment_pass_pairs:
        # Validate assignments
        valid_assignments = validate_assignments(assignments)
        
        # Validate password files
        valid_pass_files = validate_pass_files(pass_files)
        
        if valid_assignments:  # Only add if at least one assignment is valid
            valid_pairs.append((valid_assignments, valid_pass_files))
        elif pass_files:  # Warn if password files but no valid assignments
            print(f"Warning: No valid assignments for password files {pass_files}")
    
    return valid_pairs

def list_pass_files_in_directory(directory="."):
    """List available .pass files in the specified directory"""
    pass_files = []
    try:
        for file in os.listdir(directory):
            if file.endswith('.pass') and os.path.isfile(os.path.join(directory, file)):
                pass_files.append(file)
    except OSError:
        pass
    return pass_files

def load_deploy_config(yaml_file="deploy.yml"):
    """Load deployment configuration from YAML file"""
    import yaml
    
    if not os.path.exists(yaml_file):
        return None
    
    try:
        with open(yaml_file, 'r') as f:
            config = yaml.safe_load(f)
            return config if config else None
    except Exception as e:
        print(f"Error reading YAML config file '{yaml_file}': {e}")
        return None

def parse_yaml_config(config):
    """Parse YAML configuration into assignment-password pairs"""
    assignment_pass_pairs = []
    
    if not config:
        return assignment_pass_pairs
    
    # Handle different YAML formats
    if 'deployments' in config:
        # Format: deployments: [{ assignments: [...], password_files: [...] }]
        deployments = config['deployments']
        if isinstance(deployments, list):
            for deployment in deployments:
                assignments = deployment.get('assignments', [])
                password_files = deployment.get('password_files', [])
                if assignments:
                    assignment_pass_pairs.append((assignments, password_files))
    
    elif 'assignments' in config:
        # Format: assignments: { assignment1: [pass1, pass2], assignment2: [] }
        assignments = config['assignments']
        if isinstance(assignments, dict):
            for assignment, pass_files in assignments.items():
                if isinstance(pass_files, str):
                    pass_files = [pass_files]  # Convert single string to list
                elif not isinstance(pass_files, list):
                    pass_files = []  # Default to empty list
                assignment_pass_pairs.append(([assignment], pass_files))
    
    elif isinstance(config, list):
        # Format: [{ assignment: "name", password_files: [...] }]
        for item in config:
            if isinstance(item, dict):
                assignment = item.get('assignment')
                password_files = item.get('password_files', [])
                if assignment:
                    if isinstance(password_files, str):
                        password_files = [password_files]
                    assignment_pass_pairs.append(([assignment], password_files))
    
    return assignment_pass_pairs

def create_example_deploy_yml():
    """Create an example deploy.yml file"""
    example_config = """# SQTPM Deployment Configuration
# This file defines assignment-password file pairs for deployment

# Option 1: Simple assignment -> password files mapping
assignments:
  test_assignment1: ["users1.pass"]
  test_assignment2: ["users2.pass", "admins.pass"]
  test_assignment3: []  # No password files

# Option 2: Deployment groups (alternative format)
# deployments:
#   - assignments: ["assignment1", "assignment2"]
#     password_files: ["users.pass", "admins.pass"]
#   - assignments: ["assignment3"]
#     password_files: ["special.pass"]

# Optional: Custom configuration file
# config_file: "custom-sqtpm.cfg"

# Optional: Container name override
# container: "my-sqtpm-web-1"

# Optional: Only build the docker image without deploying
# build_only: true

# Optional: Start container without rebuilding image  
# no_rebuild: true

# Optional: Stop and remove existing containers
# cleanup: true
"""
    
    with open("deploy.yml", "w") as f:
        f.write(example_config)
    print("Created example deploy.yml file")

def fix_permissions_in_container(container_name="sqtpm-sqtpm-web-1", host_user=None):
    """Run fix-perms.sh script inside the container and ensure proper ownership"""
    print("Fixing permissions and ownership in container...")
    
    # Get host user info if not provided
    if not host_user:
        import pwd
        user_info = pwd.getpwuid(os.getuid())
        host_user = user_info.pw_name
    
    try:
        # First ensure all files are owned by the host user
        run_command([
            "docker", "exec", container_name,
            "/bin/sh", "-c",
            f"chown -R {host_user}:www-data /var/www/html/"
        ])
        
        # Then run the fix-perms script as the host user
        run_command([
            "docker", "exec", container_name,
            "/bin/sh", "-c",
            f"su -s /bin/sh {host_user} -c 'cd /var/www/html && chmod +x Utils/fix-perms.sh && sh Utils/fix-perms.sh'"
        ])
        print("Permissions and ownership fixed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error fixing permissions: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Deploy SQTPM with assignment-password file pairs from command line or YAML config",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy.py                                   # Use deploy.yml if it exists
  python deploy.py assignment1:users.pass
  python deploy.py assignment1,assignment2:users.pass,admins.pass
  python deploy.py assignment1:users.pass assignment2:admins.pass
  python deploy.py assignment1:users.pass assignment2
  python deploy.py assignment1:users.pass --config-file custom-sqtpm.cfg
  python deploy.py --container my-sqtpm-web-1 assignment1:users.pass
  python deploy.py --list-pass-files
  python deploy.py --create-example-config
  python deploy.py --build-only                              # Only build image
  python deploy.py --no-rebuild assignment1:users.pass      # Start without rebuilding
  python deploy.py --cleanup                                 # Stop and remove containers

Assignment-Password Pair Format:
  assignment_dir:password_file.pass
  assignment1,assignment2:users.pass,admins.pass  (multiple assignments and passwords)
  assignment_dir                                  (assignment without password files)

YAML Configuration (deploy.yml):
  assignments:
    assignment1: ["users.pass"]
    assignment2: ["users.pass", "admins.pass"]
    assignment3: []
        """
    )
    
    parser.add_argument(
        'assignment_pairs',
        nargs='*',
        help='Assignment-password pairs in format "assignment:password.pass" or just "assignment". If not provided, will use deploy.yml'
    )
    
    parser.add_argument(
        '--config-file',
        help='Custom sqtpm.cfg file to mount/override in the server root'
    )
    
    parser.add_argument(
        '--yaml-file',
        default='deploy.yml',
        help='YAML configuration file to use (default: deploy.yml)'
    )
    
    parser.add_argument(
        '--container',
        default='sqtpm-sqtpm-web-1',
        help='Container name (default: sqtpm-sqtpm-web-1)'
    )
    
    parser.add_argument(
        '--build-only',
        action='store_true',
        help='Only build the docker image, do not start container or deploy'
    )
    
    parser.add_argument(
        '--no-rebuild',
        action='store_true',
        help='Start container without rebuilding image (assumes image already exists)'
    )
    
    parser.add_argument(
        '--cleanup',
        action='store_true',
        help='Stop and remove any existing containers from this deployment'
    )
    
    parser.add_argument(
        '--list-pass-files',
        action='store_true',
        help='List available .pass files in current directory'
    )
    
    parser.add_argument(
        '--create-example-config',
        action='store_true',
        help='Create an example deploy.yml configuration file'
    )
    
    args = parser.parse_args()
    
    # Create example config if requested
    if args.create_example_config:
        create_example_deploy_yml()
        return
    
    # List available pass files if requested
    if args.list_pass_files:
        available_pass_files = list_pass_files_in_directory()
        if available_pass_files:
            print("Available .pass files in current directory:")
            for pf in available_pass_files:
                print(f"  {pf}")
        else:
            print("No .pass files found in current directory")
        print()
        if not args.assignment_pairs:
            # Check if deploy.yml exists
            if not os.path.exists(args.yaml_file):
                return
    
    print("SQTPM Deployment Script")
    print("=" * 40)
    
    # Parse assignment-password pairs from command line or YAML
    assignment_pass_pairs = []
    config_file_override = args.config_file
    container_override = args.container
    build_only_override = args.build_only
    no_rebuild_override = args.no_rebuild
    cleanup_override = args.cleanup
    
    if args.assignment_pairs:
        # Use command line arguments
        print("Using command line arguments")
        assignment_pass_pairs = parse_assignment_pass_pairs(args.assignment_pairs)
    else:
        # Try to load from YAML file
        print(f"Loading configuration from {args.yaml_file}")
        yaml_config = load_deploy_config(args.yaml_file)
        
        if yaml_config is None:
            print(f"No configuration found. Either provide command line arguments or create {args.yaml_file}")
            print("Use --create-example-config to create an example configuration file")
            sys.exit(1)
        
        assignment_pass_pairs = parse_yaml_config(yaml_config)
        
        # Override with YAML config if not provided via command line
        if not config_file_override and 'config_file' in yaml_config:
            config_file_override = yaml_config['config_file']
        
        if container_override == 'sqtpm-sqtpm-web-1' and 'container' in yaml_config:
            container_override = yaml_config['container']
        
        if not build_only_override and yaml_config.get('build_only', False):
            build_only_override = True
            
        if not no_rebuild_override and yaml_config.get('no_rebuild', False):
            no_rebuild_override = True
            
        if not cleanup_override and yaml_config.get('cleanup', False):
            cleanup_override = True
    
    print("Parsed assignment-password pairs:")
    for assignments, pass_files in assignment_pass_pairs:
        if pass_files:
            print(f"  Assignments: {', '.join(assignments)} -> Password files: {', '.join(pass_files)}")
        else:
            print(f"  Assignments: {', '.join(assignments)} (no password files)")
    
    # Get host user information (needed for both building and fixing permissions)
    import pwd
    user_info = pwd.getpwuid(os.getuid())
    host_uid = user_info.pw_uid
    host_gid = user_info.pw_gid
    host_user = user_info.pw_name
    
    if config_file_override:
        print(f"Config file to mount: {config_file_override}")
    else:
        print("No custom config file specified")
    
    # Handle cleanup mode
    if cleanup_override:
        print("\nCleaning up existing containers...")
        try:
            # Stop and remove containers using docker-compose
            run_command(["docker-compose", "down", "-v"], check=False)
            print("Containers stopped and removed successfully")
            
            # Also remove any override file
            if os.path.exists("docker-compose.override.yml"):
                os.remove("docker-compose.override.yml")
                print("Removed docker-compose.override.yml")
            
            return
        except Exception as e:
            print(f"Error during cleanup: {e}")
            sys.exit(1)
    
    # Handle build-only mode
    if build_only_override:
        print("\nBuild-only mode: Building docker image...")
        print(f"Building with host user: {host_user} (UID:{host_uid}, GID:{host_gid})")
        
        # Set environment variables for docker-compose build
        env = os.environ.copy()
        env.update({
            'HOST_UID': str(host_uid),
            'HOST_GID': str(host_gid),
            'HOST_USER': host_user
        })
        
        try:
            result = subprocess.run(
                ["docker-compose", "build"],
                check=True,
                env=env
            )
            print("Docker image built successfully")
            print("Use --no-rebuild flag to start container without rebuilding")
            return
        except subprocess.CalledProcessError as e:
            print(f"Error building image: {e}")
            sys.exit(1)
    
    # Validate assignment-password pairs
    valid_assignment_pass_pairs = validate_assignment_pass_pairs(assignment_pass_pairs)
    
    if not valid_assignment_pass_pairs:
        print("No valid assignment-password pairs found!")
        sys.exit(1)
    
    # Get all assignments and password files for container operations
    all_assignments = get_all_assignments_from_pairs(valid_assignment_pass_pairs)
    all_pass_files = get_all_pass_files_from_pairs(valid_assignment_pass_pairs)
    
    # Step 1: Update docker-compose.override.yml with volume mappings for assignments, password files, and config
    print("\nStep 1: Updating volume mappings for assignments, password files, and config...")
    if not update_docker_compose_override(all_assignments, config_file_override, all_pass_files):
        print("Failed to update docker-compose override")
        sys.exit(1)
    
    # Step 2: Start the container
    print("\nStep 2: Starting SQTPM container with volume mappings...")
    
    print(f"Building with host user: {host_user} (UID:{host_uid}, GID:{host_gid})")
    
    # Set environment variables for docker-compose
    env = os.environ.copy()
    env.update({
        'HOST_UID': str(host_uid),
        'HOST_GID': str(host_gid),
        'HOST_USER': host_user
    })
    
    try:
        if no_rebuild_override:
            # Start without rebuilding (assumes image exists)
            result = subprocess.run(
                ["docker-compose", "up", "-d"],
                check=True,
                env=env
            )
            print("Container started successfully (without rebuilding)")
        else:
            # Build and start
            result = subprocess.run(
                ["docker-compose", "up", "-d", "--build"],
                check=True,
                env=env
            )
            print("Container built and started successfully")
    except subprocess.CalledProcessError as e:
        print(f"Error starting container: {e}")
        sys.exit(1)
    
    # Wait for container to be ready
    if not wait_for_container(container_override):
        print("Container failed to start properly")
        sys.exit(1)
    
    # Step 3: Create password file symbolic links based on assignment-password pairs
    if any(pass_files for _, pass_files in valid_assignment_pass_pairs):
        print(f"\nStep 3: Creating password file symbolic links...")
        if not create_pass_file_links(valid_assignment_pass_pairs, container_override):
            print("Failed to create password file links")
            sys.exit(1)
    else:
        print("\nStep 3: No password file links to create")
    
    # Step 4: Fix permissions and ownership
    print("\nStep 4: Fixing permissions and ownership...")
    if not fix_permissions_in_container(container_override, host_user):
        print("Failed to fix permissions")
        sys.exit(1)
    
    # Step 5: Restart Apache to ensure all changes are loaded
    print("\nStep 5: Restarting Apache server...")
    try:
        run_command([
            "docker", "exec", container_override,
            "/bin/sh", "-c",
            "apache2ctl graceful || true"
        ], check=False)
        print("Apache server reloaded successfully")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not reload Apache: {e}")
    
    print("\n" + "=" * 40)
    print("Deployment completed successfully!")
    print(f"SQTPM is available at: http://localhost:8080")
    
    # Show assignment mappings and their password files
    print(f"Assignments with their password files:")
    for assignments, pass_files in valid_assignment_pass_pairs:
        assignment_basenames = get_assignment_basenames(assignments)
        for assignment, basename in zip(assignments, assignment_basenames):
            if pass_files:
                print(f"  {assignment} -> {basename} (passwords: {', '.join(pass_files)})")
            else:
                print(f"  {assignment} -> {basename} (no passwords)")
    
    if config_file_override and os.path.exists(config_file_override):
        print(f"Config file mounted: {config_file_override} -> sqtpm.cfg")
    print("Assignment directories and password files are mounted as volumes - changes will reflect immediately!")
    
    # Show container status
    print(f"\nContainer status:")
    run_command(["docker", "ps", "--filter", f"name={container_override}"], check=False)

if __name__ == "__main__":
    main()
