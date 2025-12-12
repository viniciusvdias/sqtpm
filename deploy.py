#!/usr/bin/env python3
"""
SQTPM Deployment Script

This script starts the SQTPM container and copies assignment directories
to the running container's server root. It also manages password file
symbolic links within assignment directories.

Usage:
    python deploy.py assignment1 assignment2 assignment3 ...
    python deploy.py arvore_geradora_minima --pass-files users.pass admins.pass
    python deploy.py assignment1 --pass-files users.pass
"""

import sys
import os
import subprocess
import time
import argparse

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

def copy_assignments_to_container(assignments, container_name="sqtpm-sqtpm-web-1"):
    """Copy assignment directories to the running container"""
    server_root = "/usr/local/apache2/htdocs"
    
    for assignment in assignments:
        if not os.path.exists(assignment):
            print(f"Warning: Assignment directory '{assignment}' does not exist")
            continue
            
        if not os.path.isdir(assignment):
            print(f"Warning: '{assignment}' is not a directory")
            continue
        
        print(f"Copying assignment '{assignment}' to container...")
        
        # Copy the directory to the container
        try:
            run_command([
                "docker", "cp", 
                f"{assignment}", 
                f"{container_name}:{server_root}/"
            ])
            print(f"Successfully copied {assignment}")
        except subprocess.CalledProcessError as e:
            print(f"Error copying {assignment}: {e}")
            return False
    
    return True

def copy_pass_files_to_container(pass_files, container_name="sqtpm-sqtpm-web-1"):
    """Copy password files to the container's server root"""
    if not pass_files:
        return True
    
    server_root = "/usr/local/apache2/htdocs"
    
    print(f"Copying password files to container...")
    
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

def create_pass_file_links(assignments, pass_files, container_name="sqtpm-sqtpm-web-1"):
    """Create symbolic links to password files in each assignment directory"""
    if not pass_files:
        print("No password files specified, skipping symbolic link creation")
        return True
    
    server_root = "/usr/local/apache2/htdocs"
    
    print(f"Creating symbolic links for password files: {', '.join(pass_files)}")
    
    for assignment in assignments:
        assignment_path = f"{server_root}/{assignment}"
        
        # Check if assignment directory exists in container
        try:
            result = run_command([
                "docker", "exec", container_name,
                "test", "-d", assignment_path
            ], check=False, capture_output=True)
            
            if result.returncode != 0:
                print(f"Warning: Assignment directory {assignment} not found in container")
                continue
                
        except subprocess.CalledProcessError:
            print(f"Warning: Could not check assignment directory {assignment}")
            continue
        
        print(f"Creating password file links in {assignment}...")
        
        for pass_file in pass_files:
            # Check if password file exists in server root
            pass_file_path = f"{server_root}/{pass_file}"
            
            try:
                result = run_command([
                    "docker", "exec", container_name,
                    "test", "-f", pass_file_path
                ], check=False, capture_output=True)
                
                if result.returncode != 0:
                    print(f"Warning: Password file {pass_file} not found in server root")
                    continue
                    
            except subprocess.CalledProcessError:
                print(f"Warning: Could not check password file {pass_file}")
                continue
            
            # Create symbolic link
            link_target = f"../{pass_file}"
            link_path = f"{assignment_path}/{pass_file}"
            
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
                
                print(f"  Created link: {assignment}/{pass_file} -> {link_target}")
                
            except subprocess.CalledProcessError as e:
                print(f"  Error creating link for {pass_file} in {assignment}: {e}")
                return False
    
    return True

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

def fix_permissions_in_container(container_name="sqtpm-sqtpm-web-1"):
    """Run fix-perms.sh script inside the container"""
    print("Fixing permissions in container...")
    
    try:
        run_command([
            "docker", "exec", container_name,
            "/bin/sh", "-c",
            "cd /usr/local/apache2/htdocs && chmod +x Utils/fix-perms.sh && sh Utils/fix-perms.sh"
        ])
        print("Permissions fixed successfully")
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
  python deploy.py --container my-sqtpm-web-1 assignment1 --pass-files users.pass
  python deploy.py assignment1 --list-pass-files
        """
    )
    
    parser.add_argument(
        'assignments',
        nargs='+',
        help='Assignment directories to copy to the container'
    )
    
    parser.add_argument(
        '--pass-files',
        nargs='*',
        help='Password files (.pass) to copy to server root and link in assignment directories'
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
    
    if args.pass_files:
        print(f"Password files to deploy: {', '.join(args.pass_files)}")
    else:
        print("No password files specified")
    
    # Step 1: Start the container (unless --no-build is specified)
    if not args.no_build:
        print("\nStep 1: Starting SQTPM container...")
        try:
            run_command(["docker-compose", "up", "-d", "--build"])
            print("Container started successfully")
        except subprocess.CalledProcessError as e:
            print(f"Error starting container: {e}")
            sys.exit(1)
        
        # Wait for container to be ready
        if not wait_for_container(args.container):
            print("Container failed to start properly")
            sys.exit(1)
    else:
        print("\nStep 1: Skipping container startup (--no-build specified)")
    
    # Step 2: Copy password files to container
    if args.pass_files:
        print(f"\nStep 2: Copying {len(args.pass_files)} password file(s) to container...")
        if not copy_pass_files_to_container(args.pass_files, args.container):
            print("Failed to copy password files")
            sys.exit(1)
    else:
        print("\nStep 2: No password files to copy")
    
    # Step 3: Copy assignments to container
    print(f"\nStep 3: Copying {len(args.assignments)} assignment(s) to container...")
    if not copy_assignments_to_container(args.assignments, args.container):
        print("Failed to copy assignments")
        sys.exit(1)
    
    # Step 4: Create password file symbolic links
    if args.pass_files:
        print(f"\nStep 4: Creating password file symbolic links...")
        if not create_pass_file_links(args.assignments, args.pass_files, args.container):
            print("Failed to create password file links")
            sys.exit(1)
    else:
        print("\nStep 4: No password file links to create")
    
    # Step 5: Fix permissions
    print("\nStep 5: Fixing permissions...")
    if not fix_permissions_in_container(args.container):
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
    print(f"Assignments deployed: {', '.join(args.assignments)}")
    if args.pass_files:
        print(f"Password files deployed: {', '.join(args.pass_files)}")
        print("Password file symbolic links created in assignment directories")
    
    # Show container status
    print(f"\nContainer status:")
    run_command(["docker", "ps", "--filter", f"name={args.container}"], check=False)

if __name__ == "__main__":
    main()
