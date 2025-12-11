# SQTPM Docker Setup

This repository contains a Perl-based web system for receiving, compiling and verifying programming assignments via web interface.

## Quick Start

### Using Docker Compose (Recommended)

1. **Build and run the container:**
   ```bash
   docker-compose up -d
   ```

2. **Access the application:**
   - Open your browser and go to: http://localhost:8080
   - The main page will be available at: http://localhost:8080/home.html
   - CGI scripts are accessible at: http://localhost:8080/cgi-bin/sqtpm.cgi

3. **Stop the container:**
   ```bash
   docker-compose down
   ```

### Using Docker directly

1. **Build the image:**
   ```bash
   docker build -t sqtpm-web .
   ```

2. **Run the container:**
   ```bash
   docker run -d -p 8080:80 --name sqtpm-container sqtpm-web
   ```

3. **Access the application:**
   - Open your browser and go to: http://localhost:8080

4. **Stop and remove the container:**
   ```bash
   docker stop sqtpm-container
   docker rm sqtpm-container
   ```

## What's included

- Apache HTTP Server with CGI support
- Perl with required modules for the SQTPM system
- All web assets (HTML, CSS, JS, images)
- CGI scripts for handling submissions
- Configuration files

## Development

To make changes to the application:

1. Modify files in the repository
2. Rebuild the container: `docker-compose build`
3. Restart: `docker-compose up -d`

## System Requirements

- Docker
- Docker Compose (optional but recommended)

The system supports submissions in C, C++, Fortran, Pascal, Python3, Java, and PDF files.