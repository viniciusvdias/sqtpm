FROM httpd:2.4-alpine

# Install system dependencies for Perl modules
RUN apk add --no-cache \
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

# Configure CGI directory
RUN echo "ScriptAlias /cgi-bin/ /usr/local/apache2/cgi-bin/" >> /usr/local/apache2/conf/httpd.conf
RUN echo "<Directory \"/usr/local/apache2/cgi-bin\">" >> /usr/local/apache2/conf/httpd.conf
RUN echo "    AllowOverride None" >> /usr/local/apache2/conf/httpd.conf
RUN echo "    Options +ExecCGI" >> /usr/local/apache2/conf/httpd.conf
RUN echo "    Require all granted" >> /usr/local/apache2/conf/httpd.conf
RUN echo "</Directory>" >> /usr/local/apache2/conf/httpd.conf

# Copy web content
COPY *.html /usr/local/apache2/htdocs/
COPY *.css /usr/local/apache2/htdocs/
COPY *.js /usr/local/apache2/htdocs/
COPY *.png /usr/local/apache2/htdocs/
COPY *.webp /usr/local/apache2/htdocs/
COPY *.pdf /usr/local/apache2/htdocs/
COPY google-code-prettify/ /usr/local/apache2/htdocs/google-code-prettify/

# Copy CGI scripts
COPY *.cgi /usr/local/apache2/cgi-bin/
COPY *.pm /usr/local/apache2/cgi-bin/
COPY sqtpm.cfg /usr/local/apache2/cgi-bin/

# Make CGI scripts executable
RUN chmod +x /usr/local/apache2/cgi-bin/*.cgi

# Create necessary directories
RUN mkdir -p /usr/local/apache2/htdocs/Utils
COPY Utils/ /usr/local/apache2/htdocs/Utils/

EXPOSE 80
