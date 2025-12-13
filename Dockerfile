FROM httpd:2.4-alpine

# Create gpt user and add to existing www-data group
RUN adduser -S gpt -G www-data

# Install system dependencies for Perl modules
RUN apk add --no-cache \
    bash \
    perl \
    perl-cgi \
    perl-dev \
    perl-lwp-protocol-https \
    perl-digest-sha1 \
    build-base \
    curl \
    wget \
    gd-dev \
    libgd \
    libpng-dev \
    jpeg-dev \
    freetype-dev \
    zlib-dev \
    openssl-dev

# Install additional Alpine Perl packages that are available
RUN apk add --no-cache \
    perl-encode \
    perl-file-copy-recursive \
    perl-time-hires \
    perl-digest-md5 \
    perl-mime-base64 \
    perl-fcntl \
    perl-posix \
    perl-cwd \
    || true

# Configure CPAN for non-interactive installation
RUN echo "o conf build_requires_install_policy yes" | cpan
RUN echo "o conf commit" | cpan

# Install required CPAN modules
RUN cpan install \
    CGI::Session \
    CGI::Carp \
    LWP::Simple \
    LWP::UserAgent \
    MIME::Base64 \
    GD \
    Digest::SHA \
    Encode \
    File::Basename \
    File::Find \
    File::Copy \
    Time::Local

# Enable CGI module
RUN sed -i 's/#LoadModule cgid_module/LoadModule cgid_module/' /usr/local/apache2/conf/httpd.conf
RUN sed -i 's/#LoadModule rewrite_module/LoadModule rewrite_module/' /usr/local/apache2/conf/httpd.conf

# Configure document root to allow CGI execution
RUN echo "<Directory \"/usr/local/apache2/htdocs\">" >> /usr/local/apache2/conf/httpd.conf
RUN echo "    AllowOverride None" >> /usr/local/apache2/conf/httpd.conf
RUN echo "    Options +ExecCGI" >> /usr/local/apache2/conf/httpd.conf
RUN echo "    AddHandler cgi-script .cgi" >> /usr/local/apache2/conf/httpd.conf
RUN echo "    Require all granted" >> /usr/local/apache2/conf/httpd.conf
RUN echo "</Directory>" >> /usr/local/apache2/conf/httpd.conf

# Copy all content to document root
COPY moss-sqtpm /usr/local/apache2/htdocs/
COPY *.pass /usr/local/apache2/htdocs/
COPY *.html /usr/local/apache2/htdocs/
COPY *.css /usr/local/apache2/htdocs/
COPY *.js /usr/local/apache2/htdocs/
COPY *.png /usr/local/apache2/htdocs/
COPY *.webp /usr/local/apache2/htdocs/
COPY *.pdf /usr/local/apache2/htdocs/
COPY *.cgi /usr/local/apache2/htdocs/
COPY *.pm /usr/local/apache2/htdocs/
COPY sqtpm.cfg /usr/local/apache2/htdocs/
COPY google-code-prettify/ /usr/local/apache2/htdocs/google-code-prettify/

# Make CGI scripts executable and set ownership
RUN chmod +x /usr/local/apache2/htdocs/*.cgi
RUN chown -R gpt:www-data /usr/local/apache2/htdocs/

# Create necessary directories
RUN mkdir -p /usr/local/apache2/htdocs/Utils
COPY Utils/ /usr/local/apache2/htdocs/Utils/

# Copy sqtpm-etc-localhost.sh to server root and create symlink
RUN cp /usr/local/apache2/htdocs/Utils/sqtpm-etc-localhost.sh /usr/local/apache2/htdocs/ && \
    ln -s /usr/local/apache2/htdocs/sqtpm-etc-localhost.sh /usr/local/apache2/htdocs/sqtpm-etc.sh

# Fix file permissions using the provided script
RUN cd /usr/local/apache2/htdocs && chmod +x Utils/fix-perms.sh && sh Utils/fix-perms.sh

# Create startup script
RUN echo '#!/bin/sh' > /usr/local/bin/start-sqtpm.sh && \
    echo 'cd /usr/local/apache2/htdocs && chmod +x Utils/fix-perms.sh && sh Utils/fix-perms.sh' >> /usr/local/bin/start-sqtpm.sh && \
    echo 'exec httpd-foreground' >> /usr/local/bin/start-sqtpm.sh && \
    chmod +x /usr/local/bin/start-sqtpm.sh

# Configure Apache to run as gpt user
RUN echo "User gpt" >> /usr/local/apache2/conf/httpd.conf
RUN echo "Group www-data" >> /usr/local/apache2/conf/httpd.conf

EXPOSE 80

CMD ["/usr/local/bin/start-sqtpm.sh"]
