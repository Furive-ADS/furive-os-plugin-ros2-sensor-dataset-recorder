#!/bin/bash

IMAGE_NAME=furive-os-plugin-ros2-sensor-dataset-recorder
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HASH_FILE="$SCRIPT_DIR/.build_hash"

network_available() {
    timeout 3 bash -c '</dev/tcp/archive.ubuntu.com/80' >/dev/null 2>&1 &&
    timeout 3 bash -c '</dev/tcp/packages.ros.org/80' >/dev/null 2>&1
}

image_exists() {
    docker image inspect "$IMAGE_NAME" > /dev/null 2>&1
}

CURRENT_HASH=$(
    cd "$SCRIPT_DIR" || exit 1
    {
        printf '%s\n' ./Dockerfile ./entrypoint.sh ./package.xml ./setup.cfg ./setup.py
        find ./launch ./resource ./ros2_sensor_dataset_recorder -type f ! -name '*.pyc' 2>/dev/null
    } | sort | xargs md5sum 2>/dev/null | md5sum | awk '{print $1}'
)

if [ "$1" = "--force" ]; then
    echo "$IMAGE_NAME 이미지 강제 빌드..."
    docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"
    if [ $? -eq 0 ]; then
        echo "$CURRENT_HASH" > "$HASH_FILE"
    fi
    exit $?
fi

PREVIOUS_HASH=""
if [ -f "$HASH_FILE" ]; then
    PREVIOUS_HASH=$(cat "$HASH_FILE")
fi

if ! image_exists; then
    echo "$IMAGE_NAME 이미지가 없습니다. 빌드 시작..."
    docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"
    if [ $? -eq 0 ]; then
        echo "$CURRENT_HASH" > "$HASH_FILE"
    fi
elif [ "$CURRENT_HASH" != "$PREVIOUS_HASH" ]; then
    if ! network_available; then
        echo "$IMAGE_NAME 소스 변경 감지, 하지만 네트워크가 없어 기존 이미지로 실행합니다. previous=${PREVIOUS_HASH:-none} current=$CURRENT_HASH (강제 빌드: ./build.sh --force)"
        exit 0
    fi
    echo "$IMAGE_NAME 소스 변경 감지. 재빌드 시작... previous=${PREVIOUS_HASH:-none} current=$CURRENT_HASH"
    docker build -t "$IMAGE_NAME" "$SCRIPT_DIR"
    if [ $? -eq 0 ]; then
        echo "$CURRENT_HASH" > "$HASH_FILE"
    fi
else
    echo "$IMAGE_NAME 변경 없음. 빌드 스킵. (강제 빌드: ./build.sh --force)"
fi
