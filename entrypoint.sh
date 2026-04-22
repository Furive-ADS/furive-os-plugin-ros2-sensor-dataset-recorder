#!/bin/bash
set -e

source /opt/ros/${ROS_DISTRO:-humble}/setup.bash
source /ws/install/setup.bash

PARAMS_FILE="${SENSOR_DATASET_RECORDER_CONFIG:-/data/config/params.yaml}"
mkdir -p /data/dataset

ARGS=(--ros-args)

if [ -f "$PARAMS_FILE" ]; then
  ARGS+=(--params-file "$PARAMS_FILE")
fi

if [ -n "${SENSOR_DATASET_RECORDER_DATASET_DIR:-}" ]; then
  mkdir -p "${SENSOR_DATASET_RECORDER_DATASET_DIR}"
  ARGS+=(-p "dataset_root_dir:=${SENSOR_DATASET_RECORDER_DATASET_DIR}")
fi

if [ -n "${SENSOR_DATASET_RECORDER_LIDAR_TOPIC:-}" ]; then
  ARGS+=(-p "lidar_topic:=${SENSOR_DATASET_RECORDER_LIDAR_TOPIC}")
fi

if [ -n "${SENSOR_DATASET_RECORDER_CAMERA_TOPIC:-}" ]; then
  ARGS+=(-p "camera_topic:=${SENSOR_DATASET_RECORDER_CAMERA_TOPIC}")
fi

if [ -n "${SENSOR_DATASET_RECORDER_SAVE_INTERVAL:-}" ]; then
  ARGS+=(-p "save_interval:=${SENSOR_DATASET_RECORDER_SAVE_INTERVAL}")
fi

if [ -n "${SENSOR_DATASET_RECORDER_SYNC_SLOP:-}" ]; then
  ARGS+=(-p "sync_slop:=${SENSOR_DATASET_RECORDER_SYNC_SLOP}")
fi

if [ -n "${SENSOR_DATASET_RECORDER_TIMEOUT_THRESHOLD:-}" ]; then
  ARGS+=(-p "timeout_threshold:=${SENSOR_DATASET_RECORDER_TIMEOUT_THRESHOLD}")
fi

if [ -n "${SENSOR_DATASET_RECORDER_ID_HEARTBEAT_TIMEOUT:-}" ]; then
  ARGS+=(-p "id_heartbeat_timeout:=${SENSOR_DATASET_RECORDER_ID_HEARTBEAT_TIMEOUT}")
fi

exec ros2 run ros2_sensor_dataset_recorder ros2_sensor_dataset_recorder "${ARGS[@]}"
