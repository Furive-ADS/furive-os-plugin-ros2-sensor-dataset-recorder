#!/usr/bin/env python3

import os
import cv2
import numpy as np
from datetime import datetime
from cv_bridge import CvBridge

import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy
from message_filters import ApproximateTimeSynchronizer, Subscriber

from sensor_msgs.msg import PointCloud2, Image
import sensor_msgs_py.point_cloud2 as pc2
from std_msgs.msg import String, UInt8

DATASET_ROOT_DIR = '/data/datasets'


class SensorDatasetRecorder(Node):
    def __init__(self):
        super().__init__('ros2_sensor_dataset_recorder')

        # Declare parameters
        self.declare_parameter('dataset_root_dir', DATASET_ROOT_DIR)
        self.declare_parameter('lidar_topic', '/sensing/lidar/top/pointcloud_raw_ex')
        self.declare_parameter('camera_topic', '/sensing/camera/camera_top/image_raw')
        self.declare_parameter('save_interval', 0.5)
        self.declare_parameter('timeout_threshold', 1.5)
        self.declare_parameter('id_heartbeat_timeout', 1.5)

        # Get parameters
        dataset_root_dir = self.get_parameter('dataset_root_dir').get_parameter_value().string_value
        self.root_dir = dataset_root_dir
        lidar_topic = self.get_parameter('lidar_topic').get_parameter_value().string_value
        camera_topic = self.get_parameter('camera_topic').get_parameter_value().string_value
        save_interval = self.get_parameter('save_interval').get_parameter_value().double_value
        self.timeout_threshold = self.get_parameter('timeout_threshold').get_parameter_value().double_value
        self.id_heartbeat_timeout = self.get_parameter('id_heartbeat_timeout').get_parameter_value().double_value

        self.lidar_dir = None
        self.camera_dir = None
        self.prev_id = None

        self.rosbag_recorder_id_sub = self.create_subscription(
            String,
            '/rosbag_recorder_id',
            self.rosbag_recorder_id_callback,
            1,
        )

        # CV Bridge
        self.bridge = CvBridge()

        # QoS settings (BEST_EFFORT for lidar)
        qos_profile = QoSProfile(
            reliability=ReliabilityPolicy.BEST_EFFORT,
            history=HistoryPolicy.KEEP_LAST,
            depth=10
        )

        # Message filters subscribers
        self.lidar_sub = Subscriber(
            self,
            PointCloud2,
            lidar_topic,
            qos_profile=qos_profile
        )
        self.camera_sub = Subscriber(
            self,
            Image,
            camera_topic
        )

        # Approximate Time Synchronizer (sync within 100ms)
        self.sync = ApproximateTimeSynchronizer(
            [self.lidar_sub, self.camera_sub],
            queue_size=10,
            slop=0.1
        )
        self.sync.registerCallback(self.sync_callback)

        # Individual topic tracking callbacks
        self.lidar_sub.registerCallback(self.lidar_tracking_callback)
        self.camera_sub.registerCallback(self.camera_tracking_callback)

        # Timer for saving data
        self.timer = self.create_timer(save_interval, self.timer_callback)

        # Publisher for capture directory info
        self.capture_dir_pub = self.create_publisher(String, '/capture_dir', 10)
        self.diag_pub = self.create_publisher(UInt8, '/capture_diag', 10)

        # Latest synchronized data storage
        self.latest_lidar = None
        self.latest_camera = None
        self.latest_lidar_time = None
        self.latest_camera_time = None
        self.last_received_time = None

        # Individual topic tracking
        self.last_lidar_individual_time = None
        self.last_camera_individual_time = None

        # rosbag recorder settings
        self.last_id_heartbeat_time = None

        self.get_logger().info('Sensor Dataset Saver Node initialized')
        self.get_logger().info(f'Root dir: {self.root_dir}')
        self.get_logger().info(f'LiDAR topic: {lidar_topic}')
        self.get_logger().info(f'Camera topic: {camera_topic}')

    def lidar_tracking_callback(self, msg):
        self.last_lidar_individual_time = self.get_clock().now()

    def camera_tracking_callback(self, msg):
        self.last_camera_individual_time = self.get_clock().now()

    def sync_callback(self, lidar_msg, camera_msg):
        """Store synchronized lidar and camera messages"""
        self.latest_lidar = lidar_msg
        self.latest_camera = camera_msg
        self.latest_lidar_time = lidar_msg.header.stamp
        self.latest_camera_time = camera_msg.header.stamp
        self.last_received_time = self.get_clock().now()

    def rosbag_recorder_id_callback(self, msg: String):
        """Set save folder based on rosbag recorder start time"""
        if msg.data is None or msg.data.strip() == '':
            self.get_logger().info('Received wrong id.')
            return

        # Update heartbeat time
        self.last_id_heartbeat_time = self.get_clock().now()

        # Return if same id (just heartbeat update)
        if self.prev_id == msg.data.strip():
            return

        # Create dirs for new id
        self.create_dirs(msg.data.strip())

    def create_dirs(self, rosbag_start_time):
        session_ref = rosbag_start_time.strip().strip('/')
        parts = session_ref.split('/')

        if len(parts) >= 3 and parts[1] == 'bags':
            date_dir = parts[0]
            session_id = parts[2]
        else:
            session_id = os.path.basename(session_ref)
            if len(session_id) >= 10:
                date_dir = session_id[:10]
            else:
                date_dir = datetime.now().strftime('%Y-%m-%d')

        base_dir = os.path.join(self.root_dir, date_dir, 'sensor_blobs', 'trainval', session_id)

        self.lidar_dir = os.path.join(base_dir, 'MergedPointCloud')
        self.camera_dir = os.path.join(base_dir, 'CAM_F0')

        os.makedirs(self.lidar_dir, exist_ok=True)
        os.makedirs(self.camera_dir, exist_ok=True)

        self.prev_id = session_ref

        self.get_logger().info(f'Using rosbag start time as rosbag_start_time: {session_ref}')
        self.get_logger().info(f'Lidar save path: {self.lidar_dir}')
        self.get_logger().info(f'Camera save path: {self.camera_dir}')

    def timer_callback(self):
        """Periodically save the latest synchronized data to files"""
        # check 1: heartbeat timeout check
        if self.last_id_heartbeat_time is not None:
            current_time = self.get_clock().now()
            time_diff = (current_time - self.last_id_heartbeat_time).nanoseconds * 1e-9
            if time_diff > self.id_heartbeat_timeout:
                self.get_logger().warn(
                    f'check 1-1, Heartbeat timeout ({time_diff:.1f}s > {self.id_heartbeat_timeout}s). '
                    f'Stopping record.'
                )
                self.publish_diagnostic(1)
                return
        else:
            self.get_logger().warn("check 1-2, Waiting for /rosbag_recorder_id ...")
            self.publish_diagnostic(2)
            return

        # check 2: sensor topic check
        if self.latest_lidar is None or self.latest_camera is None:
            lidar_ok = self.last_lidar_individual_time is not None
            camera_ok = self.last_camera_individual_time is not None

            if not lidar_ok and not camera_ok:
                self.get_logger().warn('check 2, Both LiDAR and Camera not received')
                self.publish_diagnostic(33)
            elif not lidar_ok:
                self.get_logger().warn('check 2, LiDAR topic not received')
                self.publish_diagnostic(31)
            elif not camera_ok:
                self.get_logger().warn('check 2, Camera topic not received')
                self.publish_diagnostic(32)
            else:
                self.get_logger().warn('check 2, Both topics received but time sync failed (slop > 100ms)')
                self.publish_diagnostic(34)
            return

        # check 3: timeout check
        current_time = self.get_clock().now()
        time_since_last_msg = (current_time - self.last_received_time).nanoseconds * 1e-9

        if time_since_last_msg > self.timeout_threshold:
            self.get_logger().error(
                f'check 3, No new data received for {time_since_last_msg:.1f}s - '
                f'Topics may be disconnected. Skipping save.'
            )
            time_out_data = 0.0
            if time_since_last_msg < 10.0:
                time_out_data = 100 + int(time_since_last_msg * 10)
            else:
                if time_since_last_msg < 50.0:
                    time_out_data = 200 + int(time_since_last_msg)
                else:
                    time_out_data = 250

            # self.publish_diagnostic(4)
            self.publish_diagnostic(time_out_data)
            return

        # Current time (for filename)
        save_time = datetime.now()
        filename = save_time.strftime('%Y_%m_%d_%H_%M_%S_%f')

        # Publish capture directory info
        capture_msg = String()
        capture_msg.data = f"stamp: {current_time.nanoseconds * 1e-9:.6f}, file_name: {filename}"
        self.capture_dir_pub.publish(capture_msg)

        # Save Lidar as binary PCD
        pcd_path = os.path.join(self.lidar_dir, f'{filename}.pcd')
        self.save_pointcloud_as_binary_pcd(self.latest_lidar, pcd_path)

        # Save Camera as JPG
        jpg_path = os.path.join(self.camera_dir, f'{filename}.jpg')
        self.save_image_as_jpg(self.latest_camera, jpg_path)

        # Log timestamps
        lidar_time = self.latest_lidar_time.sec + self.latest_lidar_time.nanosec * 1e-9
        camera_time = self.latest_camera_time.sec + self.latest_camera_time.nanosec * 1e-9

        self.get_logger().info('=' * 60)
        self.get_logger().info(f'Data saved: {filename}')
        self.get_logger().info(f'current timestamp:  {current_time.nanoseconds * 1e-9:.6f}')
        self.get_logger().info(f'Lidar timestamp:  {lidar_time:.6f}')
        self.get_logger().info(f'Camera timestamp: {camera_time:.6f}')
        self.get_logger().info(f'Save time:        {save_time.strftime("%Y-%m-%d %H:%M:%S")}')
        self.get_logger().info(f'Sensor timestamp diff (ms):   {abs(lidar_time - camera_time) * 1000:.2f}')
        self.get_logger().info(f'Working diff (sec):   {(self.get_clock().now() - current_time).nanoseconds * 1e-9:.6f}')
        self.get_logger().info('=' * 60)
        self.publish_diagnostic(5)

    def save_pointcloud_as_binary_pcd(self, pointcloud_msg, filename):
        """Save PointCloud2 as binary PCD file (nuPlan format)

        Fields: x, y, z, intensity, ring, lidar_info
        Note: intensity, ring, lidar_info are dummy values (0.0)
        """
        try:
            points = []
            for point in pc2.read_points(pointcloud_msg, skip_nans=True):
                # x, y, z from pointcloud, intensity/ring/lidar_info as dummy (0.0)
                points.append([point[0], point[1], point[2], 0.0, 0.0, 0.0])

            points = np.asarray(points, dtype=np.float32)

            header = (
                "# .PCD v0.7 - Point Cloud Data file format\n"
                "VERSION 0.7\n"
                "FIELDS x y z intensity ring lidar_info\n"
                "SIZE 4 4 4 4 4 4\n"
                "TYPE F F F F F F\n"
                "COUNT 1 1 1 1 1 1\n"
                f"WIDTH {len(points)}\n"
                "HEIGHT 1\n"
                "VIEWPOINT 0 0 0 1 0 0 0\n"
                f"POINTS {len(points)}\n"
                "DATA binary\n"
            )

            with open(filename, "wb") as f:
                f.write(header.encode("ascii"))
                f.write(points.tobytes(order="C"))

            self.get_logger().info(f"Saved binary PCD: {filename} ({len(points)} points)")
        except Exception as e:
            self.get_logger().error(f"Failed to save PCD: {str(e)}")

    def save_image_as_jpg(self, image_msg, filename):
        """Save Image as JPG file"""
        try:
            cv_image = self.bridge.imgmsg_to_cv2(image_msg, desired_encoding='bgr8')
            cv2.imwrite(filename, cv_image)
            self.get_logger().info(f'Saved JPG: {filename} ({cv_image.shape[1]}x{cv_image.shape[0]})')
        except Exception as e:
            self.get_logger().error(f'Failed to save JPG: {str(e)}')

    def publish_diagnostic(self, num):
        diag_msg = UInt8()
        diag_msg.data = num
        self.diag_pub.publish(diag_msg)

def main(args=None):
    rclpy.init(args=args)
    node = SensorDatasetRecorder()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
