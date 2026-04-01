# ros2_sensor_dataset_recorder

LiDAR와 카메라 데이터를 시간 동기화하여 nuPlan 호환 포맷으로 저장하는 ROS2 패키지.
(ros2 topic의 stamp를 동기화 할 뿐이지 하드웨어의 시간 동기화는 별도로 진행해주어야 한다)

외부 rosbag recorder와 연동하여 세션 단위 데이터 수집을 수행하며, 3단계 검증 파이프라인과 진단 코드를 통해 안정적인 녹화 상태를 보장한다.

## 동작 방식

### 녹화 흐름

1. `/rosbag_recorder_id` 토픽으로 세션 ID(rosbag 시작 시간) 수신
2. 세션별 저장 디렉토리 생성: `{dataset_root_dir}/{YYYY-MM-DD}/sensor_blobs/trainval/{session_id}/` (세션 예시: CAM_F0, MergedPointCloud 등)
3. LiDAR(PointCloud2)와 Camera(Image)를 ApproximateTimeSynchronizer로 100ms 이내 동기화
4. `save_interval` 주기로 3단계 검증 후 디스크에 저장

### 저장 포맷

| 센서 | 디렉토리 | 포맷 | 비고 |
|------|----------|------|------|
| LiDAR | `MergedPointCloud/` | Binary PCD (v0.7) | Fields: x, y, z, intensity, ring, lidar_info (nuPlan 포맷) |
| Camera | `CAM_F0/` | JPG (BGR8) | cv_bridge로 변환 후 저장 |

파일명: `YYYY_MM_DD_HH_MM_SS_ffffff` (시스템 시간 기준)

### 3단계 검증 파이프라인

저장 시도 시마다 아래 순서로 검증하며, 실패 시 해당 진단 코드를 publish하고 저장을 건너뛴다.

| 단계 | 검증 내용 | 실패 조건 |
|------|----------|----------|
| 1 | Heartbeat 확인 | `/rosbag_recorder_id` 미수신 또는 타임아웃 |
| 2 | 센서 토픽 확인 | LiDAR/Camera 미수신 또는 동기화 실패 |
| 3 | 데이터 신선도 확인 | 마지막 동기화 데이터가 `timeout_threshold` 초과 |

## 토픽

### Subscribe

| 토픽 | 타입 | QoS | 설명 |
|------|------|-----|------|
| `/sensing/lidar/concatenated/pointcloud` | sensor_msgs/PointCloud2 | BEST_EFFORT | LiDAR 포인트클라우드 |
| `/sensing/camera/camera_top/image_raw` | sensor_msgs/Image | Default | 카메라 이미지 |
| `/rosbag_recorder_id` | std_msgs/String | Default | 녹화 세션 ID 및 heartbeat |

### Publish

| 토픽 | 타입 | 설명 |
|------|------|------|
| `/capture_dir` | std_msgs/String | 저장 시 타임스탬프와 파일명 정보 |
| `/capture_diag` | std_msgs/UInt8 | 진단 코드 (아래 표 참고) |

### 진단 코드 (`/capture_diag`)

| 코드 | 의미 |
|------|------|
| 1 | Heartbeat 타임아웃 (녹화 중단) |
| 2 | `/rosbag_recorder_id` 대기 중 |
| 5 | 저장 성공 |
| 31 | LiDAR 미수신 |
| 32 | Camera 미수신 |
| 33 | 양쪽 센서 모두 미수신 |
| 34 | 양쪽 수신되었으나 동기화 실패 (>100ms) |
| 100-190 | 타임아웃 <10초 (`100 + int(seconds * 10)`) |
| 200-249 | 타임아웃 <50초 (`200 + int(seconds)`) |
| 250 | 타임아웃 >= 50초 |

## 파라미터

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `dataset_root_dir` | string | `../niro_dataset` | 데이터셋 루트 디렉토리 |
| `lidar_topic` | string | `/sensing/lidar/concatenated/pointcloud` | LiDAR 토픽 |
| `camera_topic` | string | `/sensing/camera/camera_top/image_raw` | Camera 토픽 |
| `save_interval` | double | `0.5` | 저장 주기 (초) |
| `timeout_threshold` | double | `1.5` | 데이터 타임아웃 임계값 (초) |
| `id_heartbeat_timeout` | double | `1.5` | Heartbeat 타임아웃 임계값 (초) |

## 실행

```bash
ros2 launch ros2_sensor_dataset_recorder ros2_sensor_dataset_recorder.launch.xml
```

furive-os 관리 패키지로 실행:

```bash
cd package/plugin/ros2-sensor-dataset-recorder
./build.sh
./run.sh
```

파라미터 오버라이드:

```bash
ros2 launch ros2_sensor_dataset_recorder ros2_sensor_dataset_recorder.launch.xml \
  dataset_root_dir:=/data/dataset \
  lidar_topic:=/lidar/points \
  camera_topic:=/camera/image \
  save_interval:=0.2
```

## 의존성

- `rclpy`, `sensor_msgs`, `std_msgs`, `message_filters`
- `cv_bridge`, `python3-opencv`, `python3-numpy`
