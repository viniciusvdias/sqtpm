#!/usr/bin/env python3
"""
SQTPM Deployment Script

This script starts the SQTPM container and mounts assignment directories
as volumes in the container's server root. Password files are copied to 
the container's server root and symbolic links are created in assignment 
directories. A custom sqtpm.cfg file can be mounted to override the default 
configuration. Changes to mounted files are reflected immediately in the container.

Usage:
    python deploy.py assignment1 assignment2 assignment3 ...
    python deploy.py arvore_geradora_minima --pass-files users.pass admins.pass
    python deploy.py assignment1 --pass-files users.pass --config-file my-sqtpm.cfg
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

def create_docker_compose_override(assignments, config_file=None):
    """Create docker-compose.yml with volume mappings for assignments and config file"""
    import yaml
    import os
    
    # Get absolute paths for assignments and use basename for container mapping
    assignment_volumes = []
    for assignment in assignments:
        if os.path.exists(assignment) and os.path.isdir(assignment):
            abs_path = os.path.abspath(assignment)
            # Strip trailing slash to ensure basename works correctly
            assignment_basename = os.path.basename(assignment.rstrip('/'))
            if not assignment_basename:  # Handle edge case
                assignment_basename = os.path.basename(abs_path)
            assignment_volumes.append(f"{abs_path}:/usr/local/apache2/htdocs/{assignment_basename}")
    
    # Add config file mapping if provided
    config_volumes = []
    if config_file and os.path.exists(config_file) and os.path.isfile(config_file):
        abs_config_path = os.path.abspath(config_file)
        config_volumes.append(f"{abs_config_path}:/usr/local/apache2/htdocs/sqtpm.cfg")
        print(f"Adding config file mapping: {config_file} -> sqtpm.cfg")
    elif config_file:
        print(f"Warning: Config file '{config_file}' does not exist or is not a file")
    
    all_volumes = assignment_volumes + config_volumes
    
    if not all_volumes:
        # Remove override file if no volumes needed
        if os.path.exists("docker-compose.yml"):
            os.remove("docker-compose.yml")
        return True
    
    override_config = {
        'version': '3.8',
        'services': {
            'sqtpm-web': {
                'volumes': [
                    './data:/var/www/data'  # Keep existing data volume
                ] + all_volumes
            }
        }
    }
    
    try:
        with open("docker-compose.yml", "w") as f:
            yaml.dump(override_config, f, default_flow_style=False)
        assignment_count = len(assignment_volumes)
        config_count = len(config_volumes)
        print(f"Created docker-compose.yml with {assignment_count} assignment volume(s) and {config_count} config file mapping(s)")
        return True
    except Exception as e:
        print(f"Error creating docker-compose.yml: {e}")
        return False

def copy_pass_files_to_container(pass_files, container_name="sqtpm-sqtpm-web-1"):
    """Copy password files to the container's server root"""
    if not pass_files:
        return True
    
    server_root = "/usr/local/apache2/htdocs"
    
    print(f"Copying {len(pass_files)} password file(s) to container...")
    
    for pass_file in pass_files:
        if not os.path.exists(pass_file):
            print(f"Warning: Password file '{pass_file}' does not exist locally")
            continue
            
        if not os.path.isfile(pass_file):
            print(f"Warning: '{pass_file}' is not a file")
            continue
        
        print(f"Copying password file '{pass_file}' to container...")
        
        try:
            run_command([
                "docker", "cp", 
                pass_file, 
                f"{container_name}:{server_root}/"
            ])
            print(f"Successfully copied {pass_file}")
        except subprocess.CalledProcessError as e:
            print(f"Error copying {pass_file}: {e}")
            return False
    
    return True

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

