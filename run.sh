#!/bin/bash
set -e

IMAGE_NAME="${FURIVE_DOCKER_IMAGE:-furive-os-plugin-ros2-sensor-dataset-recorder:latest}"
CONTAINER_NAME="${FURIVE_DOCKER_CONTAINER_NAME:-furive-os-plugin-ros2-sensor-dataset-recorder}"
CONFIG_DIR="${FURIVE_SENSOR_DATASET_RECORDER_CONFIG_DIR:-/data/furive-os/ros2-sensor-dataset-recorder/config}"
ROSBAGS_DIR="${FURIVE_SENSOR_DATASET_RECORDER_ROSBAGS_DIR:-/data/furive-os/data-logging-system/rosbags}"
CYCLONEDDS_CONFIG_PATH="${FURIVE_SENSOR_DATASET_RECORDER_CYCLONEDDS_CONFIG:-$CONFIG_DIR/cyclonedds.xml}"
DOCKER_NAME_FLAG=(--rm)
TTY_FLAG=(-it)

if [ "${FURIVE_PM_MANAGED:-0}" = "1" ]; then
  DOCKER_NAME_FLAG=(--name "$CONTAINER_NAME" --restart unless-stopped)
  TTY_FLAG=(-d)
elif [ ! -t 0 ] || [ ! -t 1 ]; then
  TTY_FLAG=(-d)
fi

mkdir -p "$CONFIG_DIR" "$ROSBAGS_DIR"

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
  -v "$ROSBAGS_DIR:/data/rosbags:rw" \
  -v "$CYCLONEDDS_CONFIG_PATH:/etc/cyclonedds/runtime_config.xml:ro" \
  -e TZ="${TZ:-Asia/Seoul}" \
  -e ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-79}" \
  -e ROS_LOCALHOST_ONLY="${ROS_LOCALHOST_ONLY:-0}" \
  -e RMW_IMPLEMENTATION="${RMW_IMPLEMENTATION:-rmw_cyclonedds_cpp}" \
  -e CYCLONEDDS_URI="file:///etc/cyclonedds/runtime_config.xml" \
  -e SENSOR_DATASET_RECORDER_CONFIG="/data/config/params.yaml" \
  "$IMAGE_NAME"
