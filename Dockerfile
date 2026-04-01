FROM osrf/ros:humble-desktop

ENV DEBIAN_FRONTEND=noninteractive
ENV ROS_DISTRO=humble
ENV TZ=Asia/Seoul

RUN apt-get update && apt-get install -y \
    python3-colcon-common-extensions \
    python3-opencv \
    python3-numpy \
    ros-humble-cv-bridge \
    ros-humble-message-filters \
    ros-humble-rmw-cyclonedds-cpp \
    ros-humble-sensor-msgs-py \
    tzdata \
    && ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime \
    && echo "${TZ}" > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /ws

COPY . /ws/src/ros2_sensor_dataset_recorder

RUN /bin/bash -lc "source /opt/ros/${ROS_DISTRO}/setup.bash && colcon build --symlink-install --packages-select ros2_sensor_dataset_recorder"

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