def create_pass_file_links(assignments, pass_files, container_name="sqtpm-sqtpm-web-1"):
    """Create symbolic links to password files in assignment directories"""
    if not pass_files:
        print("No password files specified, skipping symbolic link creation")
        return True
    
    server_root = "/usr/local/apache2/htdocs"
    
    print(f"Creating symbolic links for password files: {', '.join(pass_files)}")
    
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
            
            # Check if password file exists in server root (copied to container)
            pass_file_path = f"{server_root}/{pass_file_basename}"
            
            try:
                result = run_command([
                    "docker", "exec", container_name,
                    "test", "-f", pass_file_path
                ], check=False, capture_output=True)
                
                if result.returncode != 0:
                    print(f"Warning: Password file {pass_file_basename} not found in server root")
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
            f"chown -R {host_user}:www-data /usr/local/apache2/htdocs/"
        ])
        
        # Then run the fix-perms script as the host user
        run_command([
            "docker", "exec", container_name,
            "/bin/sh", "-c",
            f"su -s /bin/sh {host_user} -c 'cd /usr/local/apache2/htdocs && chmod +x Utils/fix-perms.sh && sh Utils/fix-perms.sh'"
        ])
        print("Permissions and ownership fixed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error fixing permissions: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Deploy SQTPM with assignments and password files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python deploy.py arvore_geradora_minima
  python deploy.py arvore_geradora_minima --pass-files users.pass
  python deploy.py assignment1 assignment2 --pass-files users.pass admins.pass
  python deploy.py assignment1 --config-file custom-sqtpm.cfg
  python deploy.py assignment1 --pass-files users.pass --config-file custom-sqtpm.cfg
  python deploy.py --container my-sqtpm-web-1 assignment1 --pass-files users.pass
  python deploy.py assignment1 --list-pass-files
        """
    )
    
    parser.add_argument(
        'assignments',
        nargs='+',
        help='Assignment directories to mount as volumes in the container'
    )
    
    parser.add_argument(
        '--pass-files',
        nargs='*',
        help='Password files (.pass) to copy to server root and link in assignment directories'
    )
    
    parser.add_argument(
        '--config-file',
        help='Custom sqtpm.cfg file to mount/override in the server root'
    )
    
    parser.add_argument(
        '--container',
        default='sqtpm-sqtpm-web-1',
        help='Container name (default: sqtpm-sqtpm-web-1)'
    )
    
    parser.add_argument(
        '--no-build',
        action='store_true',
        help='Skip docker-compose up (assume container is already running)'
    )
    
    parser.add_argument(
        '--list-pass-files',
        action='store_true',
        help='List available .pass files in current directory'
    )
    
    args = parser.parse_args()
    
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
    
    print("SQTPM Deployment Script")
    print("=" * 40)
    
    # Get host user information (needed for both building and fixing permissions)
    import pwd
    user_info = pwd.getpwuid(os.getuid())
    host_uid = user_info.pw_uid
    host_gid = user_info.pw_gid
    host_user = user_info.pw_name
    
    if args.pass_files:
        print(f"Password files to deploy: {', '.join(args.pass_files)}")
    else:
        print("No password files specified")
    
    if args.config_file:
        print(f"Config file to mount: {args.config_file}")
    else:
        print("No custom config file specified")
    
    # Validate assignments and pass files
    valid_assignments = validate_assignments(args.assignments)
    valid_pass_files = validate_pass_files(args.pass_files)
    
    if not valid_assignments:
        print("No valid assignment directories found!")
        sys.exit(1)
    
    # Step 1: Create docker-compose.override.yml with volume mappings for assignments
    print("\nStep 1: Creating volume mappings for assignments and config...")
    if not create_docker_compose_override(valid_assignments, args.config_file):
        print("Failed to create docker-compose override")
        sys.exit(1)
    
    # Step 2: Start the container (unless --no-build is specified)
    if not args.no_build:
        print("\nStep 2: Starting SQTPM container with volume mappings...")
        
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
                ["docker-compose", "up", "-d", "--build"],
                check=True,
                env=env
            )
            print("Container started successfully")
        except subprocess.CalledProcessError as e:
            print(f"Error starting container: {e}")
            sys.exit(1)
        
        # Wait for container to be ready
        if not wait_for_container(args.container):
            print("Container failed to start properly")
            sys.exit(1)
    else:
        print("\nStep 2: Skipping container startup (--no-build specified)")
        # Still need to restart container to pick up new volume mappings
        print("Restarting container to pick up new volume mappings...")
        try:
            run_command(["docker-compose", "restart"])
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not restart container: {e}")
    
    # Step 3: Copy password files to container
    if valid_pass_files:
        print(f"\nStep 3: Copying {len(valid_pass_files)} password file(s) to container...")
        if not copy_pass_files_to_container(valid_pass_files, args.container):
            print("Failed to copy password files")
            sys.exit(1)
    else:
        print("\nStep 3: No password files to copy")
    
    # Step 4: Create password file symbolic links
    if valid_pass_files:
        print(f"\nStep 4: Creating password file symbolic links...")
        if not create_pass_file_links(valid_assignments, valid_pass_files, args.container):
            print("Failed to create password file links")
            sys.exit(1)
    else:
        print("\nStep 4: No password file links to create")
    
    # Step 5: Fix permissions and ownership
    print("\nStep 5: Fixing permissions and ownership...")
    if not fix_permissions_in_container(args.container, host_user):
        print("Failed to fix permissions")
        sys.exit(1)
    
    # Step 6: Restart Apache to ensure all changes are loaded
    print("\nStep 6: Restarting Apache server...")
    try:
        run_command([
            "docker", "exec", args.container,
            "/bin/sh", "-c",
            "pkill -HUP httpd || true"
        ], check=False)
        print("Apache server reloaded successfully")
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not reload Apache: {e}")
    
    print("\n" + "=" * 40)
    print("Deployment completed successfully!")
    print(f"SQTPM is available at: http://localhost:8080")
    
    # Show assignment mapping (original path -> basename in container)
    assignment_basenames = get_assignment_basenames(valid_assignments)
    assignment_mappings = []
    for orig_path, basename in zip(valid_assignments, assignment_basenames):
        if orig_path != basename:
            assignment_mappings.append(f"{orig_path} -> {basename}")
        else:
            assignment_mappings.append(basename)
    
    print(f"Assignments mounted as volumes: {', '.join(assignment_mappings)}")
    if valid_pass_files:
        print(f"Password files copied to container: {', '.join(valid_pass_files)}")
        print("Password file symbolic links created in assignment directories")
    if args.config_file and os.path.exists(args.config_file):
        print(f"Config file mounted: {args.config_file} -> sqtpm.cfg")
    print("Assignment directories are mounted as volumes - changes will reflect immediately!")
    
    # Show container status
    print(f"\nContainer status:")
    run_command(["docker", "ps", "--filter", f"name={args.container}"], check=False)

if __name__ == "__main__":
    main()
