#!/bin/bash
set -e

IMAGE_NAME="${FURIVE_DOCKER_IMAGE:-furive-os-plugin-ros2-sensor-dataset-recorder:latest}"
CONTAINER_NAME="${FURIVE_DOCKER_CONTAINER_NAME:-furive-os-plugin-ros2-sensor-dataset-recorder}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${FURIVE_SENSOR_DATASET_RECORDER_CONFIG_DIR:-$SCRIPT_DIR/config}"
DATASETS_DIR="${FURIVE_SENSOR_DATASET_RECORDER_DATASETS_DIR:-/data/furive-os/data-logging-system/datasets}"
CYCLONEDDS_CONFIG_PATH="${FURIVE_SENSOR_DATASET_RECORDER_CYCLONEDDS_CONFIG:-}"
if [ -z "$CYCLONEDDS_CONFIG_PATH" ]; then
  if [ -f "$SCRIPT_DIR/../../../cyclonedds_config.xml" ]; then
    CYCLONEDDS_CONFIG_PATH="$SCRIPT_DIR/../../../cyclonedds_config.xml"
  else
    CYCLONEDDS_CONFIG_PATH="/data/furive-os/cyclonedds_config.xml"
  fi
fi
DOCKER_NAME_FLAG=(--rm)
TTY_FLAG=(-it)
FURIVE_NODE_TYPE="${FURIVE_NODE_TYPE:-agent}"

if [ "${FURIVE_PM_MANAGED:-0}" = "1" ]; then
  DOCKER_NAME_FLAG=(--name "$CONTAINER_NAME" --restart unless-stopped)
  TTY_FLAG=(-d)
  if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER_NAME"; then
    docker rm -f "$CONTAINER_NAME" >/dev/null
  fi
elif [ ! -t 0 ] || [ ! -t 1 ]; then
  TTY_FLAG=(-d)
fi

mkdir -p "$CONFIG_DIR" "$DATASETS_DIR"

if [ ! -f "$CYCLONEDDS_CONFIG_PATH" ]; then
  echo "ros2-sensor-dataset-recorder CycloneDDS 설정 없음: $CYCLONEDDS_CONFIG_PATH" >&2
  exit 1
fi

docker run "${TTY_FLAG[@]}" "${DOCKER_NAME_FLAG[@]}" \
  --net=host \
  --ipc=host \
  --pid=host \
  -v /etc/localtime:/etc/localtime:ro \
  -v /etc/timezone:/etc/timezone:ro \
  -v /dev/shm:/dev/shm \
  -v "$CONFIG_DIR:/data/config:rw" \
  -v "$DATASETS_DIR:/data/datasets:rw" \
  -v "$CYCLONEDDS_CONFIG_PATH:/etc/cyclonedds/config.xml:ro" \
  -e TZ="${TZ:-Asia/Seoul}" \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-79}" \
  -e ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}" \
  -e RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}" \
  -e CYCLONEDDS_URI="file:///etc/cyclonedds/config.xml" \
  -e SENSOR_DATASET_RECORDER_CONFIG="/data/config/params.yaml" \
  "$IMAGE_NAME"
