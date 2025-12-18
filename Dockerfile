FROM debian:bookworm-slim

# Accept host user information as build arguments
ARG HOST_UID=1000
ARG HOST_GID=1000
ARG HOST_USER=user

# Install Apache and system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    apache2 \
    apache2-utils \
    bash \
    perl \
    curl \
    wget \
    ca-certificates \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create host user and add to existing www-data group
RUN groupadd -g ${HOST_GID} ${HOST_USER} 2>/dev/null || true
RUN useradd -u ${HOST_UID} -g www-data -G ${HOST_USER} -s /bin/bash ${HOST_USER}

# Install Perl modules via apt
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcgi-pm-perl \
    libcgi-session-perl \
    liblwp-useragent-determined-perl \
    libwww-perl \
    libgd-perl \
    libdigest-sha-perl \
    libmime-base64-perl \
    libfile-copy-recursive-perl \
    libencode-perl \
    && rm -rf /var/lib/apt/lists/*

# Enable CGI module
RUN a2enmod cgi
RUN a2enmod rewrite

# Configure document root to allow CGI execution
RUN echo "<Directory \"/var/www/html\">" >> /etc/apache2/sites-available/000-default.conf
RUN echo "    AllowOverride None" >> /etc/apache2/sites-available/000-default.conf
RUN echo "    Options +ExecCGI" >> /etc/apache2/sites-available/000-default.conf
RUN echo "    AddHandler cgi-script .cgi" >> /etc/apache2/sites-available/000-default.conf
RUN echo "    Require all granted" >> /etc/apache2/sites-available/000-default.conf
RUN echo "</Directory>" >> /etc/apache2/sites-available/000-default.conf

# Copy all content to document root
COPY moss-sqtpm /var/www/html/
COPY *.pass /var/www/html/
COPY *.html /var/www/html/
COPY *.css /var/www/html/
COPY *.js /var/www/html/
COPY *.png /var/www/html/
COPY *.webp /var/www/html/
COPY *.pdf /var/www/html/
COPY *.cgi /var/www/html/
COPY *.pm /var/www/html/
COPY sqtpm.cfg /var/www/html/
COPY google-code-prettify/ /var/www/html/google-code-prettify/

# Create necessary directories and copy Utils first
RUN mkdir -p /var/www/html/Utils
COPY Utils/ /var/www/html/Utils/

# Copy sqtpm-etc-localhost.sh to server root and create symlink
RUN cp /var/www/html/Utils/sqtpm-etc-localhost.sh /var/www/html/ && \
    ln -s /var/www/html/sqtpm-etc-localhost.sh /var/www/html/sqtpm-etc.sh

# Set ownership of all files to host user after all copies are done
RUN chown -R ${HOST_USER}:www-data /var/www/html/

# Fix file permissions using the provided script
RUN cd /var/www/html && chmod +x Utils/fix-perms.sh && sh Utils/fix-perms.sh

# Create startup script that ensures proper ownership and runs as host user
RUN echo '#!/bin/bash' > /usr/local/bin/start-sqtpm.sh && \
    echo '# Ensure all files are owned by host user' >> /usr/local/bin/start-sqtpm.sh && \
    echo "chown -R ${HOST_USER}:www-data /var/www/html/" >> /usr/local/bin/start-sqtpm.sh && \
    echo '# Fix permissions as host user' >> /usr/local/bin/start-sqtpm.sh && \
    echo "su -s /bin/bash ${HOST_USER} -c 'cd /var/www/html && chmod +x Utils/fix-perms.sh && sh Utils/fix-perms.sh'" >> /usr/local/bin/start-sqtpm.sh && \
    echo '# Start Apache in foreground' >> /usr/local/bin/start-sqtpm.sh && \
    echo "exec apache2ctl -D FOREGROUND" >> /usr/local/bin/start-sqtpm.sh && \
    chmod +x /usr/local/bin/start-sqtpm.sh

# Configure Apache to run as host user
RUN sed -i "s/export APACHE_RUN_USER=www-data/export APACHE_RUN_USER=${HOST_USER}/" /etc/apache2/envvars
RUN sed -i "s/export APACHE_RUN_GROUP=www-data/export APACHE_RUN_GROUP=www-data/" /etc/apache2/envvars

EXPOSE 80

CMD ["/usr/local/bin/start-sqtpm.sh"]
