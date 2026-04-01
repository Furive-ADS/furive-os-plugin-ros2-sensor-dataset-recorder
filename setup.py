from warnings import simplefilter

from pkg_resources import PkgResourcesDeprecationWarning
from setuptools import SetuptoolsDeprecationWarning
from setuptools import setup

simplefilter("ignore", category=SetuptoolsDeprecationWarning)
simplefilter("ignore", category=PkgResourcesDeprecationWarning)

package_name = "ros2_sensor_dataset_recorder"

setup(
    name=package_name,
    version="0.1.0",
    packages=[package_name],
    data_files=[
        ("share/ament_index/resource_index/packages", [f"resource/{package_name}"]),
        (f"share/{package_name}", ["package.xml"]),
        (f"share/{package_name}/launch", [f"launch/{package_name}.launch.xml"]),
    ],
    install_requires=["setuptools"],
    zip_safe=True,
    maintainer="furive",
    maintainer_email="furive@dgist.ac.kr",
    description="ROS2 sensor dataset recorder for LiDAR and camera data",
    license="Apache License 2.0",
    tests_require=["pytest"],
    entry_points={
        "console_scripts": [
            "ros2_sensor_dataset_recorder = ros2_sensor_dataset_recorder.ros2_sensor_dataset_recorder:main"
        ],
    },
)
