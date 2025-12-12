#!/usr/bin/perl -w
# Script to create/manage users for sqtpm
# Copyright 2024 - Part of sqtpm project

use strict;
use Digest::SHA qw(sha512_base64);
use Fcntl ':flock';

my $usage = <<EOF;
Usage: $0 [options] username [password]

Options:
  -t, --type TYPE     User type: aluno (default), prof, monitor
  -f, --file FILE     Password file (default: users.pass)
  -h, --help          Show this help

Examples:
  $0 john123                          # Create student with empty password
  $0 -t prof teacher1 mypassword      # Create professor with password
  $0 -t monitor assistant1            # Create monitor with empty password
  $0 --file admins.pass admin1 secret # Create in specific file

User types:
  aluno   - Student (no prefix)
  prof    - Professor (* prefix)
  monitor - Monitor (@ prefix)
EOF

# Parse command line arguments
my $type = 'aluno';
my $file = 'users.pass';
my $username = '';
my $password = '';

while (@ARGV) {
    my $arg = shift @ARGV;
    
    if ($arg eq '-h' || $arg eq '--help') {
        print $usage;
        exit 0;
    }
    elsif ($arg eq '-t' || $arg eq '--type') {
        $type = shift @ARGV or die "Error: --type requires an argument\n";
        unless ($type eq 'aluno' || $type eq 'prof' || $type eq 'monitor') {
            die "Error: Invalid type '$type'. Must be: aluno, prof, or monitor\n";
        }
    }
    elsif ($arg eq '-f' || $arg eq '--file') {
        $file = shift @ARGV or die "Error: --file requires an argument\n";
    }
    elsif (!$username) {
        $username = $arg;
    }
    elsif (!$password) {
        $password = $arg;
    }
    else {
        die "Error: Too many arguments\n$usage";
    }
}

# Validate username
die "Error: Username is required\n$usage" unless $username;
$username =~ s/\s//g;  # Remove whitespace
die "Error: Username cannot be empty\n" unless $username;

# Set prefix based on type
my $prefix = '';
if ($type eq 'prof') {
    $prefix = '*';
}
elsif ($type eq 'monitor') {
    $prefix = '@';
}

# Remove prefix from username if user provided it
if ($username =~ /^([\*\@])(.+)$/) {
    my $user_prefix = $1;
    $username = $2;
    
    # Warn if prefix doesn't match type
    if (($user_prefix eq '*' && $type ne 'prof') ||
        ($user_prefix eq '@' && $type ne 'monitor')) {
        print "Warning: Username prefix '$user_prefix' doesn't match type '$type'\n";
    }
}

# Encrypt password if provided
my $encrypted_password = '';
if ($password) {
    $encrypted_password = sha512_base64($password);
}

# Read existing file or create new
my @lines = ();
my $user_exists = 0;

if (-f $file) {
    open(my $fh, '<', $file) or die "Error: Cannot read $file: $!\n";
    while (<$fh>) {
        chomp;
        my $line = $_;
        
        # Skip comments and empty lines
        next if /^\s*#/ || /^\s*$/;
        
        # Check if user already exists
        if (/^([\*\@]?)$username:/ || /^([\*\@]?)$username\s*$/) {
            print "Warning: User '$username' already exists in $file\n";
            print "Updating password...\n";
            $user_exists = 1;
            $line = "$prefix$username:$encrypted_password";
        }
        
        push @lines, $line;
    }
    close($fh);
}

# Add new user if not exists
unless ($user_exists) {
    push @lines, "$prefix$username:$encrypted_password";
}

# Write back to file
open(my $fh, '>', $file) or die "Error: Cannot write to $file: $!\n";
flock($fh, LOCK_EX) or die "Error: Cannot lock $file: $!\n";

foreach my $line (@lines) {
    print $fh "$line\n";
}

flock($fh, LOCK_UN);
close($fh);

# Report success
my $type_name = $type eq 'aluno' ? 'student' : $type;
if ($user_exists) {
    print "Updated user '$username' ($type_name) in $file\n";
} else {
    print "Created user '$username' ($type_name) in $file\n";
}

if (!$password) {
    print "Note: User has empty password and must set one via sqtpm-pwd.cgi\n";
}

print "Entry: $prefix$username:$encrypted_password\n";