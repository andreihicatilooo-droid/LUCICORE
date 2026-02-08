#!/bin/bash
# Merchant API SDK - TOR Installation Script
# Automatically detects OS and installs TOR proxy

set -e

echo "================================"
echo "  TOR Proxy Installation Script"
echo "================================"

detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
    elif [ -f /etc/debian_version ]; then
        OS="debian"
    elif [ -f /etc/redhat-release ]; then
        OS="rhel"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        OS="unknown"
    fi
    echo $OS
}

install_tor() {
    local os=$(detect_os)
    echo "Detected OS: $os"

    case $os in
        ubuntu|debian)
            apt-get update && apt-get install -y tor
            systemctl enable tor && systemctl start tor
            ;;
        centos|rhel|fedora|rocky|alma)
            yum install -y epel-release || dnf install -y epel-release
            yum install -y tor || dnf install -y tor
            systemctl enable tor && systemctl start tor
            ;;
        alpine)
            apk add tor
            rc-update add tor default && service tor start
            ;;
        macos)
            if ! command -v brew &> /dev/null; then
                echo "Install Homebrew first: https://brew.sh"
                exit 1
            fi
            brew install tor && brew services start tor
            ;;
        arch|manjaro)
            pacman -Sy --noconfirm tor
            systemctl enable tor && systemctl start tor
            ;;
        *)
            echo "Unknown OS: $os"
            echo "Install TOR manually:"
            echo "  Ubuntu/Debian: apt-get install tor"
            echo "  CentOS/RHEL:   yum install tor"
            echo "  macOS:         brew install tor"
            exit 1
            ;;
    esac

    sleep 3
    echo ""
    if curl --socks5-hostname 127.0.0.1:9050 -s --connect-timeout 10 https://check.torproject.org/api/ip | grep -q '"IsTor":true'; then
        echo "TOR INSTALLED SUCCESSFULLY!"
        echo "Proxy: socks5h://127.0.0.1:9050"
    else
        echo "TOR installed. Check status: systemctl status tor"
    fi
}

if [ "$EUID" -ne 0 ] && [ "$(detect_os)" != "macos" ]; then
    echo "Please run as root (sudo)"
    exit 1
fi

install_tor
