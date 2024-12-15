#!/bin/bash
# Copyright (c) 2024 Tucker Craig
# See LICENSE file for full license details.

# Get the absolute directory of the current script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Color definitions
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
print_step() {
    echo -e "${BLUE}==> $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

EXTENSIONS_JSON="$HOME/.vscode/extensions/extensions.json"

# Create a backup of the current file
if [ -f "$EXTENSIONS_JSON" ]; then
    backup_file="${EXTENSIONS_JSON}.bak.$(date +%Y%m%d_%H%M%S)"
    print_step "Creating backup at: $backup_file"
    cp "$EXTENSIONS_JSON" "$backup_file"
fi

print_step "Restoring extensions.json with all extensions..."

# Create the new extensions.json with all extensions
cat > "$EXTENSIONS_JSON" << 'EOF'
[
  {
    "identifier": {
      "id": "local.current-theme"
    },
    "version": "1.0.0",
    "location": {
      "scheme": "file",
      "path": "/Users/tucker/.vscode/extensions/current-theme"
    },
    "relativeLocation": "current-theme"
  },
  {
    "identifier": {
      "id": "ritwickdey.liveserver",
      "uuid": "b63c44fd-0457-4696-99e9-dbfdf70d77de"
    },
    "version": "5.7.9",
    "location": {
      "scheme": "file",
      "path": "/Users/tucker/.vscode/extensions/ritwickdey.liveserver-5.7.9"
    },
    "relativeLocation": "ritwickdey.liveserver-5.7.9",
    "metadata": {
      "id": "b63c44fd-0457-4696-99e9-dbfdf70d77de",
      "publisherId": "17fd9a78-e430-4a78-add2-ade4a8830352",
      "publisherDisplayName": "Ritwick Dey",
      "targetPlatform": "undefined",
      "updated": false,
      "isPreReleaseVersion": false,
      "hasPreReleaseVersion": false,
      "installedTimestamp": 1712001254596,
      "pinned": false
    }
  },
  {
    "identifier": {
      "id": "yzhang.markdown-all-in-one",
      "uuid": "98790d67-10fa-497c-9113-f6c7489207b2"
    },
    "version": "3.6.2",
    "location": {
      "scheme": "file",
      "path": "/Users/tucker/.vscode/extensions/yzhang.markdown-all-in-one-3.6.2"
    },
    "relativeLocation": "yzhang.markdown-all-in-one-3.6.2",
    "metadata": {
      "id": "98790d67-10fa-497c-9113-f6c7489207b2",
      "publisherId": "36c8b41c-6ef6-4bf5-a5b7-65bef29b606f",
      "publisherDisplayName": "Yu Zhang",
      "targetPlatform": "undefined",
      "updated": false,
      "isPreReleaseVersion": false,
      "hasPreReleaseVersion": false,
      "installedTimestamp": 1713575155948,
      "pinned": false,
      "source": "gallery"
    }
  },
  {
    "identifier": {
      "id": "ms-python.python",
      "uuid": "f1f59ae4-9318-4f3c-a9b5-81b2eaa5f8a5"
    },
    "version": "2024.22.0",
    "location": {
      "scheme": "file",
      "path": "/Users/tucker/.vscode/extensions/ms-python.python-2024.22.0-darwin-arm64"
    },
    "relativeLocation": "ms-python.python-2024.22.0-darwin-arm64",
    "metadata": {
      "id": "f1f59ae4-9318-4f3c-a9b5-81b2eaa5f8a5",
      "publisherId": "998b010b-e2af-44a5-a6cd-0b5fd3b9b6f8",
      "publisherDisplayName": "Microsoft",
      "targetPlatform": "darwin-arm64",
      "updated": true,
      "isPreReleaseVersion": false,
      "hasPreReleaseVersion": false,
      "installedTimestamp": 1734059950089,
      "pinned": false,
      "source": "gallery"
    }
  },
  {
    "identifier": {
      "id": "vscodevim.vim",
      "uuid": "d96e79c6-8b25-4be3-8545-0e0ecefcae03"
    },
    "version": "1.29.0",
    "location": {
      "scheme": "file",
      "path": "/Users/tucker/.vscode/extensions/vscodevim.vim-1.29.0"
    },
    "relativeLocation": "vscodevim.vim-1.29.0",
    "metadata": {
      "id": "d96e79c6-8b25-4be3-8545-0e0ecefcae03",
      "publisherId": "5d63889b-1b67-4b1f-8350-4f1dce041a26",
      "publisherDisplayName": "vscodevim",
      "targetPlatform": "undefined",
      "updated": true,
      "isPreReleaseVersion": false,
      "hasPreReleaseVersion": false,
      "installedTimestamp": 1734059950090,
      "pinned": false,
      "source": "gallery"
    }
  },
  {
    "identifier": {
      "id": "github.copilot",
      "uuid": "23c4aeee-f844-43cd-b53e-1113e483f1a6"
    },
    "version": "1.252.0",
    "location": {
      "scheme": "file",
      "path": "/Users/tucker/.vscode/extensions/github.copilot-1.252.0"
    },
    "relativeLocation": "github.copilot-1.252.0",
    "metadata": {
      "id": "23c4aeee-f844-43cd-b53e-1113e483f1a6",
      "publisherId": "7c1c19cd-78eb-4dfb-8999-99caf7679002",
      "publisherDisplayName": "GitHub",
      "targetPlatform": "undefined",
      "updated": true,
      "isPreReleaseVersion": false,
      "hasPreReleaseVersion": false,
      "installedTimestamp": 1734148065460,
      "pinned": false,
      "source": "gallery"
    }
  },
  {
    "identifier": {
      "id": "golang.go",
      "uuid": "d6f6cfea-4b6f-41f4-b571-6ad2ab7918da"
    },
    "version": "0.42.1",
    "location": {
      "scheme": "file",
      "path": "/Users/tucker/.vscode/extensions/golang.go-0.42.1"
    },
    "relativeLocation": "golang.go-0.42.1",
    "metadata": {
      "id": "d6f6cfea-4b6f-41f4-b571-6ad2ab7918da",
      "publisherId": "dbf6ae0a-da75-4167-ac8b-75b4512f2153",
      "publisherDisplayName": "Go Team at Google",
      "targetPlatform": "undefined",
      "updated": false,
      "isPreReleaseVersion": false,
      "hasPreReleaseVersion": false,
      "installedTimestamp": 1734148501599,
      "source": "gallery"
    }
  }
]
EOF

print_success "Restored extensions.json with all major extensions"
print_warning "Please restart VSCode for the changes to take effect"
print_warning "Some extensions may need to be reinstalled through the marketplace"
print_warning "A backup of your previous extensions.json has been created"
