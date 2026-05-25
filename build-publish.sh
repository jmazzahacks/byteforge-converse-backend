#!/bin/sh

VERSION_FILE="VERSION"
REGISTRY="ghcr.io/jmazzahacks/byteforge-converse-backend"

# Parse command line arguments
NO_CACHE=""
if [ "$1" = "--no-cache" ]; then
    NO_CACHE="--no-cache"
    echo "Building with --no-cache flag"
fi

# Initialize VERSION if missing
if [ ! -f "$VERSION_FILE" ]; then
    echo "1" > "$VERSION_FILE"
    echo "Created VERSION file with initial version 1"
fi

CURRENT_VERSION=$(cat "$VERSION_FILE" 2>/dev/null)

if ! echo "$CURRENT_VERSION" | grep -qE '^[0-9]+$'; then
    echo "Error: Invalid version format in $VERSION_FILE. Expected a number, got: $CURRENT_VERSION"
    exit 1
fi

VERSION=$((CURRENT_VERSION + 1))

echo "Building version $VERSION (incrementing from $CURRENT_VERSION)"

docker build $NO_CACHE --platform linux/amd64 -t $REGISTRY:$VERSION . \
    || { echo "docker build failed"; exit 1; }

# Tag as latest
docker tag $REGISTRY:$VERSION $REGISTRY:latest

# Push both tags
docker push $REGISTRY:$VERSION \
    || { echo "docker push (version) failed"; exit 1; }
docker push $REGISTRY:latest \
    || { echo "docker push (latest) failed"; exit 1; }

# Persist new version
echo "$VERSION" > "$VERSION_FILE"
echo "Updated $VERSION_FILE to version $VERSION"
